document.addEventListener('DOMContentLoaded', function () {
    // Función para actualizar el contador de caracteres
    const textarea = document.getElementById('descripcion'); // Seleccionar el textarea
    const contador = document.getElementById('contador-letras'); // Seleccionar el contador de caracteres
    const maxLength = parseInt(textarea.getAttribute('maxlength'), 10); // Obtener el límite máximo

    textarea.addEventListener('input', function () {
        const contadorAuxiliar = maxLength - textarea.value.length; // Calcular caracteres restantes
        contador.textContent = contadorAuxiliar; // Actualizar el texto del contador
    });
});
