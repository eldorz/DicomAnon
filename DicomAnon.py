import sys
import glob
import os
import shutil
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar, QVBoxLayout, QApplication, QFileDialog, QTextEdit
from PyQt6.QtGui import QTextCursor, QTextOption
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
        self.anon_button = QPushButton('Anonymise!')
        self.anon_button.clicked.connect(self.anon_button_clicked)

        self.pbar = QProgressBar(self, minimum=0, maximum=100, textVisible=False, objectName="BlueProgressBar")
        self.pbar.setValue(0)
        self.pbar.setVisible(False)

        self.logOutput = QTextEdit(self)
        self.logOutput.setReadOnly(True)
        self.logFont = self.logOutput.font()
        self.logFont.setFamily("Courier")
        self.logFont.setPointSize(10)

        self.resize(600, 400)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.pbar)
        self.vbox.addWidget(self.anon_button)
        self.vbox.addWidget(self.logOutput)
        self.setLayout(self.vbox)
        self.show()

    def anonymise_image(self, ds):
        # update the personal fields
        ds.PatientAddress = 'Anonymised'
        ds.PatientMotherBirthName = 'Anonymised'
        ds.EthnicGroup = 'Anonymised'
        ds.PatientIdentityRemoved = 'YES'

        ds.ReferringPhysicianName = 'Anonymised'
        ds.ReferringPhysicianAddress = 'Anonymised'

        ds.StudyDescription = 'Anonymised'
        ds.SeriesDescription = 'Anonymised'

        ds.InstitutionName = 'Anonymised'
        ds.InstitutionAddress = 'Anonymised'

        # remove private data elements, as there is no guarantee as to what kind of information might be contained in them
        ds.remove_private_tags()

        return ds

    # process all DICOMs under the selected top-level folder containing patient folders
    def process_folder(self, tl_dir):
        base_dir = os.path.dirname(tl_dir)
        tl_folder_name = os.path.basename(tl_dir)
        anon_tl_folder_name = tl_folder_name + '_ANON'
        # directories under the top-level folder
        tl_files_l = glob.glob('{}/*'.format(tl_dir), recursive=False)
        # need to replace two things in the DICOM's full path name with the anonymised version:
        #   1. the top-level folder name
        #   2. the patient folder name
        patient_id = 1
        patients_d = {}
        for tl_file_idx,tl_file in enumerate(tl_files_l):
            if os.path.isdir(tl_file):
                # this is a patient folder
                patient_folder_name = os.path.basename(tl_file)
                folder_sub = tl_dir + os.sep + patient_folder_name
                # the anon patient folder
                anon_patient_folder_name = 'Brain-{:03d}'.format(patient_id)
                # to anonymise the folder names, we now have the substring to replace with
                anon_folder_sub = anon_tl_folder_name + os.sep + anon_patient_folder_name
                anon_tl_file = tl_file.replace(tl_file, anon_folder_sub)
                anon_tl_path = base_dir + os.sep + anon_tl_file
                # now find the DICOMs under the patient folder
                dicom_files = glob.glob('{}/**/*.dcm'.format(tl_file), recursive=True)
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
                        ds = self.anonymise_image(ds)
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
        dicom_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if dicom_dir != "":
            # update the progress bar
            self.pbar.setValue(0)
            self.pbar.setVisible(True)
            # process the DICOMs within
            patients_d = self.process_folder(dicom_dir)
            # display log
            self.logOutput.setCurrentFont(self.logFont)
            # self.logOutput.setTextColor(color)
            for k, v in patients_d.items():
                log_msg = 'Patient {}\nsource: {}\ndestination: {}\n{} files processed\n{} invalid\n------\n'.format(k, v['from_folder'], v['to_folder'], v['number_of_files'], v['invalid_file_count'])
                self.logOutput.insertPlainText(log_msg)
                sb = self.logOutput.verticalScrollBar()
                sb.setValue(sb.maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    widget = DicomAnonWidget()
    widget.show()
    sys.exit(app.exec())
