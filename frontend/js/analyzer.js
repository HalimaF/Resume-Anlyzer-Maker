/* ============================================================================
   Resume Analyzer + Job Match.

   Both pages share this script; it adapts to whichever elements the host page
   provides, and to whether that page treats the target role as optional
   (analyzer) or as the point of the exercise (job-finder).
   ========================================================================= */

import {
  animateNumber,
  describeApiError,
  describeNetworkError,
  downloadBlob,
  escapeHtml,
  formatBytes,
  getApiBase,
  initTheme,
  mountApiSetting,
  mountChrome,
  mountDropZone,
  scoreBand,
  scoreTone,
  toast,
  validateFile,
} from "./shared.js";

const $ = (id) => document.getElementById(id);

const el = {
  dropZone: $("dropZone"),
  selectedFile: $("selectedFile"),
  analyzeBtn: $("analyzeBtn"),
  reanalyzeBtn: $("reanalyzeBtn"),
  downloadBtn: $("downloadReportBtn"),
  jobSelect: $("jobSelect"),
  jobDescription: $("jobDescription"),
  jobBrief: $("jobBrief"),
  jobBriefText: $("jobBriefText"),
  jobBriefSkills: $("jobBriefSkills"),
  targetDisclosure: $("targetDisclosure"),
  targetState: $("targetState"),
  emptyState: $("emptyState"),
  loadingState: $("loadingState"),
  results: $("results"),
  verdict: $("verdict"),
  scoreValue: $("scoreValue"),
  scoreMeter: $("scoreMeter"),
  scoreBand: $("scoreBand"),
  verdictHeadline: $("verdictHeadline"),
  verdictText: $("verdictText"),
  verdictFacts: $("verdictFacts"),
  actionsList: $("actionsList"),
  actionsTotal: $("actionsTotal"),
  actionsPanel: $("actionsPanel"),
  scoreBreakdown: $("scoreBreakdown"),
  skillGroups: $("skillGroups"),
  skillCount: $("skillCount"),
  disclaimedBlock: $("disclaimedBlock"),
  disclaimedList: $("disclaimedList"),
  matchPanel: $("matchPanel"),
  matchSummary: $("matchSummary"),
  matchedSkills: $("matchedSkills"),
  missingSkillsList: $("missingSkillsList"),
  missingKeywords: $("missingKeywords"),
  atsChecklist: $("atsChecklist"),
  atsSummary: $("atsSummary"),
  presentSections: $("presentSections"),
  missingSections: $("missingSections"),
  structureSummary: $("structureSummary"),
  aiPanel: $("aiPanel"),
  aiBody: $("aiBody"),
  aiModel: $("aiModel"),
  aiStatus: $("aiStatus"),
};

// job-finder.html marks itself as role-first; the analyzer treats a role as optional.
const ROLE_REQUIRED = document.body.dataset.roleRequired === "true";

let selectedFile = null;
let latestAnalysis = null;
let jobs = [];
let selectedJob = null;

/* ---- small helpers ------------------------------------------------------- */

function renderChips(container, values, variant = "", emptyText = "None") {
  if (!container) return;
  if (!values || values.length === 0) {
    container.innerHTML = `<span class="chip is-empty">${escapeHtml(emptyText)}</span>`;
    return;
  }
  container.innerHTML = values
    .map((value) => `<span class="chip ${variant}">${escapeHtml(value)}</span>`)
    .join("");
}

function titleCase(value) {
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}

const BREAKDOWN_LABELS = {
  ats_compliance: "ATS compliance",
  structure_format: "Structure & format",
  keyword_matching: "Keyword matching",
  content_quality: "Content quality",
  experience_relevance: "Experience relevance",
};

const CHECK_LABELS = {
  has_contact_email: "Email address is findable",
  has_contact_phone: "Phone number is findable",
  has_experience_section: "Experience section is clearly headed",
  has_education_section: "Education section is clearly headed",
  has_skills_section: "Skills section is clearly headed",
  has_action_verbs: "Bullets open with action verbs",
  reasonable_length: "Length is in the readable range",
  keyword_density_ok: "Enough specific skills are named",
};

/* ---- view state ---------------------------------------------------------- */

function showState(state) {
  if (el.emptyState) el.emptyState.hidden = state !== "empty";
  if (el.loadingState) el.loadingState.hidden = state !== "loading";
  if (el.results) el.results.hidden = state !== "results";
}

