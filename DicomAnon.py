import sys
import glob
import os
import shutil
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar, QVBoxLayout, QHBoxLayout, QApplication, QFileDialog, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from pydicom import dcmread
import datetime
import random

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
        self.pbar.setVisible(False)

        # log output
        self.logOutput = QTextEdit(self)
        self.logOutput.setReadOnly(True)
        self.logFont = self.logOutput.font()
        self.logFont.setFamily("Courier")
        self.logFont.setPointSize(10)

        # source folder
        self.source_hbox = QHBoxLayout()
        self.source_hbox.addWidget(self.source_button)
        self.source_hbox.addWidget(self.source_label)

        # destination folder
        self.destination_hbox = QHBoxLayout()
        self.destination_hbox.addWidget(self.destination_button)
        self.destination_hbox.addWidget(self.destination_label)

        self.resize(600, 400)
        self.vbox = QVBoxLayout()
        self.vbox.setSpacing(5)
        self.vbox.addWidget(self.pbar)
        self.vbox.addLayout(self.source_hbox)
        self.vbox.addLayout(self.destination_hbox)
        self.vbox.addWidget(self.anon_button)
        self.vbox.addSpacing(10)
        self.vbox.addWidget(self.logOutput)
        self.setLayout(self.vbox)
        self.show()

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

        image.StudyDescription = 'Anonymised'
        image.SeriesDescription = 'Anonymised'

        image.InstitutionName = 'Anonymised'
        image.InstitutionAddress = 'Anonymised'

        # remove private data elements, as there is no guarantee as to what kind of information might be contained in them
        image.remove_private_tags()

        return image

    # look for existing anon folders and determine the next ID to use
    def get_base_id(self, destination_dir):
        last_id = None
        dir_names_l = sorted(glob.glob('{}/Brain-???'.format(destination_dir), recursive=False))
        if len(dir_names_l) > 0:
            last_name = dir_names_l[-1]
            last_id = int(last_name.split('Brain-')[1])
        else:
            last_id = 1
        return last_id

    # process all DICOMs under the selected top-level folder containing patient folders
    def process_folder(self, source_dir, destination_dir):
        # directories under the top-level folder
        base_dir = os.path.dirname(source_dir)
        source_subdir_l = glob.glob('{}/*'.format(source_dir), recursive=False)

        print('checking {}'.format(source_dir))
        patient_id = self.get_base_id(destination_dir)
        print('base patient ID: {}'.format(patient_id))
        patients_d = {}
        for tl_file_idx,source_subdir in enumerate(source_subdir_l):
            if os.path.isdir(source_subdir):
                # this is a patient folder
                patient_folder_name = os.path.basename(source_subdir)
                print('processing {}'.format(patient_folder_name))
                folder_sub = source_subdir + os.sep + patient_folder_name
                # the anon patient folder
                anon_patient_folder_name = 'Brain-{:03d}'.format(patient_id)
                # to anonymise the folder names, we now have the substring to replace with
                anon_folder_sub = self.destination_dir + os.sep + anon_patient_folder_name
                # now find the DICOMs under the patient folder
                dicom_files = glob.glob('{}/**/*.dcm'.format(source_subdir), recursive=True)
                invalid_file_count = 0
                for dicom_fn in dicom_files:
                    anon_dicom_fn = base_dir + os.sep + dicom_fn.replace(folder_sub, anon_folder_sub)
                    anon_dicom_fn_dirname = os.path.dirname(anon_dicom_fn)
                    # create the anon folder if it doesn't exist
                    if not os.path.exists(anon_dicom_fn_dirname):
                        os.makedirs(anon_dicom_fn_dirname)
                    # load and process the file
                    try:
                        ds = dcmread(dicom_fn)
                    except Exception as e:
                        print(e)
                        invalid_file_count += 1
                    else:
                        # ds = self.anonymise_image(image=ds, name=anon_patient_folder_name)
                        ds.save_as(anon_dicom_fn)
                patients_d[patient_id] = {'number_of_files':len(dicom_files), 
                                          'invalid_file_count':invalid_file_count,
                                          'from_folder':tl_file,
                                          'to_folder':anon_tl_path
                                          }
                patient_id += 1

            # update the progress bar
            proportion_completed = int((tl_file_idx+1)/len(tl_files_l)*100)
            self.pbar.setValue(proportion_completed)
            # process GUI events to reflect the update value
            QApplication.processEvents()
        return patients_d

    def anon_button_clicked(self):
        # get the file names under the directory selected
        if self.dicom_dir != "":
            # update the progress bar
            self.pbar.setValue(0)
            self.pbar.setVisible(True)
            # process the DICOMs within
            patients_d = self.process_folder(self.dicom_dir)
            # display log
            self.logOutput.setCurrentFont(self.logFont)
            # self.logOutput.setTextColor(color)
            for k, v in patients_d.items():
                log_msg = 'Patient {}\nsource: {}\ndestination: {}\n{} files processed\n{} invalid\n------\n'.format(k, v['from_folder'], v['to_folder'], v['number_of_files'], v['invalid_file_count'])
                self.logOutput.insertPlainText(log_msg)
                sb = self.logOutput.verticalScrollBar()
                sb.setValue(sb.maximum())

    def source_button_clicked(self):
        self.source_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if self.source_dir != "":
            self.source_label.setText(self.source_dir)

    def destination_button_clicked(self):
        self.destination_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if self.destination_dir != "":
            self.destination_label.setText(self.destination_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    widget = DicomAnonWidget()
    widget.show()
    sys.exit(app.exec())
