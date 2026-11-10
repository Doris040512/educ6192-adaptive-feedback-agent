"use strict";

const form = document.querySelector("#context-form");
const status = document.querySelector("#input-status");

const decideButton = document.querySelector("#decide-button");
const clearButton = document.querySelector("#clear-inputs");
const exampleButton = document.querySelector("#load-example");
const activityStatus = document.querySelector("#activity-status");
const activityAction = document.querySelector("#activity-action");
const activityExplanation = document.querySelector("#activity-explanation");
const activityQuestion = document.querySelector("#activity-question");
const activityEvidence = document.querySelector("#activity-evidence");

function showActivity(label, action, explanation, question = null, evidence = []) {
  activityStatus.textContent = label;
  activityAction.textContent = action;
  activityExplanation.textContent = explanation;
  activityQuestion.textContent = question || "";
  activityQuestion.hidden = !question;
  activityEvidence.replaceChildren();
  if (evidence.length) {
    const heading = document.createElement("strong");
    heading.textContent = "Relevant rubric evidence";
    activityEvidence.append(heading);
    const list = document.createElement("ul");
    evidence.forEach((item) => {
      const entry = document.createElement("li");
      entry.textContent = `${item.criterion}: “${item.excerpt}”`;
      list.append(entry);
    });
    activityEvidence.append(list);
    activityEvidence.hidden = false;
  } else {
    activityEvidence.hidden = true;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (decideButton.disabled) return;
  decideButton.disabled = true;
  clearButton.disabled = true;
  exampleButton.disabled = true;
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
      assessment_error: "Assessment error",
      decision_complete: "Decision complete",
    };
    if (!labels[result.status] || typeof result.explanation !== "string") {
      throw new Error("Unexpected response");
    }
    if (result.status === "decision_complete" &&
        (!response.ok || !["CLARIFY", "ANALYZE"].includes(result.action) ||
         !["consistent", "ambiguous", "contradictory"].includes(result.consistency_status) ||
         !Array.isArray(result.evidence))) {
      throw new Error("Invalid decision");
    }
    showActivity(labels[result.status], result.action || "No decision made",
      result.explanation, result.clarification_question, result.evidence || []);
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
    exampleButton.disabled = false;
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

// This fictional example is safe for classroom demonstrations and requires no API call to load.
exampleButton.addEventListener("click", () => {
  const hasInputs = [...form.querySelectorAll("textarea")].some((field) => field.value.trim());
  if (hasInputs && !window.confirm("Replace the current inputs with a fictional example?")) return;
  document.querySelector("#assignment").value =
    "Write one paragraph explaining whether AI tools should be used for studying. State a clear position and support it with two reasons.";
  document.querySelector("#rubric").value =
    "Position (2 points): a clear position on AI use. Reasons (4 points): two relevant reasons with explanations. Organization (2 points): ideas presented in a logical sequence.";
  document.querySelector("#student-response").value =
    "AI can support studying because it provides practice questions and can explain difficult ideas in simpler words.";
  showActivity("Example loaded", "Ready to check",
    "This fictional example has clear criteria. Submit it to check whether the rubric is sufficiently consistent. No decision has been made yet.");
  status.textContent = "Example loaded. You may edit it before checking.";
  document.querySelector("#assignment").focus();
});
