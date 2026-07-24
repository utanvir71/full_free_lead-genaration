document.addEventListener("DOMContentLoaded", () => {
  const button = document.querySelector("#copy-draft");
  const body = document.querySelector("#draft-body");
  if (!(button instanceof HTMLButtonElement) || !(body instanceof HTMLElement)) {
    return;
  }
  button.addEventListener("click", () => {
    void navigator.clipboard.writeText(body.innerText);
  });
});
