/* ============================================================================
   Bulk Review: score many resumes against one posting and rank them.
   ========================================================================= */

import {
  describeApiError,
  describeNetworkError,
  downloadBlob,
  escapeHtml,
  getApiBase,
  initTheme,
  mountApiSetting,
  mountChrome,
  mountDropZone,
  scoreTone,
  toast,
  validateFile,
} from "./shared.js";

const $ = (id) => document.getElementById(id);
const MAX_FILES = 25;

const el = {
  jobDesc: $("bulkJobDesc"),
  fileSummary: $("fileSummary"),
  analyzeBtn: $("bulkAnalyzeBtn"),
  emptyState: $("emptyState"),
  loadingState: $("loadingState"),
  loadingText: $("loadingText"),
  results: $("results"),
  metrics: $("metrics"),
  failuresPanel: $("failuresPanel"),
  failuresList: $("failuresList"),
  candidateRows: $("candidateRows"),
  tableCount: $("tableCount"),
  search: $("candidateSearch"),
  scoreFilter: $("scoreFilter"),
  distribution: $("distribution"),
};

let files = [];
let candidates = [];

/* ---- file selection ------------------------------------------------------ */

function describeSelection() {
  const icon = el.fileSummary.querySelector("i");
  const text = el.fileSummary.querySelector("span");
  if (files.length === 0) {
    el.fileSummary.classList.remove("has-file");
    icon.className = "fa-regular fa-circle";
    text.textContent = "No files chosen yet";
    el.fileSummary.querySelector(".clear")?.remove();
    return;
  }

  el.fileSummary.classList.add("has-file");
  icon.className = "fa-solid fa-circle-check";
  text.textContent = `${files.length} file${files.length === 1 ? "" : "s"} ready`;

  if (!el.fileSummary.querySelector(".clear")) {
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "clear";
    clear.textContent = "Clear all";
    clear.addEventListener("click", () => {
      files = [];
      describeSelection();
    });
    el.fileSummary.appendChild(clear);
  }
}

function acceptFiles(fileList) {
  const rejected = [];
  const accepted = [];

  Array.from(fileList).forEach((file) => {
    const error = validateFile(file);
    if (error) rejected.push(error);
    else accepted.push(file);
  });

  // Add to the existing selection so several drops build one batch.
  const combined = [...files, ...accepted];
  files = combined.slice(0, MAX_FILES);
  if (combined.length > MAX_FILES) {
    rejected.push(`${combined.length - MAX_FILES} file(s) exceeded the ${MAX_FILES}-file batch limit.`);
  }

  describeSelection();
  if (rejected.length) {
    toast(rejected.length === 1 ? rejected[0] : `${rejected.length} files skipped. ${rejected[0]}`, true);
  }
}

/* ---- view state ---------------------------------------------------------- */

function showState(state) {
  el.emptyState.hidden = state !== "empty";
  el.loadingState.hidden = state !== "loading";
  el.results.hidden = state !== "results";
}

/* ---- rendering ----------------------------------------------------------- */

function renderMetrics(data) {
  const scores = candidates.map((candidate) => candidate.overall_score);
  const average = scores.length
    ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)
    : 0;
  const top = candidates[0];
  const strong = candidates.filter((candidate) => candidate.overall_score >= 70).length;

  el.metrics.innerHTML = `
    <div class="metric"><dt>Scored</dt><dd class="tabular">${data.total_analyzed}</dd></div>
    <div class="metric"><dt>Average score</dt><dd class="tabular">${average}</dd></div>
    <div class="metric"><dt>Worth interviewing</dt><dd class="tabular">${strong}</dd></div>
    <div class="metric"><dt>Top candidate</dt><dd class="is-text">${
      top ? escapeHtml(top.filename.replace(/\.[^.]+$/, "")) : "—"
    }</dd></div>`;
}

function renderFailures(failures) {
  if (!failures?.length) {
    el.failuresPanel.hidden = true;
    return;
  }
  el.failuresPanel.hidden = false;
  el.failuresList.innerHTML = failures
    .map((failure) => `<li><strong>${escapeHtml(failure.filename)}</strong> — ${escapeHtml(failure.error)}</li>`)
    .join("");
}

function renderTable() {
  const query = (el.search.value || "").trim().toLowerCase();
  const threshold = Number(el.scoreFilter.value) || 0;

  const visible = candidates.filter(
    (candidate) =>
      candidate.filename.toLowerCase().includes(query) && candidate.overall_score >= threshold
  );

  el.tableCount.textContent =
    visible.length === candidates.length
      ? `${candidates.length} candidate${candidates.length === 1 ? "" : "s"}`
      : `${visible.length} of ${candidates.length} shown`;

  if (!visible.length) {
    el.candidateRows.innerHTML = `
      <tr><td colspan="7" style="text-align:center;color:var(--ink-3);padding:28px">
        No candidate matches that filter.
      </td></tr>`;
    return;
  }

  // A score of 0 is a real value, so only fall back when genuinely absent.
  const cell = (value) => (Number.isFinite(value) ? value : "—");

  el.candidateRows.innerHTML = visible
    .map((candidate) => {
      const breakdown = candidate.score_breakdown || {};
      const tone = scoreTone(candidate.overall_score);
      return `
        <tr>
          <td>${cell(candidate.rank)}</td>
          <td><strong style="font-variant-numeric:normal">${escapeHtml(candidate.filename)}</strong></td>
          <td><span class="score-pill" data-tone="${tone}">${cell(candidate.overall_score)}</span></td>
          <td>${cell(breakdown.keyword_matching?.score)}</td>
          <td>${cell(breakdown.ats_compliance?.score)}</td>
          <td>${cell(breakdown.structure_format?.score)}</td>
          <td>${cell(candidate.percentile)}%</td>
        </tr>`;
    })
    .join("");
}

