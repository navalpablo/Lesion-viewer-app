import os
import re
import csv
import logging
import configparser
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_from_directory
from threading import Timer
import webbrowser

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define paths relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Create the Flask app
app = Flask(__name__,
            template_folder=os.path.join(parent_dir, 'templates'),
            static_folder=os.path.join(parent_dir, 'static'))

import argparse

# Add argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, required=True, help='Path to configuration file')
args = parser.parse_args()
config = configparser.ConfigParser()
config_loaded = config.read(args.config)

if not config_loaded:
    raise FileNotFoundError(f"Could not load configuration file: {args.config}")

# Update Flask's config with the settings from the config file
for section in config.sections():
    app.config[section] = dict(config.items(section))

try:
    # Set the output directory and annotations CSV file using the loaded config
    OUT_DIR = config.get('PATHS', 'out_dir')
    ANNOTATIONS_CSV = os.path.join(OUT_DIR, 'annotations.csv')
except configparser.NoSectionError:
    raise ValueError("Configuration file is missing required 'PATHS' section")
except configparser.NoOptionError as e:
    raise ValueError(f"Configuration file is missing required option: {str(e)}")

logger.debug(f"Config file loaded: {args.config}")
logger.debug(f"OUT_DIR: {OUT_DIR}")
logger.debug(f"ANNOTATIONS_CSV: {ANNOTATIONS_CSV}")
    
##############################
#         ROUTES             #
##############################

@app.route('/')
def index():
    subjects = get_subject_list()
    return render_template('index.html', subjects=subjects)

@app.route('/view/<subject_id>')
def view_subject(subject_id):
    subject_data = get_subject_data(subject_id)
    return render_template('view_subject.html', subject=subject_data)

@app.route('/save_annotations', methods=['POST'])
def save_annotations():
    """
    Receives JSON with "subject_id" and "annotations" (a dict).
    Appends each annotation as a new row to a single CSV file in OUT_DIR.
    """
    try:
        data = request.get_json()
        subject_id = data.get('subject_id')
        annotations = data.get('annotations')

        if not subject_id or not annotations:
            return jsonify({'status': 'error', 'message': 'Missing subject_id or annotations'}), 400

        file_exists = os.path.exists(ANNOTATIONS_CSV)
        with open(ANNOTATIONS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['Subject', 'Lesion', 'Annotation'])
            for lesion_id, annotation_value in annotations.items():
                writer.writerow([subject_id, lesion_id, annotation_value])

        logger.info(f"Annotations appended to {ANNOTATIONS_CSV}")
        return jsonify({'status': 'success', 'message': 'Annotations saved successfully'})
    except Exception as e:
        logger.error(f"Error saving annotations: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error saving annotations: {str(e)}'}), 500

@app.route('/slices/<path:filename>')
def serve_slice(filename):
    """
    Serve slice images from OUT_DIR/slices.
    """
    logger.debug(f"Requested slice: {filename}")
    slices_dir = os.path.abspath(os.path.join(current_dir, '..', OUT_DIR, 'slices'))
    full_path = os.path.join(slices_dir, filename)

    if os.path.exists(full_path):
        return send_from_directory(slices_dir, filename)
    else:
        # Try adding 'sub-' prefix if necessary
        if not filename.startswith('sub-'):
            alt_path = os.path.join(slices_dir, f"sub-{filename}")
            if os.path.exists(alt_path):
                return send_from_directory(slices_dir, f"sub-{filename}")
        logger.error(f"File not found: {full_path}")
        return "File not found", 404

@app.route('/static_html/<path:filename>')
def serve_static_html(filename):
    """
    Serve pre-generated static HTML pages from OUT_DIR/static_html.
    """
    static_html_dir = os.path.join(OUT_DIR, 'static_html')
    full_path = os.path.join(static_html_dir, filename)
    if os.path.exists(full_path):
        return send_from_directory(static_html_dir, filename)
    else:
        logger.error(f"Static HTML not found: {full_path}")
        return "File not found", 404

##############################
#    HELPER FUNCTIONS        #
##############################

def get_subject_list():
    """
    Scan the slices directory for unique subjects.
    """
    slices_dir = os.path.abspath(os.path.join(current_dir, '..', OUT_DIR, 'slices'))
    if not os.path.exists(slices_dir):
        os.makedirs(slices_dir)
        return []
    subjects = set()
    for filename in os.listdir(slices_dir):
        if filename.endswith('.jpg'):
            subj_id = filename.split('_')[0]
            if subj_id.startswith('sub-'):
                subj_id = subj_id[4:]
            subjects.add(subj_id)
    return sorted(list(subjects))

def get_subject_data(subject_id):
    """
    Gather all lesion slices for a subject and include multiple match info if available.
    """
    slices_dir = os.path.abspath(os.path.join(current_dir, '..', OUT_DIR, 'slices'))
    lesions = {}
    pattern = re.compile(rf'^(sub-)?{re.escape(subject_id)}_(\d+)_(\d+)\.jpg$')

    tsv_file = os.path.join(OUT_DIR, 'lesion_comparison_results.tsv')
    if os.path.exists(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t')
    else:
        df = pd.DataFrame(columns=['Lesion ID', 'Multiple Matches'])

    for filename in os.listdir(slices_dir):
        match = pattern.match(filename)
        if match:
            lesion_num = match.group(2)
            lesion_id = f"{subject_id}_{lesion_num}"
            if lesion_id not in lesions:
                lesions[lesion_id] = {'slices': [], 'multiple_matches': ''}
            lesions[lesion_id]['slices'].append(filename)
            row = df[df['Lesion ID'] == lesion_id]
            if len(row) > 0 and 'Multiple Matches' in df.columns:
                mm_value = row['Multiple Matches'].values[0]
                if pd.notna(mm_value):
                    lesions[lesion_id]['multiple_matches'] = mm_value
    return {'subject_id': subject_id, 'lesions': lesions}

def open_browser():
    """
    Automatically open the static HTML index page.
    NOTE: Make sure your GUI calls the URL "http://127.0.0.1:5000/static_html/index.html"
    so that requests (like /save_annotations) reach this server.
    """
    url = "http://127.0.0.1:5000/static_html/index.html"
    webbrowser.open_new(url)

##############################
#         MAIN RUNNER        #
##############################

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)
