import 'htmx.org';

document.addEventListener("DOMContentLoaded", () => {
    const generateForm = document.querySelector("#generate-form");
    if (generateForm) {
        generateForm.addEventListener("submit", () => {
            const button = generateForm.querySelector("button[type=submit]");
            if (button) {
                button.disabled = true;
                button.dataset.originalText = button.textContent;
                button.textContent = "Generating…";
            }
            // The response is a file download, so the page never navigates
            // away — restore the button once the browser has it in hand.
            window.setTimeout(() => {
                if (button) {
                    button.disabled = false;
                    button.textContent = button.dataset.originalText;
                }
            }, 2000);
        });
    }
});
