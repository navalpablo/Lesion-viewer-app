console.log("viewer.js loaded");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded");
    const form = document.getElementById('annotationForm');
    const lesionContainers = document.querySelectorAll('.lesion-container');
    console.log("Found", lesionContainers.length, "lesion containers");

    lesionContainers.forEach((container, index) => {
        const slider = container.querySelector('.slice-range');
        const image = container.querySelector('img');
        const currentSliceSpan = container.querySelector('.current-slice');
        console.log("Processing container", index, ":", container.dataset.lesionId);

        if (!slider || !image || !currentSliceSpan) {
            console.error("Slider, image or current-slice span not found for lesion", container.dataset.lesionId);
            return;
        }

        slider.oninput = function() {
            console.log("Slider moved for lesion", container.dataset.lesionId, "to value", this.value);
            const sliceNumber = String(this.value).padStart(3, '0');
            const [subjectId, lesionNumber, _] = image.src.split('/').pop().split('_');
            const newSrc = `/slices/${subjectId}_${lesionNumber}_${sliceNumber}.jpg`;
            console.log("New image src:", newSrc);
            image.src = newSrc;
            currentSliceSpan.textContent = sliceNumber;
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const subjectId = document.querySelector('img').dataset.subjectId;
        const annotations = {};

        lesionContainers.forEach(container => {
            const lesionId = container.dataset.lesionId;
            const selectedAnnotation = container.querySelector('input[name^="annotation_"]:checked');
            if (selectedAnnotation) {
                annotations[lesionId] = selectedAnnotation.value;
            }
        });

        console.log("Submitting annotations:", annotations);

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
                alert("Annotations saved successfully");
                window.location.href = '/';  // Redirect to the index page
            } else {
                alert("Error saving annotations. Please try again.");
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert("Error saving annotations. Please try again.");
        });
    });
});