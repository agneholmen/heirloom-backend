var imageContainers = document.getElementsByClassName('image-container');

for (let container of document.getElementsByClassName('image-container')) {
    container.addEventListener("click", () => {
        for (let imageContainer of document.getElementsByClassName('image-container')) {
            if (imageContainer.classList.contains('image-container-selected')) {
                imageContainer.classList.remove('image-container-selected');
            }
        }
        if (!container.classList.contains('image-container-selected')) {
            container.classList.toggle('image-container-selected');
            document.getElementById('selectedPhotoId').value = container.id.replace('image-', '');
        }
    });
}

function createErrorMessage(message) {
    const idString = "error-message-alert";
    const messageHTML = `
    <div class="alert alert-danger alert-dismissible fade show" role="alert" id="${idString}">
        <div>${message}</div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>`
    const template = document.createElement('template');
    template.innerHTML = messageHTML.trim();

    setTimeout(() => {
        const alert = document.getElementById(idString);
        if(alert) {
            alert.classList.remove('show');
            alert.classList.add('fade');
            setTimeout(() => {
                alert.remove();
            }, 150);
        }
    }, 3000);

    return template.content.firstChild;
}

function validateInput(event) {
    let selectedPhotoId = document.getElementById("selectedPhotoId").value;

    if (!selectedPhotoId) {
        errorMessageContainer = document.getElementById('error-messages');
        var alertDiv = createErrorMessage("You must select a photo first!");
        errorMessageContainer.appendChild(alertDiv);
        event.preventDefault();
    }
}
