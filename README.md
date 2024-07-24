# Lesion Viewer

<img src="static/images/icon.png" alt="Lesion Viewer Logo" width="50%" height="50%">

Lesion Viewer is a tool designed to assist in reviewing segmentations by one or different readers. It's particularly useful for cases involving numerous small segmentations, such as multiple sclerosis MRI lesions, where there might be many little white-matter lesions.

## Features

- GUI for easy preprocessing and viewing setup
- Isolate individual lesions from input masks
- Match lesions between different readers
- Process and prepare images for 3D interactive slice by slice web viewing centered on lesion
- Interactive web-based viewer for lesion annotation
- Compare segmentations from multiple readers
- Navigate through slices of 3D medical images
- Annotate lesions in the go using the web viewer 
- Save annotations for further analysis

## Installation

1. Clone this repository:
```git clone https://github.com/yourusername/lesion-viewer.git`
cd lesion-viewer```

2. Create a conda environment using the provided requirements.yaml:
```conda env create -f requirements.yaml```

3. Activate the environment:
```conda activate lesion-viewer```


## Usage
### GUI Interface

1. Run the GUI application:
```python lesion_viewer_gui.py```

2. Use the GUI to:
-  Select input and output directories
-  Choose preprocessing steps
-  Execute preprocessing
-  Launch the web viewer



### Command Line Interface
Alternatively, you can use the command-line interface:

Run the main script:
```python Lesion_viewer.py --base_path /path/to/input --output /path/to/output --steps isolate match process web```

#### Available steps:
- isolate: Isolate individual lesions from input masks
- match: Match lesions between different readers
- process: Process images for web viewing
- web: Start the web application for lesion viewing and annotation

### Web Viewer

1. After preprocessing, the web viewer will automatically launch in your default browser.
2. Select a subject from the list to start reviewing lesions.
3. Use the slider to navigate through slices and the radio buttons to annotate each lesion.
4. Click "Save All Annotations" to save your work.

### Input Data Structure
The pipeline expects a specific directory structure for the input data:

```base_path/
├── sub-001/
│   ├── Reader_1_mask.nii.gz
│   ├── Reader_2_mask.nii.gz
│   └── Underlay.nii.gz
├── sub-002/
│   ├── Reader_1_mask.nii.gz
│   ├── Reader_2_mask.nii.gz
│   └── Underlay.nii.gz
└── ...
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details. However, it uses multiple other tools and inherits their licensing.

## Contact
If you have any questions or feedback, please open an issue on this repository.