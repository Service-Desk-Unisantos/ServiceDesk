document.addEventListener("DOMContentLoaded", () => {
    // Mantem o foco automatico no primeiro campo em dispositivos com mouse.
    const formToFocus = document.querySelector(".js-form-focus");
    if (formToFocus && window.matchMedia("(pointer: fine)").matches) {
        const firstField = formToFocus.querySelector(
            "input:not([type='hidden']):not([disabled]), select:not([disabled]), textarea:not([disabled])"
        );

        if (firstField instanceof HTMLElement) {
            firstField.focus();
        }
    }

});

// Funcao global chamada no onclick do botao para garantir a execucao imediata do toggle.
function alternarVisibilidadeSenha(toggleButton) {
    // Usa id explicito para vincular cada botao ao campo de senha correto.
    const targetId = toggleButton.getAttribute("data-password-target");
    const passwordInput = targetId ? document.getElementById(targetId) : null;
    if (!(passwordInput instanceof HTMLInputElement)) {
        return;
    }

    const senhaEstaVisivel = passwordInput.type === "text";
    passwordInput.type = senhaEstaVisivel ? "password" : "text";

    // Troca o icone para refletir o estado atual da senha.
    const icon = toggleButton.querySelector("i");
    if (icon instanceof HTMLElement) {
        icon.classList.toggle("bi-eye", senhaEstaVisivel);
        icon.classList.toggle("bi-eye-slash", !senhaEstaVisivel);
    }

    // Atualiza texto de acessibilidade para leitor de tela.
    toggleButton.setAttribute(
        "aria-label",
        senhaEstaVisivel ? "Mostrar senha" : "Ocultar senha"
    );
}
