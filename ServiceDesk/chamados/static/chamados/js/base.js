document.addEventListener("DOMContentLoaded", () => {
    const formToFocus = document.querySelector(".js-form-focus");

    if (!formToFocus || !window.matchMedia("(pointer: fine)").matches) {
        return;
    }

    const firstField = formToFocus.querySelector(
        "input:not([type='hidden']):not([disabled]), select:not([disabled]), textarea:not([disabled])"
    );

    if (firstField instanceof HTMLElement) {
        firstField.focus();
    }
});
