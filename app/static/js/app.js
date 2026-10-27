// Ask before submitting any form marked with data-confirm (used for Delete).
// Without JavaScript the form still works; it just skips the prompt.
document.addEventListener("submit", function (event) {
  var message = event.target.getAttribute("data-confirm");
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
