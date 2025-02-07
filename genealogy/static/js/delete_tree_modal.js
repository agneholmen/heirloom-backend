function handleDeleteTreeRequest(evt) {
    if(evt.detail.xhr.status == 204) {
        location.reload();
    }
}