function handleNewPersonRequest(evt) {
    if(evt.detail.xhr.status == 204) {
        location.reload();
    } else if(evt.detail.xhr.status == 400) {
        const jsonResponse = evt.detail.xhr.response;
        const responseData = JSON.parse(jsonResponse);
        const errors = responseData.errors;

        errorMessageContainer = document.getElementById('error-messages');
        for (const key in errors) {
            if(errors.hasOwnProperty(key)) {
                if(Array.isArray(errors[key])) {
                    errors[key].forEach(message => {
                        const alertDiv = createErrorMessage(message);
                        errorMessageContainer.appendChild(alertDiv);
                    });
                } else {
                    var message = errors[key];
                    const alertDiv = createErrorMessage(message);
                    errorMessageContainer.appendChild(alertDiv);
                }
            }
        }
    }
}

function createErrorMessage(message) {
    // Generate random string just in case there are multiple messages, which will probably never happen.
    const idString = "error-message-alert".concat(Math.random().toString(36).substring(2, 5));
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