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

    // Función para eliminar archivos
    const eliminarBotones = document.querySelectorAll('.btn-eliminar');
    eliminarBotones.forEach(button => {
        button.addEventListener('click', function () {
            const archivoId = this.getAttribute('data-id');

            if (confirm('¿Estás seguro de que deseas eliminar este archivo?')) {
                fetch(`/tickets/eliminar_archivo/${archivoId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCSRFToken(), // Token CSRF
                        'Content-Type': 'application/json',
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload(); // Recarga la página para reflejar los cambios
                    } else {
                        alert('Error al eliminar el archivo.');
                    }
                })
                .catch(error => {
                    console.error('Error al eliminar el archivo:', error);
                });
            }
        });
    });

    // Función para obtener el token CSRF
    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return cookie.substring('csrftoken='.length, cookie.length);
            }
        }
        return '';
    }
});
 //Funcion para que el campo de fecha y hora resolucion sea igual en todos los navegadores
 document.addEventListener("DOMContentLoaded", function () {
  console.log("✅ script.js cargó");

  console.log("flatpickr =", typeof flatpickr);
  const a = document.querySelector("#tiempo_fecha_asignacion");
  const b = document.querySelector("#fecha_hora_resolucion");
  console.log("input asignacion:", a);
  console.log("input resolucion:", b);

  if (typeof flatpickr === "undefined") {
    console.error("❌ Flatpickr no está cargado (CDN).");
    return;
  }

  const config = {
    enableTime: true,
    dateFormat: "d/m/Y H:i",
    time_24hr: true,
    allowInput: true,
    clickOpens: true,
    locale: "es"
  };

  if (a) flatpickr(a, config);
  if (b) flatpickr(b, config);
});
