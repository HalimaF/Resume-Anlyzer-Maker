const elements = {
  apiBase: document.getElementById("apiBase"),
  themeToggle: document.getElementById("themeToggle"),
  dropZone: document.getElementById("dropZone"),
  resumeInput: document.getElementById("resumeInput"),
  selectedFile: document.getElementById("selectedFile"),
  jobDescription: document.getElementById("jobDescription"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  scoreValue: document.getElementById("scoreValue"),
  scoreBar: document.getElementById("scoreBar"),
  detectedSkills: document.getElementById("detectedSkills"),
  missingSkills: document.getElementById("missingSkills"),
  topKeywords: document.getElementById("topKeywords"),
  summaryList: document.getElementById("summaryList"),
  suggestionsList: document.getElementById("suggestionsList"),
  jdScore: document.getElementById("jdScore"),
  matchedKeywords: document.getElementById("matchedKeywords"),
  missingKeywords: document.getElementById("missingKeywords"),
  structureScore: document.getElementById("structureScore"),
  presentSections: document.getElementById("presentSections"),
  missingSections: document.getElementById("missingSections"),
  atsTips: document.getElementById("atsTips"),
  atsScore: document.getElementById("atsScore"),
  atsPassedChecks: document.getElementById("atsPassedChecks"),
  atsFailedChecks: document.getElementById("atsFailedChecks"),
  atsRecommendations: document.getElementById("atsRecommendations"),
  skillSearch: document.getElementById("skillSearch"),
  searchSkillsBtn: document.getElementById("searchSkillsBtn"),
  skillsCatalog: document.getElementById("skillsCatalog"),
  downloadReportBtn: document.getElementById("downloadReportBtn"),
  toast: document.getElementById("toast"),
};

let selectedFile = null;
let latestAnalysis = null;
const maxUploadBytes = 10 * 1024 * 1024;
const allowedExtensions = new Set(["pdf", "png", "jpg", "jpeg", "webp"]);

const DEFAULT_API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:5000"
    : "https://smart-resume-analyzer-api.onrender.com";

const savedApiBase = localStorage.getItem("resumeAnalyzerApiBase") || DEFAULT_API_BASE;
elements.apiBase.value = savedApiBase;

const savedTheme = localStorage.getItem("resumeAnalyzerTheme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);
updateThemeButton(savedTheme);

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.style.borderColor = isError ? "#e63946" : "";
  elements.toast.classList.add("show");
  setTimeout(() => elements.toast.classList.remove("show"), 2200);
}

async function parseApiError(response, fallbackMessage) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const data = await response.json();
    return data.error || fallbackMessage;
  }

  const text = await response.text();
  return text || fallbackMessage;
}

function validateSelectedFile(file) {
  if (!file) {
    return "Please choose a file.";
  }

  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (!allowedExtensions.has(ext)) {
    return "Unsupported file type. Allowed: PDF, PNG, JPG, JPEG, WEBP.";
  }

  if (file.size > maxUploadBytes) {
    return "File too large. Maximum allowed size is 10 MB.";
  }

  return null;
}

function setSelectedFile(file) {
  const validationError = validateSelectedFile(file);
  if (validationError) {
    selectedFile = null;
    elements.selectedFile.textContent = "No file selected";
    showToast(validationError, true);
    return;
  }

  selectedFile = file;
  elements.selectedFile.textContent = `Selected: ${selectedFile.name}`;
}

function updateThemeButton(theme) {
  const icon = elements.themeToggle.querySelector("i");
  const label = elements.themeToggle.querySelector("span");
  if (theme === "dark") {
    icon.className = "fa-solid fa-sun";
    label.textContent = "Light Mode";
  } else {
    icon.className = "fa-solid fa-moon";
    label.textContent = "Dark Mode";
  }
}

function createChips(container, values, variant = "neutral") {
  container.innerHTML = "";
  if (!values || values.length === 0) {
    const fallback = document.createElement("span");
    fallback.className = "chip neutral";
    fallback.textContent = "No items";
    container.appendChild(fallback);
    return;
  }

  values.forEach((value) => {
    const chip = document.createElement("span");
    chip.className = `chip ${variant}`;
    chip.textContent = value;
    container.appendChild(chip);
  });
}

function createList(listEl, items) {
  listEl.innerHTML = "";
  (items || []).forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    listEl.appendChild(li);
  });
}

