const $ = (selector) => document.querySelector(selector);
const form = $("#symptomForm");
const symptoms = $("#symptoms");
const charCount = $("#charCount");
const analyzeBtn = $("#analyzeBtn");
const formError = $("#formError");
const processing = $("#processing");
const results = $("#results");
const dashboard = $("#resultsDashboard");
const emergencyBanner = $("#emergencyBanner");
let hasAssessment = false;

async function checkApiStatus() {
  const dot = $("#statusDot"), label = $("#statusText");
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    if (data.configured) {
      dot.className = "status-dot online";
      label.textContent = "AI service configured";
      label.title = `Configured model: ${data.model}`;
    } else {
      dot.className = "status-dot offline";
      label.textContent = "API key needed";
      label.title = "Add GROQ_API_KEY to .env";
    }
  } catch {
    dot.className = "status-dot offline";
    label.textContent = "Backend unavailable";
  }
}
checkApiStatus();

symptoms.addEventListener("input", () => {
  charCount.textContent = `${symptoms.value.length} / 5000`;
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    symptoms.value = button.dataset.example;
    symptoms.dispatchEvent(new Event("input"));
    symptoms.focus();
  });
});

function setupMagnetic() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll(".magnetic").forEach((button) => {
    button.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse") return;
      const rect = button.getBoundingClientRect();
      const x = (event.clientX - rect.left - rect.width / 2) * 0.08;
      const y = (event.clientY - rect.top - rect.height / 2) * 0.10;
      button.style.transform = `translate(${x}px, ${y}px)`;
    });
    button.addEventListener("pointerleave", () => { button.style.transform = ""; });
    button.addEventListener("pointerdown", () => { button.style.scale = ".98"; });
    button.addEventListener("pointerup", () => { button.style.scale = ""; });
  });
}
setupMagnetic();

function addText(parent, tag, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = text == null ? "" : String(text);
  parent.appendChild(node);
  return node;
}
function addList(parent, items) {
  const ul = document.createElement("ul");
  (Array.isArray(items) ? items : []).forEach((item) => addText(ul, "li", item));
  parent.appendChild(ul);
}
function card(title, icon, wide = false) {
  const section = document.createElement("section");
  section.className = `result-card${wide ? " wide" : ""}`;
  const heading = document.createElement("h3");
  const symbol = document.createElement("span");
  symbol.textContent = icon;
  heading.append(symbol, document.createTextNode(title));
  section.appendChild(heading);
  return section;
}
function renderResults(data) {
  dashboard.replaceChildren();
  const grid = document.createElement("div");
  grid.className = "dashboard-grid";

  const urgency = card("Urgency level", "◈");
  const level = String(data.emergency_level || "Unclear");
  addText(urgency, "span", level, `level-pill ${level.toLowerCase().replace(/\s/g, "-")}`);
  addText(urgency, "h4", data.urgency_title || "Assessment summary");
  addText(urgency, "p", data.care_recommendation || "");
  grid.appendChild(urgency);

  const summary = card("Symptom summary", "⌕");
  addText(summary, "p", data.summary || "No summary supplied.");
  grid.appendChild(summary);

  const conditions = card("Possible explanations", "✧", true);
  if (!Array.isArray(data.possible_conditions) || !data.possible_conditions.length) {
    addText(conditions, "p", "There is not enough information to list possible explanations. A qualified clinician can assess your symptoms.");
  } else {
    data.possible_conditions.forEach((item) => {
      const article = document.createElement("article");
      article.className = "condition";
      addText(article, "h4", item.name || "Possible explanation");
      addText(article, "p", item.explanation || "");
      if (item.supporting_symptoms?.length) {
        const support = document.createElement("p");
        addText(support, "b", "Reported symptoms that may fit: ");
        support.appendChild(document.createTextNode(item.supporting_symptoms.join(", ")));
        article.appendChild(support);
      }
      if (item.uncertainties?.length) {
        const uncertain = document.createElement("small");
        uncertain.textContent = `Uncertainties: ${item.uncertainties.join("; ")}`;
        article.appendChild(uncertain);
      }
      conditions.appendChild(article);
    });
  }
  grid.appendChild(conditions);

  const warnings = card("Warning signs to watch", "!");
  addList(warnings, data.warning_signs);
  if (!data.warning_signs?.length) addText(warnings, "p", "Seek urgent help if symptoms become severe or rapidly worsen.");
  grid.appendChild(warnings);

  const firstAid = card("What to do now", "✚");
  addList(firstAid, data.first_aid);
  grid.appendChild(firstAid);

  const questions = card("Follow-up questions", "↗", true);
  if (data.follow_up_questions?.length) addList(questions, data.follow_up_questions);
  else addText(questions, "p", "No follow-up questions provided. If symptoms change, reassess and seek professional care as needed.");
  grid.appendChild(questions);

  const disclaimer = card("Please remember", "ⓘ", true);
  addText(disclaimer, "p", data.disclaimer || "This is not a confirmed diagnosis and does not replace a qualified medical professional.");
  grid.appendChild(disclaimer);
  dashboard.appendChild(grid);

  const isEmergency = level === "Level 1" || data.emergency;
  emergencyBanner.hidden = !isEmergency;
  emergencyBanner.replaceChildren();
  if (isEmergency) {
    addText(emergencyBanner, "h3", "⚠ Emergency warning — act now");
    addText(emergencyBanner, "p", data.care_recommendation || data.emergency?.instruction || "Contact local emergency services now. In Pakistan, Rescue 1122 may be available. Do not delay care to continue this chat.");
  }
  results.hidden = false;
  hasAssessment = true;
  results.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}
