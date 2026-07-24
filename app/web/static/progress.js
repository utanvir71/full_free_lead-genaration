(() => {
  const panel = document.querySelector("#run-progress");
  if (!panel || panel.dataset.terminal === "true") return;
  window.setInterval(() => window.location.reload(), 2000);
})();
