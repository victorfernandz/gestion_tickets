document.addEventListener('DOMContentLoaded', function () {

    // ── Contador de caracteres ────────────────────────────────────────────────
    const textarea = document.getElementById('descripcion');
    const contador = document.getElementById('contador-letras');
    if (textarea && contador) {
        const maxLength = parseInt(textarea.getAttribute('maxlength'), 10);
        textarea.addEventListener('input', function () {
            contador.textContent = maxLength - textarea.value.length;
        });
    }

    // ── Filtro dinámico de casos por categoría (AJAX) ─────────────────────────
    const categoriaSelect = document.getElementById('categoria');
    const tipoCasoSelect  = document.getElementById('tipoCaso');
    if (categoriaSelect && tipoCasoSelect) {
        categoriaSelect.addEventListener('change', function () {
            const categoriaId = this.value;
            tipoCasoSelect.innerHTML = '<option value="">Cargando casos...</option>';

            if (categoriaId) {
                fetch(`/tickets/crear_ticket?categoria_id=${categoriaId}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                .then(r => r.json())
                .then(data => {
                    tipoCasoSelect.innerHTML = '<option value="">Seleccione un caso</option>';
                    data.casos.forEach(caso => {
                        const opt = document.createElement('option');
                        opt.value = caso.id;
                        opt.textContent = caso.descripcion;
                        tipoCasoSelect.appendChild(opt);
                    });
                })
                .catch(() => {
                    tipoCasoSelect.innerHTML = '<option value="">Error al cargar casos</option>';
                });
            } else {
                tipoCasoSelect.innerHTML = '<option value="">Seleccione una categoría primero</option>';
            }
        });
    }

    // ── Eliminar archivos adjuntos ────────────────────────────────────────────
    document.querySelectorAll('.btn-eliminar').forEach(button => {
        button.addEventListener('click', function () {
            const archivoId = this.getAttribute('data-id');
            if (confirm('¿Estás seguro de que deseas eliminar este archivo?')) {
                fetch(`/tickets/eliminar_archivo/${archivoId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                        'Content-Type': 'application/json',
                    },
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error al eliminar el archivo.');
                    }
                })
                .catch(() => alert('Error al eliminar el archivo.'));
            }
        });
    });

    // ── Flatpickr — campos de fecha/hora (cross-browser) ──────────────────────
    if (typeof flatpickr !== 'undefined') {
        const config = {
            enableTime: true,
            dateFormat: 'd/m/Y H:i',
            time_24hr: true,
            allowInput: true,
            clickOpens: true,
            locale: 'es',
        };

        const inputAsignacion = document.getElementById('tiempo_fecha_asignacion');
        const inputResolucion = document.getElementById('fecha_hora_resolucion');

        if (inputAsignacion) flatpickr(inputAsignacion, config);
        if (inputResolucion) flatpickr(inputResolucion, config);
    }

    // ── Helper CSRF ───────────────────────────────────────────────────────────
    function getCSRFToken() {
        const match = document.cookie.split(';')
            .map(c => c.trim())
            .find(c => c.startsWith('csrftoken='));
        return match ? match.split('=')[1] : '';
    }

});
