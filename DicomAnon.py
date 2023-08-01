import sys
import glob
import os
import shutil
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar, QVBoxLayout, QApplication, QFileDialog, QGroupBox, QLineEdit, QLabel, QGridLayout, QErrorMessage, QMessageBox
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

        self.patientFieldsGroupBox = QGroupBox("Patient Fields")

        self.familyNameEdit = QLineEdit(self)
        familyNameEditLabel = QLabel("&Family name:", self)
        familyNameEditLabel.setBuddy(self.familyNameEdit)

        self.givenNameEdit = QLineEdit(self)
        givenNameEditLabel = QLabel("&Given name:", self)
        givenNameEditLabel.setBuddy(self.givenNameEdit)

        self.patientIDEdit = QLineEdit(self)
        patientIDEditLabel = QLabel("&Patient ID:", self)
        patientIDEditLabel.setBuddy(self.patientIDEdit)

        layout = QGridLayout()
        layout.addWidget(familyNameEditLabel, 0, 0)
        layout.addWidget(self.familyNameEdit, 0, 1)
        layout.addWidget(givenNameEditLabel, 1, 0)
        layout.addWidget(self.givenNameEdit, 1, 1)
        layout.addWidget(patientIDEditLabel, 2, 0)
        layout.addWidget(self.patientIDEdit, 2, 1)
        self.patientFieldsGroupBox.setLayout(layout)

        self.resize(400, 200)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.patientFieldsGroupBox)
        self.vbox.addWidget(self.pbar)
        self.vbox.addWidget(self.anon_button)
        self.setLayout(self.vbox)
        self.show()

    def anonymise_image(self, ds, current_date, current_time, patient_birth_month, patient_birth_day):
        # update the personal fields
        ds.PatientName = '{} {}'.format(self.givenNameEdit.text(), self.familyNameEdit.text())
        ds.PatientID = self.patientIDEdit.text()
        try:
            patientBirthYear = datetime.datetime.strptime(ds.PatientBirthDate, "%Y%m%d").year
        except:
            patientBirthYear = 1900
        ds.PatientBirthDate = datetime.datetime(patientBirthYear, patient_birth_month, patient_birth_day)
        ds.PatientBirthTime = current_time
        ds.PatientSex = 'O'
        ds.PatientAddress = 'Anonymised'
        ds.PatientMotherBirthName = 'Anonymised'
        ds.EthnicGroup = 'Anonymised'
        ds.PatientIdentityRemoved = 'YES'

        ds.ReferringPhysicianName = 'Anonymised'
        ds.ReferringPhysicianAddress = 'Anonymised'

        ds.StudyDescription = 'Anonymised'
        ds.SeriesDescription = 'Anonymised'
        ds.StudyID = 'RMIT-EDU'

        ds.StudyDate = current_date
        ds.StudyTime = current_time
        ds.SeriesDate = current_date
        ds.SeriesTime = current_time
        ds.InstanceCreationDate = current_date
        ds.InstanceCreationTime = current_time
        ds.ContentDate = current_date
        ds.ContentTime = current_time
        
        ds.InstitutionName = 'Anonymised'
        ds.InstitutionAddress = 'Anonymised'

        # remove private data elements, as there is no guarantee as to what kind of information might be contained in them
        ds.remove_private_tags()

        return ds

    def valid_input_fields(self):
        valid = True
        if len(self.familyNameEdit.text()) == 0:
            self.familyNameEdit.setStyleSheet("border: 1px solid red;")
            valid = False
        else:
            self.familyNameEdit.setStyleSheet("border: 0px;")

        if len(self.givenNameEdit.text()) == 0:
            self.givenNameEdit.setStyleSheet("border: 1px solid red;")
            valid = False
        else:
            self.givenNameEdit.setStyleSheet("border: 0px;")

        if len(self.patientIDEdit.text()) == 0:
            self.patientIDEdit.setStyleSheet("border: 1px solid red;")
            valid = False
        else:
            self.patientIDEdit.setStyleSheet("border: 0px;")
        
        if not valid:
            # display a prompt
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Missing input fields")
            dlg.setText("Please enter a value in the fields with a red border.")
            button = dlg.exec()
        return valid

    def anon_button_clicked(self):
        # make sure the fields are not empty
        if self.valid_input_fields():
            # get the current time
            d = datetime.datetime.now()
            current_date = d.strftime("%Y%m%d")
            current_time = d.strftime("%H%M%S.%f")

            # select anonymised birth date
            patient_birth_month = random.randint(1, 12)
            patient_birth_day = random.randint(1, 28)

            # get the file names under the directory selected
            dicom_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
            if dicom_dir != "":
                # update the progress bar
                self.pbar.setValue(0)
                self.pbar.setVisible(True)
                # get the list of DICOM files in the selected directory
                dicom_files = glob.glob('{}/**/*.dcm'.format(dicom_dir), recursive=True)
                if len(dicom_files) > 0:
                    # set up the anon directory
                    ANON_DIR = dicom_dir + '_ANON'
                    if os.path.exists(ANON_DIR):
                        shutil.rmtree(ANON_DIR)
                    os.makedirs(ANON_DIR)
                    # step through the files and replace the identifiable fields in each one
                    invalid_file_count = 0
                    for idx,f in enumerate(dicom_files):
                        # replicate the directory structure under the anon folder
                        dirname = os.path.dirname(f)
                        basename = os.path.basename(f)
                        anon_dirname = dirname.replace(dicom_dir, ANON_DIR)
                        output_dicom_filename = '{}/{}'.format(anon_dirname, basename)
                        # make sure the output file's subdirectory exists
                        if not os.path.exists(anon_dirname):
                            os.makedirs(anon_dirname)
                        # load and process the file
                        try:
                            ds = dcmread(f)
                        except Exception as e:
                            print(e)
                            invalid_file_count += 1
                        else:
                            ds = self.anonymise_image(ds, current_date, current_time, patient_birth_month, patient_birth_day)
                            ds.save_as(output_dicom_filename)
                        # update the progress bar
                        proportion_completed = int((idx+1)/len(dicom_files)*100)
                        self.pbar.setValue(proportion_completed)
                        # process GUI events to reflect the update value
                        QApplication.processEvents()

                    print('there were {} invalid files ({} files in total)'.format(invalid_file_count, len(dicom_files)))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    widget = DicomAnonWidget()
    widget.show()
    sys.exit(app.exec())
