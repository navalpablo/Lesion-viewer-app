import sys
import os
import subprocess
import configparser
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QFileDialog, QMessageBox
)
from PyQt5.QtCore import QSettings, QCoreApplication
from PyQt5.QtGui import QIcon
import webbrowser

class LesionViewerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('static/images/icon.ico'))
        QCoreApplication.setOrganizationName("BV-RADS")
        QCoreApplication.setApplicationName("LesionViewer")
        self.settings = QSettings()
        self.initUI()
        self.loadSettings()

    def initUI(self):
        layout = QVBoxLayout()

        # -- Subject Directory --
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel('Subject Directory:'))
        self.input_edit = QLineEdit()
        input_layout.addWidget(self.input_edit)
        input_button = QPushButton('Browse')
        input_button.clicked.connect(lambda: self.browse_directory(self.input_edit))
        input_layout.addWidget(input_button)
        layout.addLayout(input_layout)

        # -- Output Directory --
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('Output Directory:'))
        self.output_edit = QLineEdit()
        output_layout.addWidget(self.output_edit)
        output_button = QPushButton('Browse')
        output_button.clicked.connect(lambda: self.browse_directory(self.output_edit))
        output_layout.addWidget(output_button)
        layout.addLayout(output_layout)

        # -- In-plane Margin --
        in_plane_layout = QHBoxLayout()
        in_plane_layout.addWidget(QLabel('In-plane Margin:'))
        self.in_plane_edit = QLineEdit()
        self.in_plane_edit.setPlaceholderText("Default: 50")
        in_plane_layout.addWidget(self.in_plane_edit)
        layout.addLayout(in_plane_layout)

        # -- Slice Margin --
        slice_layout = QHBoxLayout()
        slice_layout.addWidget(QLabel('Slice Margin:'))
        self.slice_edit = QLineEdit()
        self.slice_edit.setPlaceholderText("Default: 5")
        slice_layout.addWidget(self.slice_edit)
        layout.addLayout(slice_layout)

        # -- Preprocessing checkboxes --
        layout.addWidget(QLabel('Choose preprocessing steps:'))
        self.isolate_check = QCheckBox('Isolate Lesions')
        self.match_check = QCheckBox('Match Lesions')
        self.process_check = QCheckBox('Process Images')
        self.static_check = QCheckBox('Generate Static HTML')  # NEW CHECKBOX

        layout.addWidget(self.isolate_check)
        layout.addWidget(self.match_check)
        layout.addWidget(self.process_check)
        layout.addWidget(self.static_check)

        # -- Execute preprocessing button --
        preprocess_button = QPushButton('Execute Preprocessing')
        preprocess_button.clicked.connect(self.execute_preprocessing)
        layout.addWidget(preprocess_button)

        # -- Open viewer button --
        open_viewer_button = QPushButton('Open Viewer (after preprocessing)')
        open_viewer_button.clicked.connect(self.open_viewer)
        layout.addWidget(open_viewer_button)

        # -- Help button --
        help_button = QPushButton('Help')
        help_button.clicked.connect(self.show_help)
        layout.addWidget(help_button)

        self.setLayout(layout)
        self.setWindowTitle('Lesion Viewer')
        self.show()

    def loadSettings(self):
        self.input_edit.setText(self.settings.value("input_directory", ""))
        self.output_edit.setText(self.settings.value("output_directory", ""))
        self.in_plane_edit.setText(self.settings.value("in_plane_margin", ""))
        self.slice_edit.setText(self.settings.value("slice_margin", ""))
        self.isolate_check.setChecked(self.settings.value("isolate_lesions", False, type=bool))
        self.match_check.setChecked(self.settings.value("match_lesions", False, type=bool))
        self.process_check.setChecked(self.settings.value("process_images", False, type=bool))
        self.static_check.setChecked(self.settings.value("static_html", False, type=bool))

    def saveSettings(self):
        self.settings.setValue("input_directory", self.input_edit.text())
        self.settings.setValue("output_directory", self.output_edit.text())
        self.settings.setValue("in_plane_margin", self.in_plane_edit.text())
        self.settings.setValue("slice_margin", self.slice_edit.text())
        self.settings.setValue("isolate_lesions", self.isolate_check.isChecked())
        self.settings.setValue("match_lesions", self.match_check.isChecked())
        self.settings.setValue("process_images", self.process_check.isChecked())
        self.settings.setValue("static_html", self.static_check.isChecked())

    def closeEvent(self, event):
        if hasattr(self, 'flask_process'):
            self.flask_process.terminate()
        self.saveSettings()
        super().closeEvent(event)

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

        # Create config in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'temp_config.ini')
        
        try:
            self.create_config(base_dir, out_dir, config_path)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to create config file: {str(e)}")
            return

        # Build the steps array from the checkboxes
        steps = []
        if self.isolate_check.isChecked():
            steps.append('isolate')
        if self.match_check.isChecked():
            steps.append('match')
        if self.process_check.isChecked():
            steps.append('process')
        if self.static_check.isChecked():
            steps.append('static')

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
        # Create full paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_py_path = os.path.join(current_dir, 'scripts', 'app.py')
        config_path = os.path.join(current_dir, 'temp_config.ini')
        
        # Always update the config file with the current GUI settings
        base_dir = self.input_edit.text()
        out_dir = self.output_edit.text()
        self.create_config(base_dir, out_dir, config_path)
        
        try:
            # Pass the updated config path as an argument to app.py
            self.flask_process = subprocess.Popen([
                sys.executable, 
                app_py_path,
                '--config', 
                config_path
            ])
            
            # Allow some time for Flask to start up
            time.sleep(5)
            
            # Verify that the server is running
            import requests
            try:
                requests.get("http://127.0.0.1:5000/")
            except requests.exceptions.ConnectionError:
                QMessageBox.critical(self, "Error", "Could not connect to viewer server. Please try again.")
                self.flask_process.terminate()
                return
            
            # Open the static HTML index in the default browser
            url = "http://127.0.0.1:5000/static_html/index.html"
            webbrowser.open(url)
            QMessageBox.information(self, "Viewer Opened", "Static HTML viewer has been opened in your browser.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch viewer server: {str(e)}")


            
    def create_config(self, base_dir, out_dir, config_path):
        config = configparser.ConfigParser()
        
        config['PATHS'] = {
            'BASE_DIR': base_dir,
            'OUT_DIR': out_dir,
            'TSV_FILE': os.path.join(out_dir, 'lesion_comparison_results.tsv'),
            'ANNOTATIONS_FILE': os.path.join(out_dir, 'annotations.tsv')
        }
        
        config['IMAGE_PROCESSING'] = {
            'SLICE_FIGURE_SIZE': '15,5',
            'T1_COLORMAP': 'gray',
            'MARC_MASK_COLORMAP': 'Reds',
            'ALBERT_MASK_COLORMAP': 'Blues',
            'MASK_ALPHA': '0.5',
            'IN_PLANE_MARGIN': self.in_plane_edit.text() or '50',
            'SLICE_MARGIN': self.slice_edit.text() or '5'
        }
        
        config['HTML_GENERATION'] = {
            'BOOTSTRAP_CSS_URL': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
            'JQUERY_URL': 'https://code.jquery.com/jquery-3.3.1.slim.min.js',
            'POPPER_URL': 'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js',
            'BOOTSTRAP_JS_URL': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js'
        }
        
        config['MULTIPROCESSING'] = {
            'NUM_PROCESSES': '0'
        }
        
        # Ensure the directory exists
        config_dir = os.path.dirname(config_path)
        if config_dir:  # Only create directory if path has a directory component
            os.makedirs(config_dir, exist_ok=True)
        
        # Write the config file
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        
        print(f"Created config file at: {config_path}")
        print("Config contents:")
        with open(config_path, 'r') as f:
            print(f.read())

    def show_help(self):
        help_text = """
Lesion Viewer Help

This application processes and views brain lesion images.

1. Subject Directory: Select the directory containing subject folders with lesion data.
2. Output Directory: Choose where processed images and results will be saved.
3. In-plane Margin: Set the in-plane margin for image processing (default: 50).
4. Slice Margin: Set the slice margin for image processing (default: 5).

Preprocessing Options:
- Isolate Lesions: Separates individual lesions from input masks.
- Match Lesions: Compares lesions between different readers.
- Process Images: Prepares images for viewing.
- Generate Static HTML: Renders static HTML pages into output/static_html.

Execution:
1. Click 'Execute Preprocessing' to run selected steps.
2. If you generated static HTML, click 'Open Viewer' to launch the static viewer in your web browser.
        """
        QMessageBox.information(self, "Help", help_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LesionViewerGUI()
    sys.exit(app.exec_())
