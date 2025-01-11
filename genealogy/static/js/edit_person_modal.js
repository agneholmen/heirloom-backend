function handleEditPersonRequest(evt) {
    if(evt.detail.xhr.status == 204) {
        var modal = bootstrap.Modal.getInstance(document.getElementById('modal'));
        modal.hide();
        var modal_inner = document.getElementById('modal-content');
        modal_inner.innerHTML = '';
    }
}