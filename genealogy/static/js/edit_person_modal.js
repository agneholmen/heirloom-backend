function handleEditPersonRequest(evt) {
    if(evt.detail.xhr.status == 204) {
        var modal = bootstrap.Modal.getInstance(document.getElementById('edit-person-modal'));
        modal.hide();
        var modal_inner = document.getElementById('edit-person-modal-content');
        modal_inner.innerHTML = '';
    }
}