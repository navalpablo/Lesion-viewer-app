from flask import Flask, render_template, request, jsonify, send_from_directory
import re
import os
import pandas as pd
from werkzeug.utils import secure_filename
import configparser
import logging
import webbrowser
from threading import Timer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

app = Flask(__name__, 
            template_folder=os.path.join(parent_dir, 'templates'),
            static_folder=os.path.join(parent_dir, 'static'))

# Load configuration
config = configparser.ConfigParser()
config.read(os.path.join(parent_dir, 'temp_config.ini'))

OUT_DIR = config.get('PATHS', 'out_dir')
ANNOTATIONS_FILE = config.get('PATHS', 'annotations_file')

app.config['HTML_GENERATION'] = dict(config['HTML_GENERATION'])

logger.debug(f"OUT_DIR: {OUT_DIR}")
logger.debug(f"ANNOTATIONS_FILE: {ANNOTATIONS_FILE}")

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
    try:
        data = request.json
        subject_id = data.get('subject_id')
        annotations = data.get('annotations')

        if not all([subject_id, annotations]):
            return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

        try:
            df = pd.read_csv(ANNOTATIONS_FILE, sep='\t')
        except FileNotFoundError:
            df = pd.DataFrame(columns=['lesion_id', 'subject_id', 'annotation'])

        for lesion_id, annotation in annotations.items():
            mask = (df['lesion_id'] == lesion_id) & (df['subject_id'] == subject_id)
            if mask.any():
                df.loc[mask, 'annotation'] = annotation
            else:
                new_row = pd.DataFrame([[lesion_id, subject_id, annotation]], 
                                       columns=['lesion_id', 'subject_id', 'annotation'])
                df = pd.concat([df, new_row], ignore_index=True)

        df.to_csv(ANNOTATIONS_FILE, sep='\t', index=False)
        logger.info(f"Annotations saved successfully to {ANNOTATIONS_FILE}")
        return jsonify({'status': 'success', 'message': 'Annotations saved successfully'})
    except Exception as e:
        logger.error(f"Error saving annotations: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error saving annotations: {str(e)}'}), 500

@app.route('/slices/<path:filename>')
def serve_slice(filename):
    logger.debug(f"Requested file: {filename}")
    
    # Get the absolute path of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the full path to the slices directory
    slices_dir = os.path.abspath(os.path.join(current_dir, '..', OUT_DIR, 'slices'))
    
    full_path = os.path.join(slices_dir, filename)
    logger.debug(f"Full path: {full_path}")
    
    if os.path.exists(full_path):
        logger.debug(f"File found: {full_path}")
        return send_from_directory(slices_dir, filename)
    else:
        # If not found, try adding 'sub-' prefix
        if not filename.startswith('sub-'):
            full_path_with_sub = os.path.join(slices_dir, f"sub-{filename}")
            logger.debug(f"Attempting to serve file with 'sub-' prefix: {full_path_with_sub}")
            if os.path.exists(full_path_with_sub):
                return send_from_directory(slices_dir, f"sub-{filename}")
        
        logger.error(f"File not found: {full_path}")
        return "File not found", 404

def get_subject_list():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    slices_dir = os.path.abspath(os.path.join(current_dir, '..', OUT_DIR, 'slices'))
    if not os.path.exists(slices_dir):
        os.makedirs(slices_dir)
        return []
    subjects = set()
    for filename in os.listdir(slices_dir):
        if filename.endswith('.jpg'):
            subject_id = filename.split('_')[0]
            if subject_id.startswith('sub-'):
                subject_id = subject_id[4:]  # Remove 'sub-' prefix
            subjects.add(subject_id)
    return sorted(list(subjects))



def get_subject_data(subject_id):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    slices_dir = os.path.abspath(os.path.join(current_dir, '..', OUT_DIR, 'slices'))
    logger.debug(f"Looking for files in: {slices_dir}")
    lesions = {}
    
    pattern = re.compile(rf'^(sub-)?{re.escape(subject_id)}_(\d+)_(\d+)\.jpg$')
    
    # Load the TSV file
    tsv_file = os.path.join(OUT_DIR, 'lesion_comparison_results.tsv')
    df = pd.read_csv(tsv_file, sep='\t')
    
    for filename in os.listdir(slices_dir):
        logger.debug(f"Checking file: {filename}")
        match = pattern.match(filename)
        if match:
            lesion_num = match.group(2)
            lesion_id = f"{subject_id}_{lesion_num}"
            
            if lesion_id not in lesions:
                lesions[lesion_id] = {
                    'slices': [],
                    'multiple_matches': ''
                }
            lesions[lesion_id]['slices'].append(filename)
            
            # Get multiple matches information
            multiple_matches = df[df['Lesion ID'] == lesion_id]['Multiple Matches'].values
            if len(multiple_matches) > 0 and pd.notna(multiple_matches[0]):
                lesions[lesion_id]['multiple_matches'] = multiple_matches[0]
            
            logger.debug(f"Added {filename} to lesion {lesion_id}")

    logger.debug(f"Found lesions: {lesions}")

    return {
        'subject_id': subject_id,
        'lesions': lesions
    }
    
def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)