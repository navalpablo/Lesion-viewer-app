import os
import numpy as np
import nibabel as nib
import pandas as pd
from multiprocessing import Pool, cpu_count
import tqdm
from functools import partial
from typing import List, Dict, Tuple, Set

def load_lesion_mask(filepath: str) -> np.ndarray:
    img = nib.load(filepath)
    return img.get_fdata()

def compare_lesions(lesion1: np.ndarray, lesion2: np.ndarray) -> bool:
    return np.any(np.logical_and(lesion1 > 0, lesion2 > 0))

def get_lesions_from_directory(base_dir: str) -> pd.DataFrame:
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

def process_subject(subject_data: pd.DataFrame) -> Tuple[List[List[str]], str, str]:
    reader_types = subject_data['Lesion Type'].unique()
    if len(reader_types) > 2:
        raise ValueError(f"Expected 1 or 2 reader types, found {len(reader_types)}: {reader_types}")
    
    reader1, reader2 = (reader_types[0], reader_types[1]) if len(reader_types) == 2 else (reader_types[0], "No_Reader")
    
    reader1_lesions = subject_data[subject_data['Lesion Type'] == reader1]
    reader2_lesions = subject_data[subject_data['Lesion Type'] == reader2] if reader2 != "No_Reader" else pd.DataFrame()

    results = []
    reader1_paths = reader1_lesions['Lesion Full Path'].tolist()
    reader2_paths = reader2_lesions['Lesion Full Path'].tolist() if not reader2_lesions.empty else []

    underlay_path = subject_data['Underlay'].iloc[0]

    lesion_counter = 1
    multiple_matches: Dict[str, Set[str]] = {}

    def add_result(r1_path: str, r2_path: str) -> None:
        nonlocal lesion_counter
        lesion_id = f'{subject_data.iloc[0]["Subject Folder"]}_{str(lesion_counter).zfill(3)}'
        results.append([lesion_id, underlay_path, r1_path, r2_path, ''])
        
        if r1_path and r2_path:
            multiple_matches.setdefault(r1_path, set()).add(r2_path)
            multiple_matches.setdefault(r2_path, set()).add(r1_path)
        
        lesion_counter += 1

    # Load all masks at once to avoid repeated disk I/O
    reader1_masks = {path: load_lesion_mask(path) for path in reader1_paths}
    reader2_masks = {path: load_lesion_mask(path) for path in reader2_paths}

    # Match Reader 1 to Reader 2
    for reader1_path, reader1_mask in reader1_masks.items():
        matches = [reader2_path for reader2_path, reader2_mask in reader2_masks.items() 
                   if compare_lesions(reader1_mask, reader2_mask)]
        
        if matches:
            for match in matches:
                add_result(reader1_path, match)
        else:
            add_result(reader1_path, '')

    # Check for unmatched Reader 2 lesions
    matched_reader2 = set(match for result in results if result[3] for match in [result[3]])
    unmatched_reader2 = set(reader2_paths) - matched_reader2
    for unmatched in unmatched_reader2:
        add_result('', unmatched)

    # Add information about multiple matches
    for i, (_, _, r1_path, r2_path, _) in enumerate(results):
        multiple_match_info = []
        
        for path, reader in [(r1_path, "Reader 1"), (r2_path, "Reader 2")]:
            if path in multiple_matches and len(multiple_matches[path]) > 1:
                matching_lesions = [os.path.basename(m) for m in multiple_matches[path]]
                multiple_match_info.append(f"{reader} matches multiple: {', '.join(matching_lesions)}")
        
        if multiple_match_info:
            results[i][4] = '; '.join(multiple_match_info)

    return results, reader1, reader2

def match_lesions(base_dir: str, output_path: str) -> None:
    data = get_lesions_from_directory(base_dir)
    subjects = data['Subject Folder'].unique()
    
    num_cores = cpu_count()
    print(f"Using {num_cores} CPU cores for parallel processing")

    with Pool(num_cores) as pool:
        process_func = partial(process_subject)
        results = list(tqdm.tqdm(
            pool.imap(process_func, [data[data['Subject Folder'] == subject] for subject in subjects]),
            total=len(subjects),
            desc="Matching lesions"
        ))

    all_results = []
    reader_types = set()

    for subject_results, reader1, reader2 in results:
        all_results.extend(subject_results)
        reader_types.update([reader1, reader2])

    if len(reader_types) != 2:
        raise ValueError(f"Expected 2 reader types across all subjects, found {len(reader_types)}: {reader_types}")

    reader1, reader2 = sorted(reader_types)
    
    output_df = pd.DataFrame(all_results, columns=['Lesion ID', 'Underlay', 'Reader_1', 'Reader_2', 'Multiple Matches'])
    
    # Check for duplicates
    output_df['Is Duplicate'] = output_df.duplicated(subset=['Lesion ID', 'Reader_1', 'Reader_2'], keep='first')
    
    output_df.to_csv(output_path, sep='\t', index=False)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Match lesions from two readers based on directory structure.")
    parser.add_argument("base_dir", help="Path to the base directory containing subject folders")
    parser.add_argument("output_tsv", help="Path to the output TSV file")
    args = parser.parse_args()

    match_lesions(args.base_dir, args.output_tsv)