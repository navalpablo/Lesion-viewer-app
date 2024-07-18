from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import nibabel as nib
import numpy as np
from scipy.ndimage import label, binary_dilation, binary_erosion, generate_binary_structure
import argparse

def process_mask(mask_file_path, subject_dir, reader, overwrite=False, smooth=False):
    """
    Process a single mask file, isolating individual lesions.

    Args:
    mask_file_path (str): Path to the mask file.
    subject_dir (str): Path to the subject directory.
    reader (str): Name of the reader (e.g., 'Reader_1', 'Reader_2').
    overwrite (bool): If True, overwrite existing reader directories.
    smooth (bool): If True, apply smoothing to the mask before processing.
    """
    subject_id = os.path.basename(subject_dir)
    print(f"[{subject_id}][{reader}] Processing mask: {mask_file_path}")

    reader_dir = os.path.join(subject_dir, reader)
    if os.path.exists(reader_dir) and overwrite:
        print(f"[{subject_id}][{reader}] Overwriting {reader} directory: {reader_dir}")
        for file in os.listdir(reader_dir):
            os.remove(os.path.join(reader_dir, file))
        os.rmdir(reader_dir)

    if not os.path.exists(reader_dir):
        os.makedirs(reader_dir)
        print(f"[{subject_id}][{reader}] Created {reader} directory: {reader_dir}")

    mask_nii = nib.load(mask_file_path)
    mask_data = mask_nii.get_fdata()

    labels = np.unique(mask_data)[1:]
    print(f"[{subject_id}][{reader}] Found labels: {labels}")
    lesion_count = 1
    for label_id in labels:
        temp_mask = (mask_data == label_id).astype(int)
        
        if smooth:
            struct = generate_binary_structure(3, 1)  # 3D structuring element
            temp_mask = binary_dilation(temp_mask, structure=struct)
            temp_mask = binary_erosion(temp_mask, structure=struct)
        
        clusters, num_clusters = label(temp_mask)
        print(f"[{subject_id}][{reader}] Found {num_clusters} clusters for label {label_id}")

        for cluster_id in range(1, num_clusters + 1):
            cluster_mask = (clusters == cluster_id).astype(int)
            lesion_filename = f"{subject_id}_Lesion_{lesion_count:02d}.nii.gz"
            lesion_filepath = os.path.join(reader_dir, lesion_filename)
            save_nifti(cluster_mask, mask_nii.affine, lesion_filepath, subject_id, reader)
            print(f"[{subject_id}][{reader}] Saved lesion file: {lesion_filename}")
            lesion_count += 1

def save_nifti(data, affine, file_path, subject_id, reader):
    """
    Save a NumPy array as a NIfTI file.

    Args:
    data (numpy.ndarray): The image data to save.
    affine (numpy.ndarray): The affine transformation matrix.
    file_path (str): The path where the NIfTI file will be saved.
    subject_id (str): ID of the subject.
    reader (str): Name of the reader.
    """
    nii = nib.Nifti1Image(data, affine)
    nib.save(nii, file_path)
    print(f"[{subject_id}][{reader}] NIfTI file saved: {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''
    Process mask files for multiple readers in subject directories, isolating individual lesions.
    
    This script expects a specific directory structure and file naming convention:
    
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
    
    After processing, the script will create Reader_1 and Reader_2 directories within each subject folder,
    containing isolated lesion files:
    
    base_path/
    ├── sub-001/
    │   ├── Reader_1_mask.nii.gz
    │   ├── Reader_2_mask.nii.gz
    │   ├── Underlay.nii.gz
    │   ├── Reader_1/
    │   │   ├── sub-001_Lesion_01.nii.gz
    │   │   ├── sub-001_Lesion_02.nii.gz
    │   │   └── ...
    │   └── Reader_2/
    │       ├── sub-001_Lesion_01.nii.gz
    │       ├── sub-001_Lesion_02.nii.gz
    │       └── ...
    └── ...
    
    The script processes all masks in parallel for efficiency.
    ''', formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument('--base_path', type=str, required=True, 
                        help='Base directory containing subject folders (e.g., D:\\DATABASES\\paper5\\LECTURA_ALL\\test)')
    parser.add_argument('--overwrite', action='store_true', 
                        help='Overwrite existing Reader_1 and Reader_2 directories if they exist.')
    parser.add_argument('--smooth', action='store_true', 
                        help='Apply smoothing (dilation followed by erosion) to the masks before isolating lesions.')
    args = parser.parse_args()

    subject_dirs = [os.path.join(args.base_path, d) for d in os.listdir(args.base_path)
                    if os.path.isdir(os.path.join(args.base_path, d)) and d.startswith('sub-')]

    mask_tasks = []
    for subject_dir in subject_dirs:
        for reader in ['Reader_1', 'Reader_2']:
            mask_file_path = os.path.join(subject_dir, f"{reader}_mask.nii.gz")
            if os.path.exists(mask_file_path):
                mask_tasks.append((mask_file_path, subject_dir, reader, args.overwrite, args.smooth))

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(process_mask, *task): task for task in mask_tasks}
        for future in as_completed(futures):
            mask_file_path, subject_dir, reader, _, _ = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"Error processing mask: {mask_file_path}")
                print(e)