function setBusy(isBusy) {
  if (!el.analyzeBtn) return;
  el.analyzeBtn.disabled = isBusy;
  const label = el.analyzeBtn.querySelector("span");
  const icon = el.analyzeBtn.querySelector("i");
  if (label) label.textContent = isBusy ? "Analyzing…" : el.analyzeBtn.dataset.label;
  if (icon) {
    icon.className = isBusy ? "fa-solid fa-spinner fa-spin" : "fa-solid fa-wand-magic-sparkles";
  }
}

/* ---- file selection ------------------------------------------------------ */

function setSelectedFile(file) {
  const error = validateFile(file);
  const icon = el.selectedFile?.querySelector("i");
  const text = el.selectedFile?.querySelector("span");

  if (error) {
    selectedFile = null;
    el.selectedFile?.classList.remove("has-file");
    if (icon) icon.className = "fa-regular fa-circle";
    if (text) text.textContent = "No file chosen yet";
    toast(error, true);
    return;
  }

  selectedFile = file;
  el.selectedFile?.classList.add("has-file");
  if (icon) icon.className = "fa-solid fa-circle-check";
  if (text) text.textContent = `${file.name} · ${formatBytes(file.size)}`;

  // Offer a way back out; a chosen file the user cannot unchoose is a trap.
  if (!el.selectedFile.querySelector(".clear")) {
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "clear";
    clear.textContent = "Remove";
    clear.addEventListener("click", (event) => {
      event.stopPropagation();
      selectedFile = null;
      el.selectedFile.classList.remove("has-file");
      if (icon) icon.className = "fa-regular fa-circle";
      if (text) text.textContent = "No file chosen yet";
      clear.remove();
    });
    el.selectedFile.appendChild(clear);
  }
}

/* ---- target job ---------------------------------------------------------- */

async function loadJobs() {
  if (!el.jobSelect) return;
  try {
    const response = await fetch("./jobs.json");
    jobs = (await response.json()).jobs || [];
    el.jobSelect.insertAdjacentHTML(
      "beforeend",
      jobs
        .map(
          (job) =>
            `<option value="${escapeHtml(job.id)}">${escapeHtml(job.title)} — ${escapeHtml(
              job.industry
            )}</option>`
        )
        .join("")
    );
  } catch {
    toast("Could not load the role list. You can still paste a job description.", true);
  }
}

function onJobChange() {
  selectedJob = jobs.find((job) => job.id === el.jobSelect.value) || null;

  if (!selectedJob) {
    if (el.jobBrief) el.jobBrief.hidden = true;
    if (el.targetState) el.targetState.textContent = "— optional, but it sharpens everything";
    return;
  }

  if (el.jobBriefText) el.jobBriefText.textContent = selectedJob.description;
  renderChips(el.jobBriefSkills, selectedJob.keywordRequirements, "");
  if (el.jobBrief) el.jobBrief.hidden = false;
  if (el.targetState) el.targetState.textContent = `— ${selectedJob.title}`;
}

/** The text actually sent as the job description. */
function targetJobText() {
  const pasted = (el.jobDescription?.value || "").trim();
  if (pasted) return pasted;
  if (selectedJob) {
    return `${selectedJob.title}. ${selectedJob.description}\nRequired skills: ${selectedJob.keywordRequirements.join(
      ", "
    )}`;
  }
  return "";
}

/* ---- rendering ----------------------------------------------------------- */

function renderVerdict(data) {
  const score = Math.max(0, Math.min(100, Number(data.resume_score) || 0));
  const tone = scoreTone(score);

  el.verdict.dataset.tone = tone;
  animateNumber(el.scoreValue, score);
  el.scoreBand.textContent = scoreBand(score);
  // Deferred a frame so the transition has a 0 -> n change to animate.
  // Scaling rather than resizing keeps the animation off the layout path.
  requestAnimationFrame(() => {
    el.scoreMeter.style.transform = `scaleX(${score / 100})`;
  });

  const actions = data.feedback?.priority_actions || [];
  const topGain = actions.reduce((sum, action) => sum + (action.impact_points || 0), 0);

  el.verdictHeadline.textContent =
    actions.length > 0
      ? `${actions.length} fix${actions.length === 1 ? "" : "es"} worth about ${Math.round(
          topGain
        )} points`
      : "Nothing left to fix";
  el.verdictText.textContent = data.feedback?.verdict || "";

  const metrics = data.quality_metrics || {};
  const facts = [
    [`${metrics.detected_skills_count ?? 0}`, "skills found"],
    [`${metrics.text_length ?? 0}`, "words"],
  ];
  if (metrics.bullet_count) {
    facts.push([`${metrics.quantified_bullets}/${metrics.bullet_count}`, "bullets with numbers"]);
  }
  if (metrics.years_of_experience) {
    facts.push([`${Math.round(metrics.years_of_experience)}`, "years inferred"]);
  }
  if (data.meta?.has_job_description) {
    facts.push([
      `${data.job_description_analysis?.job_description_match_score ?? 0}%`,
      "job match",
    ]);
  }

  el.verdictFacts.innerHTML = facts
    .map(([value, label]) => `<span class="verdict-fact"><b>${escapeHtml(value)}</b> ${escapeHtml(label)}</span>`)
    .join("");
}

