#!/usr/bin/env python
import os
import re
import pandas as pd
import configparser
from jinja2 import Environment, FileSystemLoader

def config_to_dict(config):
    result = {}
    for section_name in config.sections():
        section_dict = {}
        for key, value in config[section_name].items():
            section_dict[key] = value
        result[section_name] = section_dict
    return result

def get_subject_list(out_dir):
    slices_dir = os.path.join(out_dir, 'slices')
    if not os.path.exists(slices_dir):
        os.makedirs(slices_dir)
        return []
    subjects = set()
    for filename in os.listdir(slices_dir):
        if filename.endswith('.jpg'):
            subject_id = filename.split('_')[0]
            if subject_id.startswith('sub-'):
                subject_id = subject_id[4:]
            subjects.add(subject_id)
    return sorted(list(subjects))

def get_subject_data(out_dir, subject_id):
    slices_dir = os.path.join(out_dir, 'slices')
    lesions = {}
    pattern = re.compile(rf'^(sub-)?{re.escape(subject_id)}_(\d+)_(\d+)\.jpg$')
    tsv_file = os.path.join(out_dir, 'lesion_comparison_results.tsv')
    df = pd.read_csv(tsv_file, sep='\t')
    for filename in os.listdir(slices_dir):
        match = pattern.match(filename)
        if match:
            lesion_num = match.group(2)
            lesion_id = f"{subject_id}_{lesion_num}"
            if lesion_id not in lesions:
                lesions[lesion_id] = {'slices': [], 'multiple_matches': ''}
            lesions[lesion_id]['slices'].append(filename)
            lesions[lesion_id]['slices'].sort()
            multiple_matches = df[df['Lesion ID'] == lesion_id]['Multiple Matches'].values
            if len(multiple_matches) > 0 and pd.notna(multiple_matches[0]):
                lesions[lesion_id]['multiple_matches'] = multiple_matches[0]
    return {'subject_id': subject_id, 'lesions': lesions}

def main():
    config = configparser.ConfigParser()
    config.read('temp_config.ini')
    full_config = config_to_dict(config)
    out_dir = config['PATHS']['out_dir']
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
    static_html_dir = os.path.join(out_dir, 'static_html')
    os.makedirs(static_html_dir, exist_ok=True)
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    subjects = get_subject_list(out_dir)
    index_template = env.get_template('index.html')
    rendered_index = index_template.render(subjects=subjects, config=full_config)
    index_path = os.path.join(static_html_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(rendered_index)
    print(f"Generated index page at {index_path}")

    import shutil
    src_static = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
    dst_static = os.path.join(out_dir, 'static')
    if not os.path.exists(dst_static):
        shutil.copytree(src_static, dst_static)

    
    subject_template = env.get_template('view_subject.html')
    for subject in subjects:
        subject_data = get_subject_data(out_dir, subject)
        rendered_subject = subject_template.render(subject=subject_data, config=full_config)
        subject_filename = f"subject_{subject}.html"
        subject_path = os.path.join(static_html_dir, subject_filename)
        with open(subject_path, 'w', encoding='utf-8') as f:
            f.write(rendered_subject)
        print(f"Generated page for subject {subject} at {subject_path}")
    print("Static HTML generation complete.")

if __name__ == "__main__":
    main()
