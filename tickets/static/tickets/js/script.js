document.addEventListener('DOMContentLoaded', function () {
    // Función para actualizar el contador de caracteres
    const textarea = document.getElementById('descripcion'); 
    const contador = document.getElementById('contador-letras'); 
    const maxLength = parseInt(textarea.getAttribute('maxlength'), 10); 

    textarea.addEventListener('input', function () {
        const contadorAuxiliar = maxLength - textarea.value.length; 
        contador.textContent = contadorAuxiliar; 
    });

    // Función para filtrar casos dinámicamente según la categoría seleccionada (AJAX)
    const categoriaSelect = document.getElementById('categoria');
    const tipoCasoSelect = document.getElementById('tipoCaso');

    categoriaSelect.addEventListener('change', function () {
        const categoriaId = this.value;
        tipoCasoSelect.innerHTML = '<option value="">Cargando casos...</option>';

        if (categoriaId) {
            // Realiza la petición AJAX a la misma vista, pero con el parámetro categoria_id
            fetch(`/tickets/crear_ticket?categoria_id=${categoriaId}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(response => response.json())
                .then(data => {
                    tipoCasoSelect.innerHTML = '<option value="">Seleccione un caso</option>';
                    data.casos.forEach(caso => {
                        const option = document.createElement('option');
                        option.value = caso.id;
                        option.textContent = caso.descripcion;
                        tipoCasoSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error al cargar los casos:', error);
                    tipoCasoSelect.innerHTML = '<option value="">Error al cargar casos</option>';
                });
        } else {
            tipoCasoSelect.innerHTML = '<option value="">Seleccione una categoría primero</option>';
        }
    });
});