function showError(message, emergency) {
  formError.hidden = false;
  formError.textContent = message;
  if (emergency) {
    emergencyBanner.hidden = false;
    emergencyBanner.replaceChildren();
    addText(emergencyBanner, "h3", "⚠ Emergency warning — act now");
    addText(emergencyBanner, "p", emergency.instruction || "Contact local emergency services now. In Pakistan, Rescue 1122 may be available. Do not drive yourself.");
    results.hidden = false;
    results.scrollIntoView({ behavior: "auto", block: "start" });
  }
}
async function submitSymptoms(text, isFollowUp = false) {
  formError.hidden = true;
  processing.hidden = false;
  results.hidden = true;
  analyzeBtn.disabled = true;
  analyzeBtn.querySelector(".btn-label").textContent = "Analyzing…";
  try {
    const payload = isFollowUp
      ? { symptoms: text, age_group: $("#ageGroup").value, duration: $("#duration").value, severity: $("#severity").value, additional_info: $("#additionalInfo").value }
      : { symptoms: text, age_group: $("#ageGroup").value, duration: $("#duration").value, severity: $("#severity").value, additional_info: $("#additionalInfo").value };
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    processing.hidden = true;
    if (!response.ok) {
      showError(data.error || "The assessment could not be completed. Please try again.", data.emergency);
      return;
    }
    formError.hidden = true;
    renderResults(data);
  } catch {
    processing.hidden = true;
    showError("Could not connect to the local backend. Make sure Flask is running and try again.");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.querySelector(".btn-label").textContent = "Analyze symptoms";
  }
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!symptoms.value.trim()) {
    showError("Enter your symptoms before starting an assessment.");
    symptoms.focus();
    return;
  }
  await submitSymptoms(symptoms.value.trim());
});
$("#newAssessment").addEventListener("click", async () => {
  try { await fetch("/api/clear", { method: "POST" }); } catch {}
  symptoms.value = "";
  symptoms.dispatchEvent(new Event("input"));
  $("#followUpInput").value = "";
  $("#followUpForm").hidden = true;
  results.hidden = true;
  processing.hidden = true;
  formError.hidden = true;
  hasAssessment = false;
  $("#checker").scrollIntoView({ behavior: "smooth" });
  symptoms.focus();
});
$("#followUpBtn").addEventListener("click", () => {
  $("#followUpForm").hidden = !$("#followUpForm").hidden;
  if (!$("#followUpForm").hidden) $("#followUpInput").focus();
});
$("#followUpForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = $("#followUpInput").value.trim();
  if (!value) return;
  $("#followUpInput").value = "";
  await submitSymptoms(value, true);
});
$("#clearBtn").addEventListener("click", async () => {
  try { await fetch("/api/clear", { method: "POST" }); } catch {}
  dashboard.replaceChildren();
  emergencyBanner.hidden = true;
  emergencyBanner.replaceChildren();
  results.hidden = true;
  $("#followUpForm").hidden = true;
  formError.hidden = true;
  hasAssessment = false;
});
