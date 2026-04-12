const bulkThemeToggle = document.getElementById("bulkThemeToggle");
const savedTheme = localStorage.getItem("resumeAnalyzerTheme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);

function updateBulkThemeButton(theme) {
  const icon = bulkThemeToggle.querySelector("i");
  if (theme === "dark") {
    icon.className = "fa-solid fa-sun";
  } else {
    icon.className = "fa-solid fa-moon";
  }
}

updateBulkThemeButton(savedTheme);
bulkThemeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("resumeAnalyzerTheme", next);
  updateBulkThemeButton(next);
});

const bulkApiBase = document.getElementById("bulkApiBase");
const bulkJobDesc = document.getElementById("bulkJobDesc");
const bulkDropZone = document.getElementById("bulkDropZone");
const bulkResumeInput = document.getElementById("bulkResumeInput");
const selectedFileCount = document.getElementById("selectedFileCount");
const bulkAnalyzeBtn = document.getElementById("bulkAnalyzeBtn");
const resultsSection = document.getElementById("resultsSection");
const candidatesTable = document.getElementById("candidatesTable");
const candidateSearch = document.getElementById("candidateSearch");
const scoreFilter = document.getElementById("scoreFilter");
const toast = document.getElementById("toast");

const DEFAULT_API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:5000"
    : "https://smart-resume-analyzer-api.onrender.com";

const savedApiBase = localStorage.getItem("resumeAnalyzerApiBase") || DEFAULT_API_BASE;
bulkApiBase.value = savedApiBase;

let selectedFiles = [];
let allCandidates = [];

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.style.borderColor = isError ? "#e63946" : "";
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function bindBulkUpload() {
  const highlight = () => bulkDropZone.classList.add("active");
  const unhighlight = () => bulkDropZone.classList.remove("active");

  ["dragenter", "dragover"].forEach((eventName) => {
    bulkDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      highlight();
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    bulkDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      unhighlight();
    });
  });

  bulkDropZone.addEventListener("drop", (e) => {
    selectedFiles = Array.from(e.dataTransfer.files);
    updateFileCount();
  });

  bulkDropZone.addEventListener("click", () => bulkResumeInput.click());
  bulkResumeInput.addEventListener("change", (e) => {
    selectedFiles = Array.from(e.target.files);
    updateFileCount();
  });
}

function updateFileCount() {
  selectedFileCount.textContent = selectedFiles.length === 0 ? "No files selected" : `${selectedFiles.length} file(s) selected`;
}

async function bulkAnalyze() {
  if (selectedFiles.length === 0) {
    showToast("Please select at least one resume.", true);
    return;
  }

  const apiBase = bulkApiBase.value.trim().replace(/\/$/, "");
  if (!apiBase) {
    showToast("Please provide an API base URL.", true);
    return;
  }

  localStorage.setItem("resumeAnalyzerApiBase", apiBase);

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append("resumes", file));

  const jd = bulkJobDesc.value.trim();
  if (jd) formData.append("job_description", jd);

  bulkAnalyzeBtn.disabled = true;
  bulkAnalyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';

  try {
    const response = await fetch(`${apiBase}/api/bulk-analyze`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "";
      let errorMsg = "Analysis failed";
      if (contentType.includes("application/json")) {
        const data = await response.json();
        errorMsg = data.error || errorMsg;
      }
      throw new Error(errorMsg);
    }

    const data = await response.json();
    allCandidates = data.ranked_candidates || [];
    displayResults(data);
    showToast(`Analyzed ${data.total_analyzed} candidates successfully.`);
  } catch (error) {
    showToast(error.message || "Failed to analyze resumes.", true);
  } finally {
    bulkAnalyzeBtn.disabled = false;
    bulkAnalyzeBtn.innerHTML = '<i class="fa-solid fa-play"></i> Analyze & Rank Candidates';
  }
}

function displayResults(data) {
  resultsSection.style.display = "block";
  renderCandidatesTable();
  updateAnalytics(data);
}

