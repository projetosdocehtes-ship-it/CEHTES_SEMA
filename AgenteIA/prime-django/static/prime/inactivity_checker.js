document.addEventListener("DOMContentLoaded", function () {
    function checkInactivity() {
        fetch('/verificar-inatividade/')
            .then(response => response.json())
            .then(data => {
                if (data.logout_in <= 5) {
                    alert('Você será desconectado por inatividade.');
                }
            });
    }

    setInterval(checkInactivity, 60000); // Verifica a cada minuto
});
