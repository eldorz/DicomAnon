import sys
import glob
import os
import shutil
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar, QVBoxLayout, QApplication, QFileDialog, QGroupBox, QLineEdit, QLabel, QGridLayout
from pydicom import dcmread
import datetime
import random


class DicomAnonWidget(QWidget):
    def __init__(self):
        super(DicomAnonWidget, self).__init__()
        self.setWindowTitle('DICOM Anonymiser')
        self.anon_button = QPushButton('Anonymise!')
        self.anon_button.clicked.connect(self.anon_button_clicked)

        self.pbar = QProgressBar(self)
        self.pbar.setValue(0)
        self.pbar.setTextVisible(True)

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

    def anon_button_clicked(self):
        # get the file names
        dicom_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        print(dicom_dir)
        # get the current time
        d = datetime.datetime.now()
        current_date = d.strftime("%Y%m%d")
        current_time = d.strftime("%H%M%S.%f")
        # get the list of DICOM files in the selected directory
        dicom_files = glob.glob('{}/**/*.dcm'.format(dicom_dir), recursive=True)
        print('there are {} files'.format(len(dicom_files)))
        if len(dicom_files) > 0:
            # set up the anon directory
            ANON_DIR = dicom_dir + '_ANON'
            if os.path.exists(ANON_DIR):
                shutil.rmtree(ANON_DIR)
            os.makedirs(ANON_DIR)
            # step through the files and replace the identifiable fields in each one
            for f in dicom_files:
                dicom_filename = os.path.basename(f)
                ds = dcmread(f)
                
                ds.PatientName = '{} {}'.format(self.givenNameEdit.text(), self.familyNameEdit.text())
                ds.PatientID = self.patientIDEdit.text()
                patientBirthYear = datetime.datetime.strptime(ds.PatientBirthDate, "%Y%m%d").year
                ds.PatientBirthDate = datetime.datetime(patientBirthYear, random.randint(1, 12), random.randint(1, 28))
                ds.PatientBirthTime = current_time
                ds.PatientSex = 'O'
                ds.PatientAddress = 'Anonymised'
                ds.PatientMotherBirthName = 'Anonymised'
                ds.EthnicGroup = 'Anonymised'

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

                ds.save_as('{}/{}'.format(ANON_DIR, dicom_filename))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = DicomAnonWidget()
    widget.show()
    sys.exit(app.exec())
