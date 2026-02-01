// Disable all event listeners that block copy/paste
(function () {
    // Allow text selection
    document.body.style.userSelect = 'auto';
    document.body.style.webkitUserSelect = 'auto';

    // Remove event listeners for copy, cut, paste, contextmenu, selectstart
    ['copy', 'cut', 'paste', 'contextmenu', 'selectstart'].forEach(event => {
        document.addEventListener(event, function (e) {
            e.stopImmediatePropagation();
        }, true);
    });

    // Apply to all elements
    document.querySelectorAll('*').forEach(el => {
        el.style.userSelect = 'auto';
        el.style.webkitUserSelect = 'auto';
        el.oncopy = null;
        el.oncut = null;
        el.onpaste = null;
        el.onselectstart = null;
        el.oncontextmenu = null;
    });

    // Remove attributes that block copy
    document.querySelectorAll('[oncopy], [onselectstart], [oncontextmenu]').forEach(el => {
        el.removeAttribute('oncopy');
        el.removeAttribute('onselectstart');
        el.removeAttribute('oncontextmenu');
    });

    console.log('✅ Đã bỏ chặn copy! Bây giờ bạn có thể copy nội dung.');
})();