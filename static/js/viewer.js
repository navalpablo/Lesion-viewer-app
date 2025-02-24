console.log("viewer.js loaded");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded");

    const form = document.getElementById('annotationForm');
    const lesionContainers = document.querySelectorAll('.lesion-container');
    console.log("Found", lesionContainers.length, "lesion containers");

    // For each lesion container, set up the slice slider and "Other" annotation logic
    lesionContainers.forEach((container, index) => {
        const slider = container.querySelector('.slice-range');
        const image = container.querySelector('img');
        const currentSliceSpan = container.querySelector('.current-slice');

        if (!slider || !image || !currentSliceSpan) {
            console.error("Slider, image, or current-slice span not found for lesion", container.dataset.lesionId);
            return;
        }

        // Log the slider attributes for debugging
        console.log(`Lesion ${container.dataset.lesionId}: slider min=${slider.min}, max=${slider.max}, value=${slider.value}`);

        // When the slider moves, change the image slice
        slider.oninput = function() {
            console.log("Slider moved for lesion", container.dataset.lesionId, "to value", this.value);
            const sliceNumber = String(this.value).padStart(3, '0');

            // Example filename format: "sub-001_002_003.jpg"
            // Parse the current image filename to preserve subject & lesion IDs
            const filename = image.src.split('/').pop();  // e.g. "sub-001_002_003.jpg"
            console.log("Current filename:", filename);

            const parts = filename.split('_');
            if (parts.length < 3) {
                console.error("Unexpected filename format:", filename);
                return;
            }

            // Rebuild the filename with the new sliceNumber
            const subjectId = parts[0];    // e.g. "sub-001"
            const lesionNumber = parts[1]; // e.g. "002"
            const newFilename = subjectId + "_" + lesionNumber + "_" + sliceNumber + ".jpg";
            const newSrc = "../slices/" + newFilename;
            console.log("New image src:", newSrc);

            // Update image and the displayed slice number
            image.src = newSrc;
            currentSliceSpan.textContent = sliceNumber;
        };

        // Handle the "Other" annotation radio + textbox
        const otherRadio = container.querySelector('input[value="Other"]');
        const otherTextbox = container.querySelector('input[type="text"]');
        if (otherRadio && otherTextbox) {
            otherRadio.addEventListener('change', function() {
                if (this.checked) {
                    otherTextbox.focus();
                }
            });
            otherTextbox.addEventListener('input', function() {
                otherRadio.checked = true;
            });
        }
    });

    // Update form submission to POST annotations to the Flask backend
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Collect user annotations in an object: { lesionId: annotationValue }
        const annotations = {};
        lesionContainers.forEach(container => {
            const lesionId = container.dataset.lesionId;
            const selectedAnnotation = container.querySelector('input[name^="annotation_"]:checked');
            if (selectedAnnotation) {
                if (selectedAnnotation.value === 'Other') {
                    const otherText = container.querySelector('input[type="text"]').value;
                    annotations[lesionId] = otherText || 'Other';
                } else {
                    annotations[lesionId] = selectedAnnotation.value;
                }
            }
        });

        // Identify subject ID (assumes the first image's dataset contains subjectId)
        let subjectId = "unknown_subject";
        if (lesionContainers.length > 0) {
            const firstImg = lesionContainers[0].querySelector('img');
            if (firstImg && firstImg.dataset.subjectId) {
                subjectId = firstImg.dataset.subjectId;
            }
        }

        console.log("Annotations to submit:", annotations);
        console.log("Subject ID:", subjectId);

        // Send annotations to the Flask endpoint using fetch
        fetch('/save_annotations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                subject_id: subjectId,
                annotations: annotations
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert("Annotations saved successfully!");
            } else {
                alert("Error saving annotations: " + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Error saving annotations. Please try again.");
        });
    });
});
