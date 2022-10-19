import sys
import glob
import os
import shutil
from deid.dicom import get_files, get_identifiers, replace_identifiers
from deid.config import DeidRecipe
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar, QVBoxLayout, QApplication, QFileDialog, QGroupBox, QLineEdit, QLabel, QGridLayout

patientName = 'Fred Nerk'


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

    def generate_uid(item, value, field, dicom):
        '''This function will generate a uuid! You can expect it to be passed
        the dictionary of items extracted from the dicom (and your function)
        and variables, the original value (func:generate_uid) and the field
        name you are applying it to.
        '''
        import uuid
        # a field can either be just the name string, or a DicomElement
        if hasattr(field, 'name'):
            field = field.name
        prefix = field.lower().replace(' ', '')
        # return prefix + "-" + str(uuid.uuid4())
        return prefix+'-boo!'

    def anon_button_clicked(self):
        global patientName

        # make a copy of the patient data
        patientName = self.givenNameEdit.text() + ' ' + self.familyNameEdit.text()
        # get the file names
        dicom_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        # get the list of DICOM files in the selected directory
        dicom_files = list(get_files(dicom_dir, check=True))
        print('there are {} valid files'.format(len(dicom_files)))
        if len(dicom_files) > 0:
            updated_ids = dict();
            # set up the anon directory
            ANON_DIR = dicom_dir + '_ANON'
            if os.path.exists(ANON_DIR):
                shutil.rmtree(ANON_DIR)
            os.makedirs(ANON_DIR)
            # load the recipe
            recipe = DeidRecipe('deid.dicom')
            # get the identifiers
            ids = get_identifiers(dicom_files)
            for image, fields in ids.items():
                for field in fields:
                    if hasattr(field, 'name'):
                        field = field.name
                    print(field)
                # fields['generate_uid'] = self.generate_uid
                # fields['patient_name'] = 'this is the new patient name'
                # updated_ids[image] = fields
            # clean the files
            # cleaned_files = replace_identifiers(dicom_files=dicom_files,
            #                         deid=recipe,
            #                         ids=updated_ids)
            # print(cleaned_files[0])



if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = DicomAnonWidget()
    widget.show()
    sys.exit(app.exec())