function renderAnalysis(data) {
  latestAnalysis = data;
  elements.downloadReportBtn.disabled = false;

  const score = data.resume_score || 0;
  elements.scoreValue.textContent = `${score}/100`;
  elements.scoreBar.style.width = `${Math.max(0, Math.min(100, score))}%`;

  createChips(elements.detectedSkills, data.detected_skills, "detected");
  createChips(elements.missingSkills, data.missing_skills, "missing");
  createChips(
    elements.topKeywords,
    (data.top_keywords || []).map((item) => `${item.keyword} (${item.count})`),
    "neutral"
  );

  createList(elements.summaryList, data.feedback?.professional_summary || []);
  createList(elements.suggestionsList, data.feedback?.suggestions || []);

  const jdData = data.job_description_analysis;
  if (jdData) {
    elements.jdScore.textContent = `Match Score: ${jdData.job_description_match_score}/100`;
    createChips(elements.matchedKeywords, jdData.matched_keywords || [], "detected");
    createChips(elements.missingKeywords, jdData.missing_jd_keywords || [], "missing");
  } else {
    elements.jdScore.textContent = "Add a job description to enable match analysis.";
    createChips(elements.matchedKeywords, [], "neutral");
    createChips(elements.missingKeywords, [], "neutral");
  }

  const structure = data.structure_analysis;
  if (structure) {
    elements.structureScore.textContent = `Section Coverage: ${structure.section_coverage_score}/100`;
    createChips(elements.presentSections, structure.present_sections || [], "detected");
    createChips(elements.missingSections, structure.missing_sections || [], "missing");
    createList(elements.atsTips, structure.ats_readiness_tips || []);
  } else {
    elements.structureScore.textContent = "Upload a resume to view structure coverage.";
    createChips(elements.presentSections, [], "neutral");
    createChips(elements.missingSections, [], "neutral");
    createList(elements.atsTips, []);
  }

  const atsCheck = data.ats_check;
  if (atsCheck) {
    elements.atsScore.textContent = `ATS Score: ${atsCheck.ats_score}/100 (${atsCheck.passed_checks}/${atsCheck.total_checks} checks passed)`;
    const checks = atsCheck.checks || {};
    const passed = Object.keys(checks).filter((key) => checks[key]).map((key) => key.replaceAll("_", " "));
    const failed = Object.keys(checks).filter((key) => !checks[key]).map((key) => key.replaceAll("_", " "));
    createChips(elements.atsPassedChecks, passed, "detected");
    createChips(elements.atsFailedChecks, failed, "missing");
    createList(elements.atsRecommendations, atsCheck.recommendations || []);
  } else {
    elements.atsScore.textContent = "Run analysis to view ATS checklist score.";
    createChips(elements.atsPassedChecks, [], "neutral");
    createChips(elements.atsFailedChecks, [], "neutral");
    createList(elements.atsRecommendations, []);
  }
}

async function loadSkillsCatalog() {
  const apiBase = elements.apiBase.value.trim().replace(/\/$/, "");
  if (!apiBase) return;

  const query = elements.skillSearch.value.trim();
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  params.set("limit", "80");

  try {
    const response = await fetch(`${apiBase}/api/skills?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Unable to load skills catalog.");
    }
    createChips(elements.skillsCatalog, data.skills || [], "neutral");
  } catch (error) {
    showToast(error.message || "Skills catalog request failed.", true);
  }
}

async function analyzeResume() {
  if (!selectedFile) {
    showToast("Please upload a resume first.", true);
    return;
  }

  const apiBase = elements.apiBase.value.trim().replace(/\/$/, "");
  if (!apiBase) {
    showToast("Please provide an API base URL.", true);
    return;
  }

  localStorage.setItem("resumeAnalyzerApiBase", apiBase);

  const formData = new FormData();
  formData.append("resume", selectedFile);

  const jd = elements.jobDescription.value.trim();
  if (jd) formData.append("job_description", jd);

  elements.analyzeBtn.disabled = true;
  elements.analyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';

  try {
    const response = await fetch(`${apiBase}/api/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const message = await parseApiError(response, "Analysis failed.");
      throw new Error(message);
    }

    const data = await response.json();

    renderAnalysis(data);
    showToast("Resume analysis complete.");
  } catch (error) {
    showToast(error.message || "Failed to analyze resume.", true);
  } finally {
    elements.analyzeBtn.disabled = false;
    elements.analyzeBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Resume';
  }
}

async function downloadReport() {
  if (!latestAnalysis) {
    showToast("No analysis data available.", true);
    return;
  }

  const apiBase = elements.apiBase.value.trim().replace(/\/$/, "");

  try {
    const response = await fetch(`${apiBase}/api/report/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(latestAnalysis),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "Report generation failed.");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "resume-analysis-report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showToast("PDF report downloaded.");
  } catch (error) {
    showToast(error.message || "Unable to download report.", true);
  }
}

function bindUploadInteractions() {
  const highlight = () => elements.dropZone.classList.add("active");
  const unhighlight = () => elements.dropZone.classList.remove("active");

  ["dragenter", "dragover"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      highlight();
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      unhighlight();
    });
  });

  elements.dropZone.addEventListener("drop", (event) => {
    const files = event.dataTransfer.files;
    if (!files.length) return;
    setSelectedFile(files[0]);
  });

  elements.dropZone.addEventListener("click", () => elements.resumeInput.click());
  elements.dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      elements.resumeInput.click();
    }
  });

  elements.resumeInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setSelectedFile(file);
  });
}

elements.themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("resumeAnalyzerTheme", next);
  updateThemeButton(next);
});

elements.analyzeBtn.addEventListener("click", analyzeResume);
elements.downloadReportBtn.addEventListener("click", downloadReport);
elements.searchSkillsBtn.addEventListener("click", loadSkillsCatalog);
elements.skillSearch.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadSkillsCatalog();
  }
});

bindUploadInteractions();
loadSkillsCatalog();
