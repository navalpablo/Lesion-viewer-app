import os
import logging
from typing import Tuple, List, Optional, Dict
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from skimage import exposure
import configparser
import argparse
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Type aliases
NiftiImage = nib.Nifti1Image
NumpyArray = np.ndarray

def read_lesion_matches(tsv_path: str) -> Dict[str, Dict[str, str]]:
    try:
        df = pd.read_csv(tsv_path, sep='\t')
        logger.info(f"Columns found in the TSV file: {', '.join(df.columns)}")
        
        if 'Lesion ID' not in df.columns or 'Underlay' not in df.columns:
            logger.error("'Lesion ID' or 'Underlay' column not found in the TSV file.")
            raise ValueError("TSV file format is incorrect.")
        
        matches = {}
        for _, row in df.iterrows():
            lesion_id = str(row['Lesion ID'])
            matches[lesion_id] = {
                'Underlay': row['Underlay'],
                'Reader_1': row['Reader_1'] if 'Reader_1' in df.columns and pd.notna(row['Reader_1']) else None,
                'Reader_2': row['Reader_2'] if 'Reader_2' in df.columns and pd.notna(row['Reader_2']) else None
            }
        
        logger.info(f"Found {len(matches)} lesion matches.")
        if matches:
            sample_lesion = next(iter(matches))
            logger.info(f"Sample lesion data: {sample_lesion}: {matches[sample_lesion]}")
        
        return matches
    except Exception as e:
        logger.error(f"Error reading TSV file: {e}")
        raise

def load_nifti_image(filepath: str) -> Optional[NumpyArray]:
    try:
        img = nib.load(filepath)
        data = img.get_fdata()
        return data
    except Exception as e:
        logger.error(f"Error loading NIfTI image from {filepath}: {e}")
        return None

def get_center_and_margin(mask: NumpyArray, in_plane_margin: int = 50, slice_margin: int = 5) -> Tuple[List[List[int]], Tuple[int, int]]:
    coords = np.array(np.nonzero(mask))
    center = np.mean(coords, axis=1).astype(int)
    shape = mask.shape
    
    # Calculate in-plane bounds
    in_plane_bounds = [
        [max(0, center[i] - in_plane_margin), min(shape[i], center[i] + in_plane_margin)]
        for i in range(2)
    ]
    
    # Calculate through-plane (slice) bounds
    slice_min = max(0, coords[2].min() - slice_margin)
    slice_max = min(shape[2], coords[2].max() + slice_margin + 1)
    
    # Combine bounds
    bounds = in_plane_bounds + [[slice_min, slice_max]]
    
    return bounds, (slice_min, slice_max)



def crop_image(image: NumpyArray, bounds: List[List[int]]) -> NumpyArray:
    return image[bounds[0][0]:bounds[0][1], bounds[1][0]:bounds[1][1], bounds[2][0]:bounds[2][1]]

def save_slices_as_jpeg(t1_image: NumpyArray, mask_images: Dict[str, NumpyArray], 
                        out_dir: str, lesion_id: str, slice_range: Tuple[int, int]) -> int:
    slices_dir = os.path.join(out_dir, 'slices')
    os.makedirs(slices_dir, exist_ok=True)
    
    readers = ['Reader_1', 'Reader_2']
    num_readers = sum(1 for reader in readers if reader in mask_images)
    
    cmap = plt.get_cmap('Set1')  # Colormap for different readers
    colors = {
        'Reader_1': cmap(0)[:3],  # First color in the Set1 colormap
        'Reader_2': cmap(1)[:3]   # Second color in the Set1 colormap
    }
    
    slice_min, slice_max = slice_range
    for i in range(slice_min, slice_max):
        fig, axs = plt.subplots(1, 3, figsize=(15, 5))
        
        # Add main title with lesion ID
        fig.suptitle(f'Lesion ID: {lesion_id}', fontsize=16, y=1.05)
        
        # T1 image alone
        axs[0].imshow(np.rot90(exposure.equalize_hist(t1_image[:, :, i - slice_min])), cmap='gray')
        axs[0].axis('off')
        axs[0].set_title(f'T1 Image (Slice {i})')

        # Reader columns
        for idx, reader in enumerate(readers):
            if reader in mask_images:
                # T1 with reader's mask
                axs[idx+1].imshow(np.rot90(exposure.equalize_hist(t1_image[:, :, i - slice_min])), cmap='gray')
                mask = mask_images[reader]
                mask_rgba = np.zeros((*mask.shape[:2], 4))
                mask_rgba[..., :3] = colors[reader]  # RGB channels
                mask_rgba[..., 3] = np.where(mask[:, :, i - slice_min] > 0, 0.5, 0)  # Alpha channel
                axs[idx+1].imshow(np.rot90(mask_rgba))
                axs[idx+1].set_title(f'T1 + {reader} (Slice {i})')
            else:
                # Leave the subplot blank if reader data is absent
                axs[idx+1].axis('off')
                axs[idx+1].set_title(f'{reader} - No Data')

        # Adjust layout to make room for the main title
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])

        slice_path = os.path.join(slices_dir, f'{lesion_id}_{i:03d}.jpg')
        fig.savefig(slice_path, bbox_inches='tight', pad_inches=0.1, dpi=300)
        plt.close(fig)
    
    return slice_max - slice_min
    

