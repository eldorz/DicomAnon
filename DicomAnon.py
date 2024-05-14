import sys
import glob
import os
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar, QVBoxLayout, QHBoxLayout, QApplication, QFileDialog, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from pydicom import dcmread
import pandas as pd
from os.path import expanduser
from datetime import datetime

StyleSheet = '''
#BlueProgressBar {
    background-color: #E0E0E0;
    text-align: center;
}
#BlueProgressBar::chunk {
    background-color: #2196F3;
    width: 10px; 
    margin: 0.5px;
}
'''

class DicomAnonWidget(QWidget):
    def __init__(self):
        super(DicomAnonWidget, self).__init__()
        self.setWindowTitle('DICOM Anonymiser')

        self.source_dir = ""
        self.destination_dir = ""

        self.source_button = QPushButton('Source Folder')
        self.source_button.setMaximumWidth(150)
        self.source_button.clicked.connect(self.source_button_clicked)

        self.source_label = QLabel('<< none >>')
        self.source_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.destination_button = QPushButton('Destination Folder')
        self.destination_button.setMaximumWidth(150)
        self.destination_button.clicked.connect(self.destination_button_clicked)

        self.destination_label = QLabel('<< none >>')
        self.destination_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.anon_button = QPushButton('Anonymise!')
        self.anon_button.clicked.connect(self.anon_button_clicked)

        # progress bar
        self.pbar = QProgressBar(self, minimum=0, maximum=100, textVisible=False, objectName="BlueProgressBar")
        self.pbar.setValue(0)
        self.pbar.setVisible(True)

        # source folder
        self.source_hbox = QHBoxLayout()
        self.source_hbox.addWidget(self.source_button)
        self.source_hbox.addWidget(self.source_label)

        # destination folder
        self.destination_hbox = QHBoxLayout()
        self.destination_hbox.addWidget(self.destination_button)
        self.destination_hbox.addWidget(self.destination_label)

        # status bar
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setFixedWidth(600)
        self.vbox = QVBoxLayout()
        self.vbox.setSpacing(5)
        self.vbox.addLayout(self.source_hbox)
        self.vbox.addLayout(self.destination_hbox)
        self.vbox.addWidget(self.anon_button)
        self.vbox.setSpacing(10)
        self.vbox.addWidget(self.pbar)
        self.vbox.addWidget(self.status_label)
        self.setLayout(self.vbox)
        self.show()
        self.activateWindow()
        self.raise_()

    def anonymise_image(self, image, name):
        # update the personal fields
        image.PatientName = name
        image.PatientID = name
        image.PatientAddress = 'Anonymised'
        image.PatientMotherBirthName = 'Anonymised'
        image.EthnicGroup = 'Anonymised'
        image.PatientIdentityRemoved = 'YES'

        image.ReferringPhysicianName = 'Anonymised'
        image.ReferringPhysicianAddress = 'Anonymised'

        # remove private data elements, as there is no guarantee as to what kind of information might be contained in them
        image.remove_private_tags()

        return image

    # look at the mapping file and determine the next ID to use
    def get_anon_patient_id(self, patient_id, mapping_df):
        new_patient = False
        if mapping_df is None:
            print('no previous mapping - starting')
            anon_patient_id = 1
            new_patient = True
        else:
            # have we seen this patient ID before?
            row_df = mapping_df[mapping_df.patient_id == patient_id]
            if len(row_df) > 0:
                anon_patient_id = row_df.iloc[0].anon_patient_id
                new_patient = False
                print('patient ID {} seen previously (anon ID {}) - appending to existing directory'.format(patient_id, anon_patient_id))
            else:
                anon_patient_id = mapping_df.anon_patient_id.max()+1
                new_patient = True
                print('patient ID {} not seen previously - adding new anon ID {} directory'.format(patient_id, anon_patient_id))
        return new_patient, anon_patient_id

    # process all DICOMs under the selected top-level folder containing patient folders
    def process_folder(self, source_base_dir, destination_base_dir, mapping_df):
        # update the status bar
        self.status_label.setText('Counting files.')
        # process GUI events to reflect the update value
        QApplication.processEvents()
        # count the DICOM files under the selected directory
        dicom_files_count = len(glob.glob('{}/**/*.dcm'.format(source_base_dir), recursive=True))
        print('{} files'.format(dicom_files_count))
        dicom_files_processed = 0
        # update the status bar
        self.status_label.setText('Found {} files.'.format(dicom_files_count))
        # process GUI events to reflect the update value
        QApplication.processEvents()
        # find the patient directories
        patient_dirs_l = [ name for name in os.listdir(source_base_dir) if os.path.isdir(os.path.join(source_base_dir, name)) ]
        for patient_dir_idx,patient_dir in enumerate(patient_dirs_l):
            valid_file_count = 0
            invalid_file_count = 0
            patient_id = int(patient_dir.split('_')[0])
            new_patient, anon_patient_id = self.get_anon_patient_id(patient_id, mapping_df)
            anon_patient_folder_name = 'Brain-{:04d}'.format(anon_patient_id)
            anon_patient_dir = destination_base_dir + os.sep + anon_patient_folder_name
            patient_full_dir = source_base_dir + os.sep + patient_dir
            dicom_files = glob.glob('{}/**/*.dcm'.format(patient_full_dir), recursive=True)
            # update the status bar
            self.status_label.setText('Processing patient ID {}'.format(patient_id))
            # process GUI events to reflect the update value
            QApplication.processEvents()
            for source_file in dicom_files:
                rel_path = os.path.relpath(source_file, patient_full_dir)  # use the same relative path for source and target
                anon_patient_file = anon_patient_dir + os.sep + rel_path   # add the relative path to the 'Brain-nnnn' directory
                # load and process the file
                try:
                    ds = dcmread(source_file)
                    valid_file_count += 1
                    # process GUI events
                    QApplication.processEvents()
                except Exception as e:
                    print(e)
                    invalid_file_count += 1
                else:
                    ds = self.anonymise_image(image=ds, name=anon_patient_folder_name)
                    # create the anon folder if it doesn't exist
                    target_dir = os.path.dirname(anon_patient_file)  # create the missing directories all the way to the DICOM file
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    ds.save_as(anon_patient_file)
                # update count of files processed
                dicom_files_processed += 1
                # update the progress bar
                proportion_completed = int((dicom_files_processed)/dicom_files_count*100)
                self.pbar.setValue(proportion_completed)
                # process GUI events to reflect the update value
                QApplication.processEvents()
            # count the total sessions anonymised for this patient
            anon_patient_sessions_l = [ name for name in os.listdir(anon_patient_dir) if os.path.isdir(os.path.join(anon_patient_dir, name)) ]
            session_count = len(anon_patient_sessions_l)
            # update the status bar
            self.status_label.setText('Updating the patient ID mapping.')
            # process GUI events to reflect the update value
            QApplication.processEvents()
            # add or update the mapping
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if new_patient:
                row = pd.Series({'patient_id':patient_id, 'anon_patient_dir_name':anon_patient_folder_name, 'anon_patient_id':anon_patient_id, 'total_session_count':session_count, 'valid_file_count':valid_file_count, 'invalid_file_count':invalid_file_count, 'last_updated':date_str})
                mapping_df = pd.concat([mapping_df, pd.DataFrame([row], columns=row.index)]).reset_index(drop=True)
            else:
                row_index = mapping_df.loc[mapping_df['patient_id'] == patient_id].index[0]
                mapping_df.loc[row_index, 'total_session_count'] = session_count
                mapping_df.loc[row_index, 'last_updated'] = date_str
                mapping_df.loc[row_index, 'valid_file_count'] += valid_file_count
                mapping_df.loc[row_index, 'invalid_file_count'] += invalid_file_count

        return mapping_df

    def anon_button_clicked(self):
        # get the file names under the directory selected
        if self.source_dir != "":
            # update the progress bar
            self.pbar.setValue(0)
            self.pbar.setVisible(True)
            QApplication.processEvents()
            # disable buttons
            self.source_button.setEnabled(False)
            self.destination_button.setEnabled(False)
            self.anon_button.setEnabled(False)
            # set up the mapping file
            mapping_file = '{}dicom-anon-mapping.xlsx'.format(expanduser('~')+os.sep)
            if os.path.isfile(mapping_file):
                mapping_df = pd.read_excel(mapping_file, index_col=0)
            else:
                mapping_df = None
            # process UI events
            QApplication.processEvents()
            # process the DICOMs within
            mapping_df = self.process_folder(self.source_dir, self.destination_dir, mapping_df)
            # process UI events
            QApplication.processEvents()
            # update the status bar
            self.status_label.setText('Saving the ID mapping file.')
            # update the mapping file
            mapping_df.to_excel(mapping_file)
            # process UI events
            QApplication.processEvents()
            # enable buttons
            self.source_button.setEnabled(True)
            self.destination_button.setEnabled(True)
            self.anon_button.setEnabled(True)
            # update the status bar
            self.status_label.setText('Finished processing.')

    def source_button_clicked(self):
        # update the progress bar
        self.pbar.setValue(0)
        # update the status bar
        self.status_label.setText('')

        self.source_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if self.source_dir != "":
            self.source_label.setText(self.source_dir)

    def destination_button_clicked(self):
        # update the progress bar
        self.pbar.setValue(0)
        # update the status bar
        self.status_label.setText('')

        self.destination_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if self.destination_dir != "":
            self.destination_label.setText(self.destination_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    widget = DicomAnonWidget()
    widget.show()
    sys.exit(app.exec())
