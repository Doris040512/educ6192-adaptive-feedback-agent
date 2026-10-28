"use strict";

const form = document.querySelector("#context-form");
const status = document.querySelector("#input-status");

const decideButton = document.querySelector("#decide-button");
const clearButton = document.querySelector("#clear-inputs");
const activityStatus = document.querySelector("#activity-status");
const activityAction = document.querySelector("#activity-action");
const activityExplanation = document.querySelector("#activity-explanation");
const activityQuestion = document.querySelector("#activity-question");

function showActivity(label, action, explanation, question = null) {
  activityStatus.textContent = label;
  activityAction.textContent = action;
  activityExplanation.textContent = explanation;
  activityQuestion.textContent = question || "";
  activityQuestion.hidden = !question;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (decideButton.disabled) return;
  decideButton.disabled = true;
  clearButton.disabled = true;
  const fields = [...form.querySelectorAll("textarea")];
  fields.forEach((field) => { field.readOnly = true; });
  status.textContent = "Checking inputs and requesting a decision…";
  showActivity("Checking", "Decision pending", "No action has been selected yet.");
  try {
    const response = await fetch("/api/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
      signal: AbortSignal.timeout(45000),
    });
    const result = await response.json();
    const labels = {
      validation_error: "Input needed",
      configuration_error: "Not configured",
      api_error: "API error",
      decision_complete: "Decision complete",
    };
    if (!labels[result.status] || typeof result.explanation !== "string") {
      throw new Error("Unexpected response");
    }
    if (result.status === "decision_complete" &&
        (!response.ok || !["CLARIFY", "ANALYZE"].includes(result.action))) {
      throw new Error("Invalid decision");
    }
    showActivity(labels[result.status], result.action || "No decision made",
      result.explanation, result.clarification_question);
    status.textContent = result.status === "decision_complete"
      ? "Decision received. No analysis or feedback has been generated."
      : result.explanation;
  } catch {
    showActivity("Request error", "No decision received",
      "The backend could not be reached or returned an unexpected response. Please try again.");
    status.textContent = "Request failed. No successful decision is available.";
  } finally {
    decideButton.disabled = false;
    clearButton.disabled = false;
    fields.forEach((field) => { field.readOnly = false; });
  }
});

document.querySelector("#clear-inputs").addEventListener("click", () => {
  if ([...form.querySelectorAll("textarea")].some((field) => field.value.trim())) {
    if (!window.confirm("Clear all three inputs? This cannot be undone.")) return;
  }
  form.reset();
  showActivity("Not checked", "No decision requested",
    "Check the next action to request one agent decision. There is no autonomous loop.");
  status.textContent = "Inputs cleared.";
  document.querySelector("#assignment").focus();
});

form.addEventListener("input", () => {
  status.textContent = "";
  showActivity("Inputs changed", "New decision needed",
    "The inputs have changed. Check the next action again.");
});