function renderCandidatesTable() {
  let html = `
    <table class="candidates-list">
      <thead>
        <tr>
          <th>Rank</th>
          <th>Candidate</th>
          <th>Overall Score</th>
          <th>Keyword Match</th>
          <th>ATS Compliance</th>
          <th>Structure</th>
          <th>Percentile</th>
        </tr>
      </thead>
      <tbody>
  `;

  let filtered = allCandidates.filter((c) => {
    const searchMatch = c.filename.toLowerCase().includes(candidateSearch.value.toLowerCase());
    const scoreThreshold = parseInt(scoreFilter.value) || 0;
    const scoreMatch = c.overall_score >= scoreThreshold;
    return searchMatch && scoreMatch;
  });

  filtered.forEach((candidate) => {
    const breakdown = candidate.score_breakdown || {};
    const keyword = breakdown.keyword_matching?.score || "--";
    const ats = breakdown.ats_compliance?.score || "--";
    const structure = breakdown.structure_format?.score || "--";

    html += `
      <tr class="score-${candidate.rank <= 3 ? "excellent" : candidate.overall_score >= 70 ? "good" : "fair"}">
        <td>#${candidate.rank}</td>
        <td><strong>${candidate.filename}</strong></td>
        <td>
          <span class="score-badge">${candidate.overall_score}/100</span>
        </td>
        <td>${keyword}</td>
        <td>${ats}</td>
        <td>${structure}</td>
        <td>${candidate.percentile}%</td>
      </tr>
    `;
  });

  html += `
      </tbody>
    </table>
  `;

  candidatesTable.innerHTML = html;
}

function updateAnalytics(data) {
  const candidates = data.ranked_candidates || [];
  if (candidates.length === 0) return;

  const scores = candidates.map((c) => c.overall_score);
  const avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  const topCandidate = candidates[0].filename.split(".")[0];
  const excellentCount = candidates.filter((c) => c.overall_score >= 85).length;

  document.getElementById("totalCandidates").textContent = candidates.length;
  document.getElementById("avgScore").textContent = avgScore;
  document.getElementById("topCandidate").textContent = topCandidate;
  document.getElementById("excellentCount").textContent = excellentCount;

  // Score distribution
  const distribution = {
    excellent: candidates.filter((c) => c.overall_score >= 85).length,
    good: candidates.filter((c) => c.overall_score >= 70 && c.overall_score < 85).length,
    fair: candidates.filter((c) => c.overall_score >= 55 && c.overall_score < 70).length,
    poor: candidates.filter((c) => c.overall_score < 55).length,
  };

  let distHtml = `
    <div class="distribution-bars">
      <div class="dist-bar">
        <div class="bar-label">Excellent (85+)</div>
        <div class="bar-fill" style="width: ${(distribution.excellent / candidates.length) * 100}%; background: var(--ok);"></div>
        <div class="bar-count">${distribution.excellent}</div>
      </div>
      <div class="dist-bar">
        <div class="bar-label">Good (70-84)</div>
        <div class="bar-fill" style="width: ${(distribution.good / candidates.length) * 100}%; background: var(--primary);"></div>
        <div class="bar-count">${distribution.good}</div>
      </div>
      <div class="dist-bar">
        <div class="bar-label">Fair (55-69)</div>
        <div class="bar-fill" style="width: ${(distribution.fair / candidates.length) * 100}%; background: var(--warn);"></div>
        <div class="bar-count">${distribution.fair}</div>
      </div>
      <div class="dist-bar">
        <div class="bar-label">Poor (<55)</div>
        <div class="bar-fill" style="width: ${(distribution.poor / candidates.length) * 100}%; background: #e63946;"></div>
        <div class="bar-count">${distribution.poor}</div>
      </div>
    </div>
  `;

  document.getElementById("scoreDistribution").innerHTML = distHtml;
}

candidateSearch.addEventListener("input", renderCandidatesTable);
scoreFilter.addEventListener("change", renderCandidatesTable);

document.getElementById("exportCsvBtn").addEventListener("click", () => {
  if (allCandidates.length === 0) {
    showToast("No candidates to export.", true);
    return;
  }

  let csv = "Rank,Candidate,Overall Score,Keyword Match,ATS,Structure,Percentile\n";
  allCandidates.forEach((c) => {
    const breakdown = c.score_breakdown || {};
    csv += `${c.rank},"${c.filename}",${c.overall_score},${breakdown.keyword_matching?.score || "N/A"},${breakdown.ats_compliance?.score || "N/A"},${breakdown.structure_format?.score || "N/A"},${c.percentile}\n`;
  });

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "candidates-ranking.csv";
  link.click();
  URL.revokeObjectURL(url);
  showToast("CSV exported successfully.");
});

document.getElementById("exportJsonBtn").addEventListener("click", () => {
  if (allCandidates.length === 0) {
    showToast("No candidates to export.", true);
    return;
  }

  const json = JSON.stringify(allCandidates, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "candidates-ranking.json";
  link.click();
  URL.revokeObjectURL(url);
  showToast("JSON exported successfully.");
});

document.getElementById("exportPdfBtn").addEventListener("click", () => {
  showToast("PDF export coming soon.", false);
});

bindBulkUpload();
bulkAnalyzeBtn.addEventListener("click", bulkAnalyze);
