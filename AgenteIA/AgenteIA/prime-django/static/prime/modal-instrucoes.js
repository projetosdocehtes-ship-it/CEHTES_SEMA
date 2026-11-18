// // modal-instrucoes.js
// document.addEventListener('DOMContentLoaded', function () {
//     const infoIcons = document.querySelectorAll('.info-icon');

//     infoIcons.forEach(function (icon) {
//         icon.addEventListener('click', function () {
//             const info = this.getAttribute('data-info');
//             const modalBody = document.getElementById('instrucoesModalBody');
//             modalBody.textContent = info;

//             $('#instrucoesModal').modal('show');
//         });
//     });
// });

document.addEventListener('DOMContentLoaded', function () {
    const infoIcons = document.querySelectorAll('.info-icon');

    infoIcons.forEach(function (icon) {
        icon.addEventListener('click', function () {
            const cardId = this.getAttribute('data-card-id');

            fetch(`/comum/api/get_instrucoes/${cardId}/`)
                .then(response => response.json())
                .then(data => {
                    const modalBody = document.getElementById('instrucoesModalBody');

                    // O HTML já foi convertido no servidor, então apenas insira-o no modal
                    modalBody.innerHTML = data.instrucoes;

                    $('#instrucoesModal').modal('show');
                });
        });
    });
});