def process_single_lesion(args: Tuple[str, Dict[str, str], str, int, int]) -> Optional[Tuple[str, int]]:
    lesion_id, match, out_dir, in_plane_margin, slice_margin = args
    
    try:
        t1_path = match['Underlay']
        
        if not os.path.exists(t1_path):
            logger.warning(f"T1 file not found: {t1_path}")
            return None

        t1_image = load_nifti_image(t1_path)
        if t1_image is None:
            return None

        mask_images = {}
        for reader in ['Reader_1', 'Reader_2']:
            if match[reader]:
                mask_path = match[reader]
                if os.path.exists(mask_path):
                    mask = load_nifti_image(mask_path)
                    if mask is not None:
                        mask_images[reader] = mask
                    else:
                        logger.warning(f"{reader} mask could not be loaded for lesion {lesion_id}: {mask_path}")
                else:
                    logger.warning(f"{reader} mask file not found for lesion {lesion_id}: {mask_path}")
            else:
                logger.info(f"No {reader} mask specified for lesion {lesion_id}")

        if not mask_images:
            logger.warning(f"No lesion mask found for lesion {lesion_id}")
            return None

        # Use the first available mask for bounding
        mask_for_bounds = next(iter(mask_images.values()))
        bounds, slice_range = get_center_and_margin(mask_for_bounds, in_plane_margin, slice_margin)

        cropped_t1 = crop_image(t1_image, bounds)
        cropped_masks = {reader: crop_image(mask, bounds) for reader, mask in mask_images.items()}
        num_slices = save_slices_as_jpeg(cropped_t1, cropped_masks, out_dir, lesion_id, slice_range)

        return lesion_id, num_slices
    except Exception as e:
        logger.error(f"Error processing lesion {lesion_id}: {e}")
        return None
        

def process_lesions(base_dir: str, out_dir: str, tsv_path: str) -> List[Tuple[str, int]]:
    os.makedirs(out_dir, exist_ok=True)
    
    lesion_matches = read_lesion_matches(tsv_path)
    
    in_plane_margin = int(config.get('IMAGE_PROCESSING', 'IN_PLANE_MARGIN'))
    slice_margin = int(config.get('IMAGE_PROCESSING', 'SLICE_MARGIN'))

    lesion_args = [(lesion_id, match, out_dir, in_plane_margin, slice_margin) for lesion_id, match in lesion_matches.items()]    
        
    num_processes = cpu_count()
    with Pool(num_processes) as pool:
        lesion_results = list(tqdm(pool.imap(process_single_lesion, lesion_args), total=len(lesion_args)))
    
    return [res for res in lesion_results if res is not None]
    
    
def main():
    parser = argparse.ArgumentParser(description="Process brain lesion images.")
    parser.add_argument("--config", help="Path to configuration file", default="config.ini")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    base_dir = config.get('PATHS', 'BASE_DIR')
    out_dir = config.get('PATHS', 'OUT_DIR')
    tsv_file = config.get('PATHS', 'TSV_FILE')

    if not base_dir or not out_dir or not tsv_file:
        parser.error("BASE_DIR, OUT_DIR, and TSV_FILE must be provided in the config file.")

    processed_lesions = process_lesions(base_dir, out_dir, tsv_file)
    
    logger.info(f"Processed {len(processed_lesions)} lesions.")
    logger.info(f"Images saved in {out_dir}/slices")

if __name__ == "__main__":
    main()