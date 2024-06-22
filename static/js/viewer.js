document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('annotationForm');
    const lesionContainers = document.querySelectorAll('.lesion-container');

    lesionContainers.forEach(container => {
        const slider = container.querySelector('.slice-range');
        const image = container.querySelector('img');
        const lesionId = image.dataset.lesionId;

        slider.oninput = function() {
            const sliceNumber = String(this.value).padStart(3, '0');
            const newSrc = `/slices/${lesionId}_${sliceNumber}.jpg`;
            image.src = newSrc;
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const subjectId = document.querySelector('img').dataset.subjectId;
        const annotations = {};

        lesionContainers.forEach(container => {
            const lesionId = container.querySelector('img').dataset.lesionId;
            const selectedAnnotation = container.querySelector('input[name^="annotation_"]:checked');
            if (selectedAnnotation) {
                annotations[lesionId] = selectedAnnotation.value;
            }
        });

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