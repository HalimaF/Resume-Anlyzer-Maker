const elements = {
  apiBase: document.getElementById("apiBase"),
  themeToggle: document.getElementById("themeToggle"),
  jobSelect: document.getElementById("jobSelect"),
  selectedJobInfo: document.getElementById("selectedJobInfo"),
  jobTitle: document.getElementById("jobTitle"),
  jobDescription: document.getElementById("jobDescription"),
  jobRequirements: document.getElementById("jobRequirements"),
  dropZone: document.getElementById("dropZone"),
  resumeInput: document.getElementById("resumeInput"),
  selectedFile: document.getElementById("selectedFile"),
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
  industryCheckSection: document.getElementById("industryCheckSection"),
  industryCheckInfo: document.getElementById("industryCheckInfo"),
  industryCheckResults: document.getElementById("industryCheckResults"),
};

let selectedFile = null;
let latestAnalysis = null;
let selectedJob = null;
let jobsDatabase = [];
const maxUploadBytes = 10 * 1024 * 1024;
const allowedExtensions = new Set(["pdf", "png", "jpg", "jpeg", "webp"]);

const DEFAULT_API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:5000"
    : "https://smart-resume-analyzer-api.onrender.com";

// Safe initialization
const savedApiBase = localStorage.getItem("resumeAnalyzerApiBase") || DEFAULT_API_BASE;
const apiBaseElem = elements.apiBase || document.getElementById("apiBase");
if (apiBaseElem) {
  apiBaseElem.value = savedApiBase;
}