function renderActions(data) {
  const actions = data.feedback?.priority_actions || [];
  const strengths = data.feedback?.strengths || [];

  if (actions.length === 0) {
    el.actionsList.innerHTML = `
      <li class="action">
        <span class="action-title">This resume is in good shape</span>
        <p class="action-detail">
          Every check passed. Keep tailoring the wording to each specific posting.
        </p>
      </li>`;
    el.actionsTotal.textContent = "";
  } else {
    const total = actions.reduce((sum, action) => sum + (action.impact_points || 0), 0);
    el.actionsTotal.textContent = `up to +${Math.round(total)} points`;
    el.actionsList.innerHTML = actions
      .map((action) => {
        const impact = Number(action.impact_points) || 0;
        const impactHtml = impact
          ? `<span class="action-impact">+${impact}</span>`
          : `<span class="action-impact is-zero">Worth doing</span>`;
        return `
          <li class="action">
            <span class="action-title">${escapeHtml(action.title)}</span>
            <p class="action-detail">${escapeHtml(action.detail)}</p>
            <span class="action-meta">
              ${impactHtml}
              <span class="action-effort">${escapeHtml(action.effort || "")}</span>
            </span>
          </li>`;
      })
      .join("");
  }

  // Strengths belong beside the fixes: a list of only problems misreads a
  // good resume as a bad one.
  const existing = el.actionsPanel.querySelector(".strengths-callout");
  existing?.remove();
  if (strengths.length) {
    el.actionsPanel.insertAdjacentHTML(
      "beforeend",
      `<div class="callout is-info strengths-callout" style="margin-top:20px">
         <strong>Already working:</strong> ${strengths.map(escapeHtml).join(" ")}
       </div>`
    );
  }
}

function renderBreakdown(breakdown) {
  const entries = Object.entries(breakdown || {}).filter(([, data]) => data && typeof data === "object");
  if (!entries.length) {
    el.scoreBreakdown.innerHTML = '<p class="empty-hint">No breakdown available.</p>';
    return;
  }

  // Flask serialises with sorted keys; order by weight so the heaviest driver
  // of the score reads first.
  entries.sort(([aName, a], [bName, b]) => {
    const byWeight = (Number(b.weight) || 0) - (Number(a.weight) || 0);
    return byWeight !== 0 ? byWeight : aName.localeCompare(bName);
  });

  el.scoreBreakdown.innerHTML = entries
    .map(([name, data]) => {
      const score = Math.max(0, Math.min(100, Number(data.score) || 0));
      const weight = Math.round((Number(data.weight) || 0) * 100);
      return `
        <div class="breakdown-row">
          <span class="breakdown-label">${escapeHtml(BREAKDOWN_LABELS[name] || titleCase(name))}</span>
          <span class="breakdown-value tabular">${score}<span class="breakdown-weight"> · ${weight}% weight</span></span>
          <div class="breakdown-track">
            <div class="breakdown-fill" data-tone="${scoreTone(score)}" data-width="${score}"></div>
          </div>
          <p class="breakdown-desc">${escapeHtml(data.description || "")}</p>
        </div>`;
    })
    .join("");

  requestAnimationFrame(() => {
    el.scoreBreakdown.querySelectorAll(".breakdown-fill").forEach((fill) => {
      fill.style.transform = `scaleX(${Number(fill.dataset.width) / 100})`;
    });
  });
}

function renderSkills(data) {
  const grouped = data.detected_skills_by_category || {};
  const names = Object.keys(grouped);
  el.skillCount.textContent = `${(data.detected_skills || []).length} across ${names.length} areas`;

  if (!names.length) {
    el.skillGroups.innerHTML =
      '<p class="empty-hint">No recognised skills. Add a Skills section naming the specific tools, systems, and methods you use.</p>';
  } else {
    el.skillGroups.innerHTML = names
      .map(
        (category) => `
        <div class="skill-group">
          <h4>${escapeHtml(category)}</h4>
          <div class="chips">${grouped[category]
            .map((skill) => `<span class="chip is-detected">${escapeHtml(skill)}</span>`)
            .join("")}</div>
        </div>`
      )
      .join("");
  }

  const disclaimed = data.disclaimed_skills || [];
  el.disclaimedBlock.hidden = disclaimed.length === 0;
  if (disclaimed.length) el.disclaimedList.textContent = disclaimed.join(", ");
}

