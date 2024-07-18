import os
import numpy as np
import nibabel as nib
import pandas as pd
from multiprocessing import Pool, cpu_count
import tqdm

def load_lesion_mask(filepath):
    img = nib.load(filepath)
    return img.get_fdata()

def compare_lesions(lesion1, lesion2):
    combined = lesion1 + lesion2
    return np.max(combined) > 1

def get_lesions_from_directory(base_dir):
    data = []
    for subject_dir in os.listdir(base_dir):
        subject_path = os.path.join(base_dir, subject_dir)
        if not os.path.isdir(subject_path):
            continue

        underlay_path = os.path.join(subject_path, "underlay.nii.gz")
        if not os.path.exists(underlay_path):
            print(f"Warning: No underlay found for subject {subject_dir}")
            continue

        for reader in ["Reader_1", "Reader_2"]:
            reader_path = os.path.join(subject_path, reader)
            if not os.path.isdir(reader_path):
                continue

            for lesion_file in os.listdir(reader_path):
                if lesion_file.endswith(".nii.gz"):
                    data.append({
                        "Subject Folder": subject_dir,
                        "Lesion Type": reader,
                        "Lesion Basename": lesion_file,
                        "Lesion Full Path": os.path.join(reader_path, lesion_file),
                        "Underlay": underlay_path
                    })

    return pd.DataFrame(data)

def process_subject(subject_data):
    reader_types = subject_data['Lesion Type'].unique()
    if len(reader_types) > 2:
        raise ValueError(f"Expected 1 or 2 reader types, found {len(reader_types)}: {reader_types}")
    
    if len(reader_types) == 1:
        reader1 = reader_types[0]
        reader2 = "No_Reader"
    else:
        reader1, reader2 = reader_types
    
    reader1_lesions = subject_data[subject_data['Lesion Type'] == reader1]
    reader2_lesions = subject_data[subject_data['Lesion Type'] == reader2] if reader2 != "No_Reader" else pd.DataFrame()

    results = []
    reader1_paths = reader1_lesions['Lesion Full Path'].tolist()
    reader2_paths = reader2_lesions['Lesion Full Path'].tolist() if not reader2_lesions.empty else []

    used_reader2_indices = set()
    lesion_counter = 1

    underlay_path = subject_data['Underlay'].iloc[0]

    for reader1_path in reader1_paths:
        reader1_mask = load_lesion_mask(reader1_path)
        matches = []

        for idx, reader2_path in enumerate(reader2_paths):
            if idx in used_reader2_indices:
                continue

            reader2_mask = load_lesion_mask(reader2_path)
            if compare_lesions(reader1_mask, reader2_mask):
                matches.append(reader2_path)
                used_reader2_indices.add(idx)

        lesion_id = f'{subject_data.iloc[0]["Subject Folder"]}_{str(lesion_counter).zfill(3)}'
        if matches:
            for match in matches:
                results.append([lesion_id, underlay_path, reader1_path, match])
        else:
            results.append([lesion_id, underlay_path, reader1_path, ''])
        
        lesion_counter += 1

    if reader2 != "No_Reader":
        for idx, reader2_path in enumerate(reader2_paths):
            if idx not in used_reader2_indices:
                lesion_id = f'{subject_data.iloc[0]["Subject Folder"]}_{str(lesion_counter).zfill(3)}'
                results.append([lesion_id, underlay_path, '', reader2_path])
                lesion_counter += 1

    return results, reader1, reader2

def match_lesions(base_dir, output_path):
    data = get_lesions_from_directory(base_dir)
    subjects = data['Subject Folder'].unique()
    
    # Determine the number of CPU cores to use
    num_cores = cpu_count()
    print(f"Using {num_cores} CPU cores for parallel processing")

    # Create a pool of worker processes
    with Pool(num_cores) as pool:
        # Use tqdm to show a progress bar
        results = list(tqdm.tqdm(pool.imap(process_subject, [data[data['Subject Folder'] == subject] for subject in subjects]), total=len(subjects), desc="Matching lesions"))

    all_results = []
    reader_types = set()

    for subject_results, reader1, reader2 in results:
        all_results.extend(subject_results)
        reader_types.update([reader1, reader2])

    if len(reader_types) != 2:
        raise ValueError(f"Expected 2 reader types across all subjects, found {len(reader_types)}: {reader_types}")

    reader1, reader2 = sorted(reader_types)
    
    # Create DataFrame with the expected column order
    output_df = pd.DataFrame(all_results, columns=['Lesion ID', 'Underlay', 'Reader_1', 'Reader_2'])
    
    output_df.to_csv(output_path, sep='\t', index=False)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Match lesions from two readers based on directory structure.")
    parser.add_argument("base_dir", help="Path to the base directory containing subject folders")
    parser.add_argument("output_tsv", help="Path to the output TSV file")
    args = parser.parse_args()

    match_lesions(args.base_dir, args.output_tsv)