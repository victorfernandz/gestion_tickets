document.addEventListener('DOMContentLoaded', function () {
    const textarea = document.getElementById('descripcion'); // Seleccionar el textarea
    const contador = document.getElementById('contador-letras'); // Seleccionar el contador de caracteres
    const maxLength = parseInt(textarea.getAttribute('maxlength'), 10); // Obtener el límite máximo

    // Actualizar el contador cuando el usuario escribe
    textarea.addEventListener('input', function () {
        const remainingChars = maxLength - textarea.value.length; // Calcular caracteres restantes
        contador.textContent = remainingChars; // Actualizar el texto del contador
    });
});