function renderMatch(data) {
  const jd = data.job_description_analysis;
  if (!jd) {
    el.matchPanel.hidden = true;
    return;
  }
  el.matchPanel.hidden = false;

  const parts = [`Overall match ${jd.job_description_match_score}%.`];
  if (jd.skill_match_score !== null && jd.skill_match_score !== undefined) {
    parts.push(
      `You evidence ${(jd.matched_skills || []).length} of ${
        (jd.matched_skills || []).length + (jd.missing_skills || []).length
      } skills the posting names (${jd.skill_match_score}%).`
    );
  }
  parts.push(`Wording overlap is ${jd.wording_overlap_score}%, which counts for a quarter of the match.`);
  el.matchSummary.textContent = parts.join(" ");

  renderChips(el.matchedSkills, jd.matched_skills, "is-detected", "None yet");
  renderChips(el.missingSkillsList, jd.missing_skills, "is-missing", "Nothing missing");
  renderChips(el.missingKeywords, jd.missing_jd_keywords, "", "Nothing notable");
}

function renderAts(data) {
  const ats = data.ats_check || {};
  const checks = ats.checks || {};
  el.atsSummary.textContent = `${ats.passed_checks ?? 0} of ${ats.total_checks ?? 0} passed`;

  // Failures first: the reader is here to find what is broken.
  const ordered = Object.entries(checks).sort(([, a], [, b]) => Number(a) - Number(b));
  el.atsChecklist.innerHTML = ordered
    .map(
      ([key, passed]) => `
      <li class="check ${passed ? "pass" : "fail"}">
        <i class="fa-solid ${passed ? "fa-check" : "fa-xmark"}" aria-hidden="true"></i>
        <span>${escapeHtml(CHECK_LABELS[key] || titleCase(key))}</span>
      </li>`
    )
    .join("");
}

function renderStructure(data) {
  const structure = data.structure_analysis || {};
  const present = structure.present_sections || [];
  const missing = structure.missing_sections || [];
  el.structureSummary.textContent = `${present.length} of ${present.length + missing.length} present`;
  renderChips(el.presentSections, present.map(titleCase), "is-detected", "None detected");
  renderChips(el.missingSections, missing.map(titleCase), "is-missing", "All present");
}

function renderAi(data) {
  const ai = data.ai_insights;
  if (!ai) {
    el.aiPanel.hidden = true;
    return;
  }
  el.aiPanel.hidden = false;
  el.aiModel.textContent = ai.model ? `via ${ai.model}` : "";

  const blocks = [];
  if (ai.summary) {
    blocks.push(`<p class="muted" style="font-size:0.96rem">${escapeHtml(ai.summary)}</p>`);
  }
  if (ai.additional_skills?.length) {
    blocks.push(`
      <h4 style="margin-top:20px">Also spotted</h4>
      <div class="chips">${ai.additional_skills
        .map((skill) => `<span class="chip is-detected">${escapeHtml(skill)}</span>`)
        .join("")}</div>
      <p class="field-hint">Found by the language model, outside the fixed skill catalog.</p>`);
  }
  if (ai.overstated_claims?.length) {
    blocks.push(`
      <div class="callout is-warn" style="margin-top:20px">
        <strong>Claims without evidence:</strong>
        <ul class="list" style="margin-top:8px">${ai.overstated_claims
          .map((claim) => `<li>${escapeHtml(claim)}</li>`)
          .join("")}</ul>
      </div>`);
  }
  if (ai.rewrite_suggestions?.length) {
    blocks.push(`
      <h4 style="margin-top:22px">Suggested rewrites</h4>
      <div>${ai.rewrite_suggestions
        .map(
          (item) => `
          <div class="rewrite">
            <div class="rewrite-before"><span>Before</span><span>${escapeHtml(item.original)}</span></div>
            <div class="rewrite-after"><span>After</span><span>${escapeHtml(item.improved)}</span></div>
          </div>`
        )
        .join("")}</div>
      <p class="field-hint">Replace any [X%] placeholder with your real number before using these.</p>`);
  }

  el.aiBody.innerHTML = blocks.join("");
}

