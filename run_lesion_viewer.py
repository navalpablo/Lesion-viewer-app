import os
import configparser
import subprocess
import argparse

def create_config(workdir, base_dir, in_plane_margin, slice_margin):
    config = configparser.ConfigParser()
    
    config['PATHS'] = {
        'BASE_DIR': base_dir,
        'WORK_DIR': workdir,
        'OUT_DIR': os.path.join(workdir, 'html'),
        'MATCHED_TSV_FILE': os.path.join(workdir, 'lesion_comparison_results.tsv'),
        'ANNOTATIONS_FILE': os.path.join(workdir, 'annotations.tsv')
    }

    config['IMAGE_PROCESSING'] = {
        'SLICE_FIGURE_SIZE': '15,5',
        'T1_COLORMAP': 'gray',
        'MASK_ALPHA': '0.5',
        'IN_PLANE_MARGIN': str(in_plane_margin),
        'SLICE_MARGIN': str(slice_margin)
    }

    config['HTML_GENERATION'] = {
        'BOOTSTRAP_CSS_URL': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
        'JQUERY_URL': 'https://code.jquery.com/jquery-3.3.1.slim.min.js',
        'POPPER_URL': 'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js',
        'BOOTSTRAP_JS_URL': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js'
    }

    config_path = os.path.join(workdir, 'config.ini')
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    return config_path

def run_match_lesions(base_dir, config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    output_tsv = config['PATHS']['MATCHED_TSV_FILE']
    subprocess.run(['python', 'match_lesions.py', base_dir, output_tsv])

def run_image_processing(config_path):
    subprocess.run(['python', 'image_processing.py', '--config', config_path])

def run_flask_app(config_path):
    subprocess.run(['python', 'app.py', '--config', config_path])


def main():
    parser = argparse.ArgumentParser(description="""
    Lesion Viewer Workflow

    This script orchestrates the process of matching lesions, processing images,
    and running the Flask application for lesion viewing and annotation.

    The base directory should have the following structure:
    $base_dir/$subject_dir/underlay.nii.gz
    $base_dir/$subject_dir/Reader_1/$lesion.nii.gz
    $base_dir/$subject_dir/Reader_2/$lesion.nii.gz (optional)
    """, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("base_dir", help="Base directory containing subject folders")
    parser.add_argument("work_dir", help="Working directory for intermediate files and output")
    parser.add_argument("--step", choices=['match', 'process', 'view'], 
                        help="Run a specific step: match (lesion matching), process (image processing), or view (start Flask app)")
    parser.add_argument("--in-plane-margin", type=int, default=50, 
                        help="In-plane margin for image processing (default: 50)")
    parser.add_argument("--slice-margin", type=int, default=5, 
                        help="Slice margin for image processing (default: 5)")
    args = parser.parse_args()

    # Create working directory if it doesn't exist
    os.makedirs(args.work_dir, exist_ok=True)

    print("Creating config file...")
    config_path = create_config(args.work_dir, args.base_dir, args.in_plane_margin, args.slice_margin)

    if args.step == 'match' or args.step is None:
        print("Matching lesions...")
        run_match_lesions(args.base_dir, config_path)

    if args.step == 'process' or args.step is None:
        print("Processing images...")
        run_image_processing(config_path)

    if args.step == 'view' or args.step is None:
        print("Starting Flask application...")
        run_flask_app(config_path)

if __name__ == '__main__':
    main()