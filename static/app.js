"use strict";

const form = document.querySelector("#context-form");
const status = document.querySelector("#input-status");

// This foundation intentionally has no submission, API call, or persistence.
form.addEventListener("submit", (event) => event.preventDefault());

document.querySelector("#clear-inputs").addEventListener("click", () => {
  if ([...form.querySelectorAll("textarea")].some((field) => field.value.trim())) {
    if (!window.confirm("Clear all three inputs? This cannot be undone.")) return;
  }
  form.reset();
  status.textContent = "Inputs cleared.";
  document.querySelector("#assignment").focus();
});

form.addEventListener("input", () => {
  status.textContent = "";
});
