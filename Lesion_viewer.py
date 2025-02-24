import argparse
import os
import configparser
import subprocess
import sys

# Add the scripts directory to the Python path
scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
sys.path.append(scripts_dir)

def create_temp_config(base_path, out_dir, tsv_file, annotations_file):
    config = configparser.ConfigParser()
    
    config['PATHS'] = {
        'BASE_DIR': base_path,
        'OUT_DIR': out_dir,
        'TSV_FILE': tsv_file,
        'ANNOTATIONS_FILE': annotations_file
    }
    
    config['IMAGE_PROCESSING'] = {
        'SLICE_FIGURE_SIZE': '15,5',
        'T1_COLORMAP': 'gray',
        'MARC_MASK_COLORMAP': 'Reds',
        'ALBERT_MASK_COLORMAP': 'Blues',
        'MASK_ALPHA': '0.5',
        'IN_PLANE_MARGIN': '50',
        'SLICE_MARGIN': '5'
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
    
    with open('temp_config.ini', 'w') as configfile:
        config.write(configfile)
    
    print("Created temp_config.ini with the following content:")
    with open('temp_config.ini', 'r') as configfile:
        print(configfile.read())

def run_script(script_name, args):
    script_path = os.path.join(scripts_dir, script_name)
    command = [sys.executable, script_path] + args
    subprocess.run(command, check=True, cwd=os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="""
    Master script for lesion processing pipeline

    This script orchestrates the entire lesion processing pipeline, including:
    1. Isolating lesions
    2. Matching lesions
    3. Processing images for viewer
    4. Generating static HTML pages for a fast, robust viewer
    5. Optionally starting the dynamic web application

    The pipeline expects a specific directory structure for the input data:

    base_path/
    ├── sub-001/
    │   ├── Reader_1_mask.nii.gz
    │   ├── Reader_2_mask.nii.gz
    │   └── Underlay.nii.gz
    ├── sub-002/
    │   ├── Reader_1_mask.nii.gz
    │   ├── Reader_2_mask.nii.gz
    │   └── Underlay.nii.gz
    └── ...

    After processing, the output directory will contain:

    output/
    ├── Reader_1/
    │   ├── sub-001_Lesion_01.nii.gz
    │   ├── sub-001_Lesion_02.nii.gz
    │   └── ...
    ├── Reader_2/
    │   ├── sub-001_Lesion_01.nii.gz
    │   ├── sub-001_Lesion_02.nii.gz
    │   └── ...
    ├── slices/
    │   ├── sub-001_001_001.jpg
    │   ├── sub-001_001_002.jpg
    │   └── ...
    ├── lesion_comparison_results.tsv
    ├── annotations.tsv
    └── static_html/      (generated static HTML files)
    
    The pipeline can be run in its entirety or step-by-step using the --steps argument.
    """, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--base_path", required=True, help="Base directory containing subject folders")
    parser.add_argument("--output", required=True, help="Output directory for processed data")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files in the output directory")
    parser.add_argument("--smooth", action="store_true", help="Apply smoothing to masks before isolating lesions")
    parser.add_argument("--steps", nargs='+', choices=['isolate', 'match', 'process', 'static', 'web'], 
                        default=['isolate', 'match', 'process', 'static'],
                        help="""
    Specify which steps of the pipeline to run. Options are:
    - isolate: Isolate individual lesions from the input masks
    - match: Match lesions between different readers
    - process: Process images for viewer
    - static: Generate static HTML pages for viewer
    - web: Start the dynamic web application (optional)
    If not specified, the default steps are: isolate, match, process, static.
    """)
    

    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    tsv_file = os.path.join(args.output, 'lesion_comparison_results.tsv')
    annotations_file = os.path.join(args.output, 'annotations.tsv')
    
    create_temp_config(args.base_path, args.output, tsv_file, annotations_file)
    
    if 'isolate' in args.steps:
        print("Step 1: Isolating lesions")
        isolate_args = [
            "--base_path", args.base_path
        ]
        if args.overwrite:
            isolate_args.append("--overwrite")
        if args.smooth:
            isolate_args.append("--smooth")
        run_script("Isolate_lesions.py", isolate_args)
    
    if 'match' in args.steps:
        print("Step 2: Matching lesions")
        match_args = [args.base_path, tsv_file]
        run_script("match_lesions.py", match_args)

    if 'process' in args.steps:
        print("Step 3: Processing images")
        if not os.path.exists('temp_config.ini'):
            print("Error: temp_config.ini not found. Cannot proceed with image processing.")
            return
        process_args = ["--config", os.path.abspath("temp_config.ini")]
        run_script("image_processing.py", process_args)

    if 'static' in args.steps:
        print("Step 4: Generating static HTML pages")
        run_script("generate_static_html.py", [])
    
    if 'web' in args.steps:
        print("Step 5: Starting web application")
        run_script("app.py", [])

    # Clean up temporary config file
    os.remove('temp_config.ini')

if __name__ == "__main__":
    main()