function render(data) {
  latestAnalysis = data;
  renderVerdict(data);
  renderActions(data);
  renderAi(data);
  renderMatch(data);
  renderBreakdown(data.score_breakdown);
  renderSkills(data);
  renderAts(data);
  renderStructure(data);
  showState("results");
  el.results.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---- requests ------------------------------------------------------------ */

async function analyze() {
  if (!selectedFile) {
    toast("Choose a resume file first.", true);
    el.dropZone?.focus();
    return;
  }

  const jobText = targetJobText();
  if (ROLE_REQUIRED && !jobText) {
    toast("Pick a target role or paste a job posting to match against.", true);
    el.targetDisclosure?.setAttribute("open", "");
    el.jobSelect?.focus();
    return;
  }

  const apiBase = getApiBase();
  const form = new FormData();
  form.append("resume", selectedFile);
  if (jobText) form.append("job_description", jobText);

  setBusy(true);
  showState("loading");

  try {
    const response = await fetch(`${apiBase}/api/analyze`, { method: "POST", body: form });
    if (!response.ok) {
      throw new Error(await describeApiError(response, "The analysis could not be completed."));
    }
    render(await response.json());
    toast("Analysis complete.");
  } catch (error) {
    // A TypeError from fetch means the request never reached a server at all.
    const message =
      error instanceof TypeError ? describeNetworkError(apiBase) : error.message;
    toast(message, true);
    showState(latestAnalysis ? "results" : "empty");
  } finally {
    setBusy(false);
  }
}

async function downloadReport() {
  if (!latestAnalysis) {
    toast("Run an analysis first.", true);
    return;
  }
  const apiBase = getApiBase();
  try {
    const response = await fetch(`${apiBase}/api/report/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(latestAnalysis),
    });
    if (!response.ok) {
      throw new Error(await describeApiError(response, "The report could not be generated."));
    }
    downloadBlob(await response.blob(), "resume-analysis-report.pdf");
    toast("Report downloaded.");
  } catch (error) {
    const message = error instanceof TypeError ? describeNetworkError(apiBase) : error.message;
    toast(message, true);
  }
}

/** Tell the user, up front, whether resume text will leave their machine. */
async function reportAiStatus() {
  if (!el.aiStatus) return;
  try {
    const response = await fetch(`${getApiBase()}/api/health`);
    if (!response.ok) throw new Error("unhealthy");
    const health = await response.json();
    const ai = health.ai_enrichment || {};
    el.aiStatus.textContent = ai.enabled
      ? `AI review is on, using ${ai.model} at ${ai.endpoint}. Up to ${ai.max_chars_sent} characters of your resume are sent there.`
      : "AI review is off. Everything runs locally on the rule-based engine. Set LLM_ENABLED=true in the backend to turn it on.";
  } catch {
    el.aiStatus.textContent = "API unreachable, so AI status is unknown.";
  }
}

/* ---- init ---------------------------------------------------------------- */

mountChrome();
initTheme();
mountApiSetting();

if (el.analyzeBtn) {
  el.analyzeBtn.dataset.label = el.analyzeBtn.querySelector("span")?.textContent.trim() || "Analyze resume";
  el.analyzeBtn.addEventListener("click", analyze);
}
el.reanalyzeBtn?.addEventListener("click", analyze);
el.downloadBtn?.addEventListener("click", downloadReport);
el.jobSelect?.addEventListener("change", onJobChange);

mountDropZone("dropZone", "resumeInput", (files) => setSelectedFile(files[0]));

/** Analyze text handed over from the Import page, with no file to upload. */
async function analyzePendingText(text) {
  const apiBase = getApiBase();
  setBusy(true);
  showState("loading");
  try {
    const response = await fetch(`${apiBase}/api/analyze/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_text: text, job_description: targetJobText() }),
    });
    if (!response.ok) {
      throw new Error(await describeApiError(response, "The analysis could not be completed."));
    }
    render(await response.json());
    toast("Scored the profile you imported.");
  } catch (error) {
    toast(error instanceof TypeError ? describeNetworkError(apiBase) : error.message, true);
    showState("empty");
  } finally {
    setBusy(false);
  }
}

showState("empty");
loadJobs();
reportAiStatus();

// The Import page can hand a parsed profile straight here. Consume it once so
// a refresh does not silently re-run the same analysis.
try {
  const pending = sessionStorage.getItem("sca.pendingResume");
  if (pending) {
    sessionStorage.removeItem("sca.pendingResume");
    analyzePendingText(pending);
  }
} catch {
  /* sessionStorage unavailable; the normal upload path still works */
}
