function handleDeleteTreeRequest(evt) {
    if(evt.detail.xhr.status == 204) {
        var modal = bootstrap.Modal.getInstance(document.getElementById('delete-tree-modal'));
        modal.hide();
        var modal_inner = document.getElementById('delete-tree-modal-content');
        modal_inner.innerHTML = '';
    }
}