function renderDistribution() {
  if (!candidates.length) return;
  const total = candidates.length;
  const bands = [
    { label: "Ready to send", min: 85, max: 101, color: "var(--good)" },
    { label: "Nearly there", min: 70, max: 85, color: "var(--accent)" },
    { label: "Needs work", min: 55, max: 70, color: "var(--warn)" },
    { label: "Not ready", min: 0, max: 55, color: "var(--bad)" },
  ];

  el.distribution.innerHTML = bands
    .map((band) => {
      const count = candidates.filter(
        (candidate) => candidate.overall_score >= band.min && candidate.overall_score < band.max
      ).length;
      return `
        <div class="dist-row">
          <span>${band.label}</span>
          <div class="dist-track">
            <div class="dist-fill" style="background:${band.color}" data-width="${(count / total) * 100}"></div>
          </div>
          <span class="dist-count">${count}</span>
        </div>`;
    })
    .join("");

  requestAnimationFrame(() => {
    el.distribution.querySelectorAll(".dist-fill").forEach((fill) => {
      fill.style.transform = `scaleX(${Number(fill.dataset.width) / 100})`;
    });
  });
}

/* ---- request ------------------------------------------------------------- */

async function analyze() {
  if (!files.length) {
    toast("Add at least one resume first.", true);
    return;
  }

  const apiBase = getApiBase();
  const form = new FormData();
  files.forEach((file) => form.append("resumes", file));
  const jd = (el.jobDesc.value || "").trim();
  if (jd) form.append("job_description", jd);

  el.analyzeBtn.disabled = true;
  el.loadingText.textContent = `Reading ${files.length} resume${files.length === 1 ? "" : "s"}. Scanned files take longer.`;
  showState("loading");

  try {
    const response = await fetch(`${apiBase}/api/bulk-analyze`, { method: "POST", body: form });
    if (!response.ok) {
      throw new Error(await describeApiError(response, "The batch could not be scored."));
    }
    const data = await response.json();
    candidates = data.ranked_candidates || [];

    if (!candidates.length) {
      showState("empty");
      renderFailures(data.failures);
      toast("No resume in that batch could be read.", true);
      return;
    }

    renderMetrics(data);
    renderFailures(data.failures);
    renderTable();
    renderDistribution();
    showState("results");
    toast(
      data.failed_count
        ? `Scored ${data.total_analyzed}. ${data.failed_count} could not be read.`
        : `Scored ${data.total_analyzed} candidates.`,
      Boolean(data.failed_count)
    );
  } catch (error) {
    const message = error instanceof TypeError ? describeNetworkError(apiBase) : error.message;
    toast(message, true);
    showState(candidates.length ? "results" : "empty");
  } finally {
    el.analyzeBtn.disabled = false;
  }
}

/* ---- export -------------------------------------------------------------- */

/** Quote a CSV field and neutralise spreadsheet formula injection. */
function csvCell(value) {
  let text = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}

function exportCsv() {
  if (!candidates.length) {
    toast("Score a batch first.", true);
    return;
  }
  const value = (input) => (Number.isFinite(input) ? input : "N/A");
  const rows = [["Rank", "Candidate", "Overall", "Skills", "ATS", "Structure", "Percentile"]];
  candidates.forEach((candidate) => {
    const breakdown = candidate.score_breakdown || {};
    rows.push([
      value(candidate.rank),
      candidate.filename,
      value(candidate.overall_score),
      value(breakdown.keyword_matching?.score),
      value(breakdown.ats_compliance?.score),
      value(breakdown.structure_format?.score),
      value(candidate.percentile),
    ]);
  });

  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
  // BOM keeps non-ASCII candidate names readable when Excel opens the file.
  downloadBlob(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }), "candidate-ranking.csv");
  toast("CSV exported.");
}

function exportJson() {
  if (!candidates.length) {
    toast("Score a batch first.", true);
    return;
  }
  downloadBlob(
    new Blob([JSON.stringify(candidates, null, 2)], { type: "application/json" }),
    "candidate-ranking.json"
  );
  toast("JSON exported.");
}

/* ---- init ---------------------------------------------------------------- */

mountChrome();
initTheme();
mountApiSetting();
mountDropZone("bulkDropZone", "bulkResumeInput", acceptFiles);

el.analyzeBtn.addEventListener("click", analyze);
el.search.addEventListener("input", renderTable);
el.scoreFilter.addEventListener("change", renderTable);
$("exportCsvBtn").addEventListener("click", exportCsv);
$("exportJsonBtn").addEventListener("click", exportJson);

showState("empty");
