import os
import numpy as np
import nibabel as nib
import pandas as pd
from multiprocessing import Pool, cpu_count
import tqdm
from functools import partial
from typing import List, Dict, Tuple, Set
import gc
import psutil

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 ** 2  # Memory usage in MB

def get_available_memory():
    return psutil.virtual_memory().available / 1024 ** 2  # Available memory in MB

def load_lesion_mask(filepath: str) -> np.ndarray:
    try:
        img = nib.load(filepath)
        data = img.get_fdata()
        return data.astype(np.float32)  # Convert to float32 to save memory
    except MemoryError:
        print(f"Memory Error: Unable to load {filepath}. Skipping this file.")
        return None
    except Exception as e:
        print(f"Error loading file {filepath}: {str(e)}")
        return None

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

def process_subject(subject_data: pd.DataFrame) -> Tuple[List[List[str]], str, str, int]:
    reader_types = subject_data['Lesion Type'].unique()
    
    if len(reader_types) == 1:
        reader = reader_types[0]
        lesions = subject_data[subject_data['Lesion Type'] == reader]
        results = []
        underlay_path = subject_data['Underlay'].iloc[0]
        
        for _, lesion in lesions.iterrows():
            lesion_id = f"{lesion['Subject Folder']}_{len(results) + 1:03d}"
            if reader == 'Reader_1':
                results.append([lesion_id, underlay_path, lesion['Lesion Full Path'], '', ''])
            else:
                results.append([lesion_id, underlay_path, '', lesion['Lesion Full Path'], ''])
        
        return results, reader, 'No_Reader', len(results)
    
    elif len(reader_types) == 2:
        reader1, reader2 = sorted(reader_types)
    else:
        raise ValueError(f"Expected 1 or 2 reader types, found {len(reader_types)}: {reader_types}")
    
    reader1_lesions = subject_data[subject_data['Lesion Type'] == reader1]
    reader2_lesions = subject_data[subject_data['Lesion Type'] == reader2]

    results = []
    reader1_paths = reader1_lesions['Lesion Full Path'].tolist()
    reader2_paths = reader2_lesions['Lesion Full Path'].tolist()

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

    for reader1_path in reader1_paths:
        reader1_mask = load_lesion_mask(reader1_path)
        if reader1_mask is None:
            continue
        
        matches = []
        for reader2_path in reader2_paths:
            reader2_mask = load_lesion_mask(reader2_path)
            if reader2_mask is None:
                continue
            if compare_lesions(reader1_mask, reader2_mask):
                matches.append(reader2_path)
            del reader2_mask
        
        if matches:
            for match in matches:
                add_result(reader1_path, match)
        else:
            add_result(reader1_path, '')
        
        del reader1_mask
    
    gc.collect()  # Force garbage collection

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

    return results, reader1, reader2, len(results)

def match_lesions(base_dir: str, output_path: str) -> None:
    data = get_lesions_from_directory(base_dir)
    subjects = data['Subject Folder'].unique()
    
    num_processes = cpu_count()
    print(f"Using {num_processes} processes (matching number of CPU threads)")

    all_results = []
    reader_types = set()
    total_lesions = 0
    processed_lesions = 0

    with Pool(num_processes) as pool:
        process_func = partial(process_subject)
        results = list(tqdm.tqdm(
            pool.imap(process_func, [data[data['Subject Folder'] == subject] for subject in subjects]),
            total=len(subjects),
            desc="Matching lesions"
        ))

    for subject_results, reader1, reader2, num_lesions in results:
        all_results.extend(subject_results)
        reader_types.update([reader1, reader2])
        total_lesions += num_lesions
        processed_lesions += num_lesions
        print(f"Processed {processed_lesions}/{total_lesions} lesions ({processed_lesions/total_lesions*100:.2f}%)")

    readers = sorted(reader for reader in reader_types if reader != 'No_Reader')
    
    if len(readers) == 1:
        print(f"Only one reader type found: {readers[0]}. All lesions will be unmatched.")
    elif len(readers) == 2:
        print(f"Two reader types found: {readers[0]} and {readers[1]}. Lesions have been matched where possible.")
    else:
        raise ValueError(f"Unexpected number of reader types: {readers}")

    output_df = pd.DataFrame(all_results, columns=['Lesion ID', 'Underlay', 'Reader_1', 'Reader_2', 'Multiple Matches'])
    
    # Check for duplicates
    output_df['Is Duplicate'] = output_df.duplicated(subset=['Lesion ID', 'Reader_1', 'Reader_2'], keep='first')
    
    output_df.to_csv(output_path, sep='\t', index=False)
    print(f"Results saved to {output_path}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Match lesions from one or two readers based on directory structure.")
    parser.add_argument("base_dir", help="Path to the base directory containing subject folders")
    parser.add_argument("output_tsv", help="Path to the output TSV file")
    args = parser.parse_args()

    match_lesions(args.base_dir, args.output_tsv)