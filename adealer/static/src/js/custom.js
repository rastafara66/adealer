// Додайте цей скрипт у шаблон або у відповідний JS-файл
document.querySelectorAll('a.fw-bold.text-truncate[data-tooltip]').forEach(function(el) {
    el.innerHTML = el.textContent.replace(/\s*\/\s*/g, '<br>/');
});