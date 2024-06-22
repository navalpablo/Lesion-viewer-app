from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import pandas as pd
from werkzeug.utils import secure_filename
import configparser

app = Flask(__name__)

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

OUT_DIR = config.get('PATHS', 'OUT_DIR')
ANNOTATIONS_FILE = os.path.join(OUT_DIR, 'annotations.tsv')

app.config['HTML_GENERATION'] = dict(config['HTML_GENERATION'])

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

    return jsonify({'status': 'success', 'message': 'Annotations saved successfully'})

@app.route('/slices/<path:filename>')
def serve_slice(filename):
    return send_from_directory(os.path.join(OUT_DIR, 'slices'), filename)

def get_subject_list():
    slices_dir = os.path.join(OUT_DIR, 'slices')
    subjects = set()
    for filename in os.listdir(slices_dir):
        if filename.endswith('.jpg'):
            subject_id = filename.split('_')[0]
            subjects.add(subject_id)
    return sorted(list(subjects))

def get_subject_data(subject_id):
    slices_dir = os.path.join(OUT_DIR, 'slices')
    lesions = {}
    for filename in os.listdir(slices_dir):
        if filename.startswith(subject_id) and filename.endswith('.jpg'):
            lesion_id = '_'.join(filename.split('_')[:-1])
            if lesion_id not in lesions:
                lesions[lesion_id] = []
            lesions[lesion_id].append(filename)

    for lesion_id in lesions:
        lesions[lesion_id].sort()

    return {
        'subject_id': subject_id,
        'lesions': lesions
    }

if __name__ == '__main__':
    app.run(debug=True)