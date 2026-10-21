/* Etiqueta nativa de Dash DataTable; conserva el botón y su manejador original. */
(function () {
    function translate(scope) {
        scope.querySelectorAll('.m6ct-shell button.show-hide').forEach(function (button) {
            if (button.textContent.trim() === 'Toggle Columns') {
                button.textContent = 'Mostrar/ocultar columnas';
                button.setAttribute('aria-label', 'Mostrar/ocultar columnas');
            }
        });
    }
    function start() {
        translate(document);
        new MutationObserver(function (records) {
            const relevant = records.some(function (record) {
                const target = record.target.nodeType === 1 ? record.target : record.target.parentElement;
                return (target && target.closest('.m6ct-shell')) || Array.from(record.addedNodes).some(function (node) {
                    return node.nodeType === 1 && (node.matches('.m6ct-shell') || node.querySelector('.m6ct-shell'));
                });
            });
            if (relevant) translate(document);
        }).observe(document.body, {childList: true, subtree: true, characterData: true});
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
}());
