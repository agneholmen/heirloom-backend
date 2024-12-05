document.querySelectorAll('[role="alert"]').forEach(function (el) {
    setTimeout(() => {
        el.classList.remove('show');
        el.classList.add('fade');
        setTimeout(() => {
            el.remove();
        }, 150);
    }, 5000);
});