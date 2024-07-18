import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFileDialog, QMessageBox

class LesionViewerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Input directory
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel('Subject Directory:'))
        self.input_edit = QLineEdit()
        input_layout.addWidget(self.input_edit)
        input_button = QPushButton('Browse')
        input_button.clicked.connect(lambda: self.browse_directory(self.input_edit))
        input_layout.addWidget(input_button)
        layout.addLayout(input_layout)

        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('Output Directory:'))
        self.output_edit = QLineEdit()
        output_layout.addWidget(self.output_edit)
        output_button = QPushButton('Browse')
        output_button.clicked.connect(lambda: self.browse_directory(self.output_edit))
        output_layout.addWidget(output_button)
        layout.addLayout(output_layout)

        # Preprocessing options
        layout.addWidget(QLabel('Choose preprocessing steps:'))
        self.isolate_check = QCheckBox('Isolate Lesions')
        self.match_check = QCheckBox('Match Lesions')
        self.process_check = QCheckBox('Process Images')
        layout.addWidget(self.isolate_check)
        layout.addWidget(self.match_check)
        layout.addWidget(self.process_check)

        # Execute preprocessing button
        preprocess_button = QPushButton('Execute Preprocessing')
        preprocess_button.clicked.connect(self.execute_preprocessing)
        layout.addWidget(preprocess_button)

        # Open viewer button
        open_viewer_button = QPushButton('Open Viewer (after preprocessing')
        open_viewer_button.clicked.connect(self.open_viewer)
        layout.addWidget(open_viewer_button)

        # Help button
        help_button = QPushButton('Help')
        help_button.clicked.connect(self.show_help)
        layout.addWidget(help_button)

        self.setLayout(layout)
        self.setWindowTitle('Lesion Viewer')
        self.show()

    def browse_directory(self, line_edit):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            line_edit.setText(directory)

    def execute_preprocessing(self):
        base_dir = self.input_edit.text()
        out_dir = self.output_edit.text()

        if not base_dir or not out_dir:
            QMessageBox.warning(self, "Error", "Please specify both input and output directories.")
            return

        config_path = os.path.join(out_dir, 'temp_config.ini')
        self.create_config(base_dir, out_dir, config_path)

        steps = []
        if self.isolate_check.isChecked():
            steps.append('isolate')
        if self.match_check.isChecked():
            steps.append('match')
        if self.process_check.isChecked():
            steps.append('process')

        if not steps:
            QMessageBox.warning(self, "Error", "Please select at least one preprocessing step.")
            return

        command = [sys.executable, 'Lesion_viewer.py', '--base_path', base_dir, '--output', out_dir, '--steps'] + steps

        try:
            subprocess.run(command, check=True)
            QMessageBox.information(self, "Success", "Preprocessing complete.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"An error occurred during preprocessing: {str(e)}")

    def open_viewer(self):
        out_dir = self.output_edit.text()
        if not out_dir:
            QMessageBox.warning(self, "Error", "Please specify the output directory.")
            return

        config_path = os.path.join(out_dir, 'temp_config.ini')
        if not os.path.exists(config_path):
            QMessageBox.warning(self, "Error", "Configuration file not found. Please run preprocessing first.")
            return

        command = [sys.executable, os.path.join('scripts', 'app.py')]

        try:
            subprocess.Popen(command)
            QMessageBox.information(self, "Success", "Web viewer launched. Please check your default web browser.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"An error occurred while launching the viewer: {str(e)}")

    def create_config(self, base_dir, out_dir, config_path):
        config_content = f"""[PATHS]
BASE_DIR = {base_dir}
OUT_DIR = {out_dir}
TSV_FILE = {os.path.join(out_dir, 'lesion_comparison_results.tsv')}
ANNOTATIONS_FILE = {os.path.join(out_dir, 'annotations.tsv')}

[IMAGE_PROCESSING]
SLICE_FIGURE_SIZE = 15,5
T1_COLORMAP = gray
MARC_MASK_COLORMAP = Reds
ALBERT_MASK_COLORMAP = Blues
MASK_ALPHA = 0.5
IN_PLANE_MARGIN = 50
SLICE_MARGIN = 5

[HTML_GENERATION]
BOOTSTRAP_CSS_URL = https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css
JQUERY_URL = https://code.jquery.com/jquery-3.3.1.slim.min.js
POPPER_URL = https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js
BOOTSTRAP_JS_URL = https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js

[MULTIPROCESSING]
NUM_PROCESSES = 0
"""
        with open(config_path, 'w') as f:
            f.write(config_content)

    def show_help(self):
        help_text = """
Lesion Viewer Help

This application processes and views brain lesion images.

1. Subject Directory: Select the directory containing subject folders with lesion data.
2. Output Directory: Choose where processed images and results will be saved.

Preprocessing Options:
- Isolate Lesions: Separates individual lesions from input masks.
- Match Lesions: Compares lesions between different readers.
- Process Images: Prepares images for web viewing.

Execution:
1. Click 'Execute Preprocessing' to run selected preprocessing steps.
2. Once preprocessing is complete, click 'Open Viewer' to launch the web viewer.

File Structure:
Subject directory should contain subject folders (e.g., sub-001, sub-002) with:
- Reader_1_mask.nii.gz
- Reader_2_mask.nii.gz
- Underlay.nii.gz

Output:
- Processed lesion files
- Comparison results (TSV)
- Web-viewable image slices
- Annotations file

Web Viewer:
Allows viewing and annotating processed lesion images in a web browser.
        """
        QMessageBox.information(self, "Help", help_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LesionViewerGUI()
    sys.exit(app.exec_())