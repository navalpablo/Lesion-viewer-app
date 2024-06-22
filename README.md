# Lesion Viewer
Lesion Viewer is a tool designed to assist in reviewing segmentations by different readers. It's particularly useful for cases involving numerous small segmentations, such as multiple sclerosis MRI lesions, where there might be many little white-matter lesions.

## Features

- View and compare segmentations from multiple readers
- Navigate through slices of 3D medical images
- Annotate lesions as Reader_1, Reader_2, No_rim, or Review
- Save annotations for further analysis

## Installation

1. Clone this repository:
```git clone https://github.com/yourusername/lesion-viewer.git`
cd lesion-viewer```

2. Create a conda environment using the provided requirements.yaml:
```conda env create -f requirements.yaml```

3. Activate the environment:
```conda activate lesion-viewer```


## Configuration

1. Copy the config.ini.example to config.ini:
```cp config.ini.example config.ini```

2. Edit config.ini to set your specific paths and preferences.

## Usage

### Image processing

Before using the viewer, you need to process the MRI images and segmentations:

1. Prepare a TSV file with columns for Lesion ID, Underlay (T1 image path), Reader_1 (segmentation path), and Reader_2 (segmentation path).

2. Run the image processing script:

```python image_processing.py --config config.ini```

This script will:
- Read the TSV file specified in your config.ini
- Process each lesion, creating JPEG slices for viewing
- Save the processed images in the output directory specified in your config.ini

### Viewing and annotating

1. Run the Flask application:
```python app.py```

2. Open a web browser and navigate to http://localhost:5000

3. Select a subject from the list to start reviewing lesions

4. Use the slider to navigate through slices and the radio buttons to annotate each lesion

5. Click "Save All Annotations" to save your work

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.


## Contact
If you have any questions or feedback, please open an issue on this repository.