const savedTheme = localStorage.getItem("resumeAnalyzerTheme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);
updateThemeButton(savedTheme);

function showToast(message, isError = false) {
  const toastElem = elements.toast || document.getElementById("toast");
  if (!toastElem) {
    console.log(isError ? `Error: ${message}` : `Info: ${message}`);
    return;
  }
  toastElem.textContent = message;
  toastElem.style.borderColor = isError ? "#e63946" : "";
  toastElem.classList.add("show");
  setTimeout(() => toastElem.classList.remove("show"), 2200);
}

function updateThemeButton(theme) {
  const themeBtnUpdate = elements.themeToggle || document.getElementById("themeToggle");
  if (!themeBtnUpdate) return;
  
  const icon = themeBtnUpdate.querySelector("i");
  const label = themeBtnUpdate.querySelector("span");
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

async function loadJobs() {
  try {
    const response = await fetch("./jobs.json");
    jobsDatabase = (await response.json()).jobs;
    
    jobsDatabase.forEach((job) => {
      const option = document.createElement("option");
      option.value = job.id;
      option.textContent = `${job.title} (${job.industry})`;
      elements.jobSelect.appendChild(option);
    });
  } catch (error) {
    console.error("Failed to load jobs database:", error);
  }
}

function handleJobSelection() {
  const selectedId = elements.jobSelect.value;
  if (!selectedId) {
    selectedJob = null;
    elements.selectedJobInfo.style.display = "none";
    elements.industryCheckInfo.textContent = "Select a job role to see industry-specific validation.";
    elements.industryCheckResults.innerHTML = "";
    return;
  }

  selectedJob = jobsDatabase.find((j) => j.id === selectedId);
  if (selectedJob) {
    elements.jobTitle.textContent = selectedJob.title;
    elements.jobDescription.textContent = selectedJob.description;

    let requirementsHtml = '<div class="job-requirements"><h5>Key Requirements:</h5>';
    selectedJob.keywordRequirements.forEach((req) => {
      requirementsHtml += `<span class="req-tag">${req}</span>`;
    });
    requirementsHtml += "</div>";
    elements.jobRequirements.innerHTML = requirementsHtml;

    elements.selectedJobInfo.style.display = "block";
    elements.industryCheckInfo.textContent = `Industry-level validation for ${selectedJob.title}`;
  }
}

function renderIndustryValidation(analysisData) {
  if (!selectedJob) {
    elements.industryCheckResults.innerHTML = "";
    return;
  }

  const detectedSkills = new Set(analysisData.detected_skills.map((s) => s.toLowerCase()));
  const requiredSkills = selectedJob.keywordRequirements.map((s) => s.toLowerCase());

  const matchedRequired = requiredSkills.filter((skill) =>
    Array.from(detectedSkills).some((detected) => detected.includes(skill.split(" ")[0].toLowerCase()))
  );

  const missingRequired = requiredSkills.filter((skill) =>
    !Array.from(detectedSkills).some((detected) => detected.includes(skill.split(" ")[0].toLowerCase()))
  );

  const presentSections = analysisData.structure_analysis?.present_sections || [];
  const missingRequiredSections = selectedJob.requiredSections.filter(
    (section) => !presentSections.some((s) => s.toLowerCase().includes(section.toLowerCase()))
  );

  let validationHtml = '<div class="validation-container">';
  
  if (matchedRequired.length > 0) {
    validationHtml += `<div class="validation-item pass">
      <h5><i class="fa-solid fa-check-circle"></i> Skills Match (${matchedRequired.length}/${requiredSkills.length})</h5>
      <div class="skills-chips">`;
    matchedRequired.forEach((skill) => {
      validationHtml += `<span class="skill-tag matched">${skill}</span>`;
    });
    validationHtml += "</div></div>";
  }

  if (missingRequired.length > 0) {
    validationHtml += `<div class="validation-item warning">
      <h5><i class="fa-solid fa-exclamation-circle"></i> Missing Skills (${missingRequired.length})</h5>
      <div class="skills-chips">`;
    missingRequired.forEach((skill) => {
      validationHtml += `<span class="skill-tag missing">${skill}</span>`;
    });
    validationHtml += "</div></div>";
  }

  if (missingRequiredSections.length > 0) {
    validationHtml += `<div class="validation-item warning">
      <h5><i class="fa-solid fa-folder-open"></i> Missing Resume Sections</h5>
      <ul style="margin: 8px 0;">`;
    missingRequiredSections.forEach((section) => {
      validationHtml += `<li>Add <strong>${section}</strong> section</li>`;
    });
    validationHtml += "</ul></div>";
  }

  const fitPercentage = Math.round((matchedRequired.length / requiredSkills.length) * 100);
  validationHtml += `<div class="fit-score">
    <div>Job Fit Score: <strong>${fitPercentage}%</strong></div>
    <div class="fit-bar"><div class="fit-fill" style="width: ${fitPercentage}%"></div></div>
  </div>`;

  validationHtml += "</div>";
  elements.industryCheckResults.innerHTML = validationHtml;
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
    elements.jdScore.textContent = "Add a job description or select a role to enable match analysis.";
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

  renderIndustryValidation(data);
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

async function analyzeResume() {
  if (!selectedFile) {
    showToast("Please upload a resume first.", true);
    return;
  }

  // Safely get API base URL with fallback
  const apiBaseInput = elements.apiBase || document.getElementById("apiBase");
  const apiBaseValue = apiBaseInput?.value?.trim() || DEFAULT_API_BASE;
  const apiBase = apiBaseValue.replace(/\/$/, "");
  
  if (!apiBase) {
    showToast("Please provide an API base URL.", true);
    return;
  }

  localStorage.setItem("resumeAnalyzerApiBase", apiBase);

  const formData = new FormData();
  formData.append("resume", selectedFile);

  // Safely get job description
  const jobDescriptionInput = elements.jobDescription || document.getElementById("jobDescription");
  let jdText = jobDescriptionInput?.value?.trim() || "";
  
  if (selectedJob && !jdText) {
    // Auto-generate JD context from selected job
    jdText = `Job: ${selectedJob.title}\nRequired Skills: ${selectedJob.keywordRequirements.join(", ")}`;
  }

  if (jdText) formData.append("job_description", jdText);

  // Safely disable button
  const analyzeBtnElem = elements.analyzeBtn || document.getElementById("analyzeBtn");
  if (analyzeBtnElem) {
    analyzeBtnElem.disabled = true;
    analyzeBtnElem.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
  }

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
    const analyzeBtnFinal = elements.analyzeBtn || document.getElementById("analyzeBtn");
    if (analyzeBtnFinal) {
      analyzeBtnFinal.disabled = false;
      analyzeBtnFinal.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Resume';
    }
  }
}

async function downloadReport() {
  if (!latestAnalysis) {
    showToast("No analysis data available.", true);
    return;
  }

  const apiBaseInput = elements.apiBase || document.getElementById("apiBase");
  const apiBase = apiBaseInput?.value?.trim().replace(/\/$/, "") || DEFAULT_API_BASE;

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
  const dropZoneElem = elements.dropZone || document.getElementById("dropZone");
  if (!dropZoneElem) return;
  
  const highlight = () => dropZoneElem.classList.add("active");
  const unhighlight = () => dropZoneElem.classList.remove("active");

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZoneElem.addEventListener(eventName, (event) => {
      event.preventDefault();
      highlight();
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZoneElem.addEventListener(eventName, (event) => {
      event.preventDefault();
      unhighlight();
    });
  });

  dropZoneElem.addEventListener("drop", (event) => {
    const files = event.dataTransfer.files;
    if (!files.length) return;
    setSelectedFile(files[0]);
  });

  const dropZoneClick = elements.dropZone || document.getElementById("dropZone");
  const resumeInputElem = elements.resumeInput || document.getElementById("resumeInput");
  
  if (dropZoneClick && resumeInputElem) {
    dropZoneClick.addEventListener("click", () => resumeInputElem.click());
    dropZoneClick.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        resumeInputElem.click();
      }
    });

    resumeInputElem.addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (!file) return;
      setSelectedFile(file);
    });
  }
}

// Safe theme toggle
const themeBtnElem = elements.themeToggle || document.getElementById("themeToggle");
if (themeBtnElem) {
  themeBtnElem.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("resumeAnalyzerTheme", next);
    updateThemeButton(next);
  });
}

// Safe analyze button click
const analyzeBtnInit = elements.analyzeBtn || document.getElementById("analyzeBtn");
if (analyzeBtnInit) analyzeBtnInit.addEventListener("click", analyzeResume);

// Safe download button click
const downloadBtnElem = elements.downloadReportBtn || document.getElementById("downloadReportBtn");
if (downloadBtnElem) downloadBtnElem.addEventListener("click", downloadReport);

// Safe skills search
const searchBtnElem = elements.searchSkillsBtn || document.getElementById("searchSkillsBtn");
if (searchBtnElem) searchBtnElem.addEventListener("click", loadSkillsCatalog);

const skillSearchElem = elements.skillSearch || document.getElementById("skillSearch");
if (skillSearchElem) {
  skillSearchElem.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadSkillsCatalog();
    }
  });
}

// Safe job selection
const jobSelectElem = elements.jobSelect || document.getElementById("jobSelect");
if (jobSelectElem) jobSelectElem.addEventListener("change", handleJobSelection);

bindUploadInteractions();
loadJobs();
loadSkillsCatalog();
