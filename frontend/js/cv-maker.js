/* ============================================================================
   CV Maker: guided form, live document preview, autosave, PDF export, and a
   round trip through the analyzer so you can score what you just wrote.
   ========================================================================= */

import {
  describeApiError,
  describeNetworkError,
  escapeHtml,
  getApiBase,
  initTheme,
  mountApiSetting,
  mountChrome,
  safeUrl,
  scoreBand,
  scoreTone,
  toast,
} from "./shared.js";

const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "sca.cv";
const TEMPLATE_KEY = "sca.cvTemplate";

const HEADER_FIELDS = ["fullName", "email", "phone", "location", "title", "linkedin", "github", "summary"];
const FIELD_KEY = "sca.cvField";

/* ---- worked examples per profession --------------------------------------
   The placeholders used to be software examples throughout, which quietly told
   every nurse, teacher and accountant that this tool was not built for them.
   Each entry is a real example of a strong line in that field.
------------------------------------------------------------------------- */
const FIELD_EXAMPLES = {
  general: {
    title: "Operations Manager",
    summary: "Operations manager with 8 years running teams of 20+. Cut process cycle time 31% in two years.",
    role: "Operations Manager",
    employer: "Northgate Group",
    bullets: [
      "One achievement per line.",
      "Cut order processing time 31%, from 9 days to 6.",
      "Trained 14 staff on the new system with zero downtime.",
    ],    skills: "Process Improvement, Budget Management, Leadership, Excel, Vendor Management",
    qualification: "BA Business Administration",
    institution: "University of Manchester",
  },
  healthcare: {
    title: "Registered Nurse",
    summary: "Registered nurse with 7 years in acute cardiac care. Improved unit throughput 22% while raising patient satisfaction.",
    role: "Senior Staff Nurse",
    employer: "St Mary's Hospital",
    bullets: [
      "One achievement per line.",
      "Led a 12-bed cardiac unit, improving throughput 22%.",
      "Trained 30 junior nurses in triage and emergency protocols.",
    ],    skills: "Patient Care, Triage, Clinical Documentation, Medication Administration, Electronic Health Records",
    qualification: "BSc Nursing",
    institution: "King's College London",
  },
  education: {
    title: "Secondary Teacher",
    summary: "Mathematics teacher with 9 years in the classroom. Raised GCSE pass rates from 61% to 84% across three cohorts.",
    role: "Head of Mathematics",
    employer: "Brookfield Academy",
    bullets: [
      "One achievement per line.",
      "Redesigned the KS4 curriculum, lifting pass rates 23 points.",
      "Led a department of 7 teachers across 600 students.",
    ],    skills: "Curriculum Development, Classroom Management, Assessment Design, Special Education",
    qualification: "PGCE Secondary Mathematics",
    institution: "University of Leeds",
  },
  finance: {
    title: "Chartered Accountant",
    summary: "Chartered accountant with 9 years in audit and reporting. Cut the month-end close from 12 days to 7.",
    role: "Audit Manager",
    employer: "Ledger and Co",
    bullets: [
      "One achievement per line.",
      "Led statutory audits for 18 clients with combined revenue over $400M.",
      "Reduced the close cycle from 12 days to 7 through process redesign.",
    ],    skills: "Financial Reporting, Auditing, IFRS, Excel, Taxation, Attention to Detail",
    qualification: "BSc Accounting, ACCA",
    institution: "University of Ghana",
  },
  hr: {
    title: "HR Manager",
    summary: "HR manager with 6 years across hiring and employee relations. Cut time-to-hire from 48 days to 29.",
    role: "HR Business Partner",
    employer: "Meridian Group",
    bullets: [
      "One achievement per line.",
      "Cut time-to-hire from 48 days to 29 across 40 roles.",
      "Ran the performance cycle for 300 employees.",
    ],    skills: "Recruiting, Employee Relations, Performance Management, Employment Law, HRIS",
    qualification: "CIPD Level 7",
    institution: "University of Birmingham",
  },
  sales: {
    title: "Account Executive",
    summary: "Enterprise account executive with 5 years in B2B software. Exceeded quota four years running.",
    role: "Senior Account Executive",
    employer: "Nimbus Software",
    bullets: [
      "One achievement per line.",
      "Closed $3.2M in new business, 118% of quota.",
      "Grew the territory from 12 to 47 active accounts.",
    ],    skills: "B2B Sales, CRM, Pipeline Management, Negotiation, Account Management",
    qualification: "BA Business Administration",
    institution: "IE University",
  },
  marketing: {
    title: "Marketing Manager",
    summary: "Growth marketer with 7 years in consumer subscription. Grew organic traffic 240% in 18 months.",
    role: "Senior Marketing Manager",
    employer: "Habitat",
    bullets: [
      "One achievement per line.",
      "Grew organic search traffic 240% through an SEO content programme.",
      "Ran campaigns on a 90M annual budget, lifting trial-to-paid 18%.",
    ],    skills: "SEO, Content Marketing, Campaign Management, Google Analytics, Marketing Automation",
    qualification: "BA Marketing",
    institution: "Waseda University",
  },
  creative: {
    title: "Product Designer",
    summary: "Product designer with 5 years shipping consumer apps. Lifted activation 19% through onboarding redesign.",
    role: "Senior Product Designer",
    employer: "Klar",
    bullets: [
      "One achievement per line.",
      "Designed and shipped 14 features, lifting activation 19%.",
      "Ran usability testing with 60+ participants.",
    ],    skills: "Figma, User Research, Prototyping, Design Systems, Usability Testing",
    qualification: "BA Communication Design",
    institution: "HfG Karlsruhe",
  },
  trades: {
    title: "Site Supervisor",
    summary: "Site supervisor with 11 years in commercial fit-out. Delivered 30 projects with zero reportable incidents.",
    role: "Site Supervisor",
    employer: "Kelvin Construction",
    bullets: [
      "One achievement per line.",
      "Delivered 30 projects on schedule with zero reportable incidents.",
      "Supervised crews of up to 18 across three concurrent sites.",
    ],    skills: "Health and Safety, Quality Control, Leadership, Project Management, Manufacturing",
    qualification: "NVQ Level 3 Construction",
    institution: "Leeds City College",
  },
  technology: {
    title: "Backend Engineer",
    summary: "Backend engineer with 4 years building high-throughput services. Cut p95 latency 38% across 12 microservices.",
    role: "Backend Engineer",
    employer: "Systems Ltd",
    bullets: [
      "One achievement per line.",
      "Built 12 microservices in Python, cutting p95 latency 38%.",
      "Automated releases, taking deploys from 45 minutes to 6.",
    ],    skills: "Python, Django, PostgreSQL, Docker, Kubernetes, AWS",
    qualification: "BS Computer Science",
    institution: "Punjab University",
  },
};

let fieldExample = FIELD_EXAMPLES.general;

let template = "modern";
let saveTimer = null;

/* ---- entry definitions ---------------------------------------------------
   One description per repeatable section keeps the markup, the reader, and
   the collector in step: adding a field means editing one array.
-------------------------------------------------------------------------- */
const SECTIONS = {
  experience: {
    listId: "experienceList",
    label: "Role",
    fields: [
      { key: "title", label: "Job title", placeholder: fieldExample.role, half: true },
      { key: "company", label: "Employer", placeholder: fieldExample.employer, half: true },
      { key: "start", label: "Start", placeholder: "Jan 2021", half: true },
      { key: "end", label: "End", placeholder: "Present", half: true },
      {
        key: "description",
        label: "What you did",
        type: "textarea",
        rows: 4,
        // Replaced by applyField() at startup with an example from the
        // reader's own field; this is only the pre-init default.
        placeholder: FIELD_EXAMPLES.general.bullets.join("\n"),
        hint: "One line per bullet. Start with a verb, end with a number.",
      },
    ],
  },
  education: {
    listId: "educationList",
    label: "Qualification",
    fields: [
      { key: "degree", label: "Qualification", placeholder: fieldExample.qualification, half: true },
      { key: "school", label: "Institution", placeholder: fieldExample.institution, half: true },
      { key: "field", label: "Subject", placeholder: "", half: true },
      { key: "year", label: "Year", placeholder: "2020", half: true },
    ],
  },
  projects: {
    listId: "projectsList",
    label: "Project",
    fields: [
      { key: "name", label: "Project name", placeholder: "Resume Analyzer", half: true },
      { key: "link", label: "Link", placeholder: "github.com/…", half: true },
      {
        key: "description",
        label: "What it does and what you built",
        type: "textarea",
        rows: 3,
        placeholder: "One line per bullet.",
      },
    ],
  },
};

/* ---- entry markup -------------------------------------------------------- */

function entryMarkup(section, data = {}) {
  const config = SECTIONS[section];
  let html = "";
  let index = 0;

  while (index < config.fields.length) {
    const field = config.fields[index];
    const next = config.fields[index + 1];

    if (field.half && next?.half) {
      html += `<div class="form-row">${fieldMarkup(field, data)}${fieldMarkup(next, data)}</div>`;
      index += 2;
    } else {
      html += fieldMarkup(field, data);
      index += 1;
    }
  }

  return `
    <div class="entry" data-entry="${section}">
      <div class="entry-head">
        <h4>${escapeHtml(config.label)}</h4>
        <button class="entry-remove" type="button" data-remove aria-label="Remove this ${config.label.toLowerCase()}">
          <i class="fa-solid fa-trash-can" aria-hidden="true"></i> Remove
        </button>
      </div>
      ${html}
    </div>`;
}

function fieldMarkup(field, data) {
  const value = data[field.key] || "";
  const hint = field.hint ? `<p class="field-hint">${escapeHtml(field.hint)}</p>` : "";
  const control =
    field.type === "textarea"
      ? `<textarea rows="${field.rows || 3}" data-key="${field.key}" placeholder="${escapeHtml(
          field.placeholder || ""
        )}">${escapeHtml(value)}</textarea>`
      : `<input type="text" data-key="${field.key}" value="${escapeHtml(value)}" placeholder="${escapeHtml(
          field.placeholder || ""
        )}" />`;

  return `<div class="field"><label>${escapeHtml(field.label)}</label>${control}${hint}</div>`;
}

function addEntry(section, data = {}, silent = false) {
  const list = $(SECTIONS[section].listId);
  list.insertAdjacentHTML("beforeend", entryMarkup(section, data));
  if (!silent) {
    list.lastElementChild.querySelector("input, textarea")?.focus();
    refresh();
  }
}

/* ---- reading the form ---------------------------------------------------- */

function readEntries(section) {
  return Array.from($(SECTIONS[section].listId).querySelectorAll(".entry")).map((entry) => {
    const record = {};
    entry.querySelectorAll("[data-key]").forEach((input) => {
      record[input.dataset.key] = input.value.trim();
    });
    return record;
  });
}

function readForm() {
  const data = {};
  HEADER_FIELDS.forEach((key) => {
    data[key] = $(key).value.trim();
  });
  data.skills = $("skillsInput")
    .value.split(",")
    .map((skill) => skill.trim())
    .filter(Boolean);
  data.experience = readEntries("experience");
  data.education = readEntries("education");
  data.projects = readEntries("projects");
  return data;
}

/* ---- preview rendering --------------------------------------------------- */

function bulletsMarkup(text) {
  const lines = (text || "")
    .split(/\n+/)
    .map((line) => line.replace(/^[-*•·]\s*/, "").trim())
    .filter(Boolean);
  if (!lines.length) return "";
  if (lines.length === 1) return `<p>${escapeHtml(lines[0])}</p>`;
  return `<ul>${lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
}

function renderPreview(data) {
  $("pvName").textContent = data.fullName || "Your name";
  $("pvTitle").textContent = data.title || "";
  $("pvTitle").hidden = !data.title;

  const contact = [];
  if (data.email) contact.push(`<span>${escapeHtml(data.email)}</span>`);
  if (data.phone) contact.push(`<span>${escapeHtml(data.phone)}</span>`);
  if (data.location) contact.push(`<span>${escapeHtml(data.location)}</span>`);
  const linkedin = safeUrl(data.linkedin);
  if (linkedin) contact.push(`<span><a href="${linkedin}" target="_blank" rel="noopener noreferrer">LinkedIn</a></span>`);
  const github = safeUrl(data.github);
  if (github) contact.push(`<span><a href="${github}" target="_blank" rel="noopener noreferrer">Portfolio</a></span>`);
  $("pvContact").innerHTML = contact.join("");

  // summary
  $("pvSummary").textContent = data.summary;
  $("pvSummarySection").hidden = !data.summary;

  // experience
  const experience = data.experience.filter((item) => item.title || item.company);
  $("pvExp").innerHTML = experience
    .map((item) => {
      const dates = [item.start, item.end].filter(Boolean).join(" – ");
      return `
        <div class="cv-item">
          <div class="cv-item-head">
            <h4>${escapeHtml(item.title || "Role")}</h4>
            ${dates ? `<span class="cv-date">${escapeHtml(dates)}</span>` : ""}
          </div>
          ${item.company ? `<div class="cv-org">${escapeHtml(item.company)}</div>` : ""}
          ${bulletsMarkup(item.description)}
        </div>`;
    })
    .join("");
  $("pvExpSection").hidden = experience.length === 0;

  // education
  const education = data.education.filter((item) => item.degree || item.school);
  $("pvEdu").innerHTML = education
    .map(
      (item) => `
      <div class="cv-item">
        <div class="cv-item-head">
          <h4>${escapeHtml(item.degree || "Qualification")}${
        item.field ? `, ${escapeHtml(item.field)}` : ""
      }</h4>
          ${item.year ? `<span class="cv-date">${escapeHtml(item.year)}</span>` : ""}
        </div>
        ${item.school ? `<div class="cv-org">${escapeHtml(item.school)}</div>` : ""}
      </div>`
    )
    .join("");
  $("pvEduSection").hidden = education.length === 0;

  // projects
  const projects = data.projects.filter((item) => item.name);
  $("pvProj").innerHTML = projects
    .map((item) => {
      const link = safeUrl(item.link);
      return `
        <div class="cv-item">
          <div class="cv-item-head">
            <h4>${escapeHtml(item.name)}</h4>
            ${link ? `<span class="cv-date"><a href="${link}" target="_blank" rel="noopener noreferrer">Link</a></span>` : ""}
          </div>
          ${bulletsMarkup(item.description)}
        </div>`;
    })
    .join("");
  $("pvProjSection").hidden = projects.length === 0;

  // skills
  $("pvSkills").textContent = data.skills.join(" · ");
  $("pvSkillsSection").hidden = data.skills.length === 0;

  const anyContent =
    data.summary || experience.length || education.length || projects.length || data.skills.length;
  $("pvEmpty").hidden = Boolean(anyContent);

  // counts and length guidance
  document.querySelector('[data-count="experience"]').textContent = data.experience.length;
  document.querySelector('[data-count="education"]').textContent = data.education.length;
  document.querySelector('[data-count="projects"]').textContent = data.projects.length;
  document.querySelector('[data-count="skills"]').textContent = data.skills.length;

  $("skillsPreview").innerHTML = data.skills.length
    ? data.skills.map((skill) => `<span class="chip is-detected">${escapeHtml(skill)}</span>`).join("")
    : '<span class="chip is-empty">No skills added yet</span>';

  const words = plainText(data).split(/\s+/).filter(Boolean).length;
  const hint = $("lengthHint");
  if (!words) {
    hint.textContent = "";
  } else if (words < 140) {
    hint.textContent = `${words} words · too thin, aim for 400–800`;
  } else if (words > 900) {
    hint.textContent = `${words} words · getting long, aim for 400–800`;
  } else {
    hint.textContent = `${words} words · good length`;
  }
}

/* ---- plain text (for scoring) -------------------------------------------- */

function plainText(data) {
  const lines = [data.fullName, data.title];
  lines.push([data.email, data.phone, data.location].filter(Boolean).join(" | "));
  if (data.summary) lines.push("", "SUMMARY", data.summary);

  if (data.experience.some((item) => item.title || item.company)) {
    lines.push("", "EXPERIENCE");
    data.experience.forEach((item) => {
      if (!item.title && !item.company) return;
      const dates = [item.start, item.end].filter(Boolean).join(" - ");
      lines.push(`${item.title || ""}, ${item.company || ""}${dates ? ` (${dates})` : ""}`);
      (item.description || "")
        .split(/\n+/)
        .map((line) => line.replace(/^[-*•·]\s*/, "").trim())
        .filter(Boolean)
        .forEach((line) => lines.push(`- ${line}`));
    });
  }

  if (data.education.some((item) => item.degree || item.school)) {
    lines.push("", "EDUCATION");
    data.education.forEach((item) => {
      if (!item.degree && !item.school) return;
      lines.push(
        [item.degree, item.field, item.school, item.year].filter(Boolean).join(", ")
      );
    });
  }

  if (data.projects.some((item) => item.name)) {
    lines.push("", "PROJECTS");
    data.projects.forEach((item) => {
      if (!item.name) return;
      lines.push(item.name);
      (item.description || "")
        .split(/\n+/)
        .map((line) => line.replace(/^[-*•·]\s*/, "").trim())
        .filter(Boolean)
        .forEach((line) => lines.push(`- ${line}`));
    });
  }

  if (data.skills.length) lines.push("", "SKILLS", data.skills.join(", "));
  return lines.filter((line) => line !== undefined && line !== null).join("\n");
}

/* ---- persistence --------------------------------------------------------- */

function save(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    const state = $("saveState");
    state.innerHTML = '<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Saved';
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      state.textContent = "";
    }, 1800);
  } catch {
    $("saveState").textContent = "Not saved — browser storage unavailable";
  }
}

function restore() {
  let data;
  try {
    data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  } catch {
    data = null;
  }
  if (!data) return false;

  HEADER_FIELDS.forEach((key) => {
    if (typeof data[key] === "string") $(key).value = data[key];
  });
  if (Array.isArray(data.skills)) $("skillsInput").value = data.skills.join(", ");
  ["experience", "education", "projects"].forEach((section) => {
    (data[section] || []).forEach((entry) => addEntry(section, entry, true));
  });
  return true;
}

/* ---- refresh loop -------------------------------------------------------- */

let refreshQueued = false;

function refresh() {
  if (refreshQueued) return;
  refreshQueued = true;
  requestAnimationFrame(() => {
    refreshQueued = false;
    const data = readForm();
    renderPreview(data);
    save(data);
  });
}

/* ---- tabs ---------------------------------------------------------------- */

function selectTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.tab === name));
  });
  document.querySelectorAll(".tabpanel").forEach((panel) => {
    panel.hidden = panel.dataset.panel !== name;
  });
}

/* ---- templates ----------------------------------------------------------- */

/** Repoint every visible placeholder at the chosen profession's examples. */
function applyField(name) {
  fieldExample = FIELD_EXAMPLES[name] || FIELD_EXAMPLES.general;
  try {
    localStorage.setItem(FIELD_KEY, name);
  } catch {
    /* preference simply will not persist */
  }

  document.querySelectorAll("[data-field-select]").forEach((select) => {
    select.value = name;
  });

  const map = {
    title: fieldExample.title,
    summary: fieldExample.summary,
    skillsInput: fieldExample.skills,
  };
  Object.entries(map).forEach(([id, placeholder]) => {
    const input = $(id);
    if (input) input.placeholder = placeholder;
  });

  // Repoint the repeatable entries already on the page.
  SECTIONS.experience.fields[0].placeholder = fieldExample.role;
  SECTIONS.experience.fields[1].placeholder = fieldExample.employer;
  SECTIONS.experience.fields[4].placeholder = fieldExample.bullets.join("\n");
  SECTIONS.education.fields[0].placeholder = fieldExample.qualification;
  SECTIONS.education.fields[1].placeholder = fieldExample.institution;

  document.querySelectorAll("#experienceList .entry").forEach((entry) => {
    const title = entry.querySelector('[data-key="title"]');
    const company = entry.querySelector('[data-key="company"]');
    const description = entry.querySelector('[data-key="description"]');
    if (title) title.placeholder = fieldExample.role;
    if (company) company.placeholder = fieldExample.employer;
    if (description) description.placeholder = fieldExample.bullets.join("\n");
  });
  document.querySelectorAll("#educationList .entry").forEach((entry) => {
    const degree = entry.querySelector('[data-key="degree"]');
    const school = entry.querySelector('[data-key="school"]');
    if (degree) degree.placeholder = fieldExample.qualification;
    if (school) school.placeholder = fieldExample.institution;
  });
}


function applyTemplate(name) {
  template = name;
  const doc = $("cvDoc");
  doc.className = `cv-doc tpl-${name}`;
  document.querySelectorAll(".template-option").forEach((option) => {
    option.setAttribute("aria-pressed", String(option.dataset.template === name));
  });
  try {
    localStorage.setItem(TEMPLATE_KEY, name);
  } catch {
    /* preference simply will not persist */
  }
}

/* ---- PDF export ---------------------------------------------------------- */

function exportPdf() {
  const data = readForm();
  const missing = [];
  if (!data.fullName) missing.push("name");
  if (!data.email) missing.push("email");
  if (missing.length) {
    toast(`Add your ${missing.join(" and ")} before exporting.`, true);
    selectTab("personal");
    $(missing[0] === "name" ? "fullName" : "email").focus();
    return;
  }

  const printWindow = window.open("", "_blank", "width=900,height=1000");
  if (!printWindow) {
    toast("Your browser blocked the print window. Allow pop-ups for this page and try again.", true);
    return;
  }

  // Inline the two stylesheets the document actually needs, so the print view
  // matches the preview without depending on the opener staying alive.
  const styles = Array.from(document.styleSheets)
    .filter((sheet) => sheet.href?.includes("cv-maker.css") || sheet.href?.includes("styles.css"))
    .map((sheet) => {
      try {
        return Array.from(sheet.cssRules).map((rule) => rule.cssText).join("\n");
      } catch {
        return "";
      }
    })
    .join("\n");

  printWindow.document.write(`<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>${escapeHtml(data.fullName)} — CV</title>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&family=Schibsted+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
${styles}
:root { color-scheme: light; }
body { margin: 0; background: #fff; }
.cv-doc { box-shadow: none; border-radius: 0; max-width: 190mm; margin: 0 auto; padding: 14mm 16mm; }
@page { size: A4; margin: 0; }
</style>
</head><body>${$("cvDoc").outerHTML}</body></html>`);
  printWindow.document.close();

  // Give the new document a moment to lay out and load fonts before opening
  // the print dialog; whichever of load or timeout fires first wins.
  let printed = false;
  const printOnce = () => {
    if (printed) return;
    printed = true;
    try {
      printWindow.focus();
      printWindow.print();
    } catch {
      /* the user closed the window first */
    }
  };
  printWindow.onload = printOnce;
  setTimeout(printOnce, 700);
  toast("Print dialog opening. Choose “Save as PDF” as the destination.");
}

/* ---- score this CV ------------------------------------------------------- */

async function scoreCv() {
  const data = readForm();
  const text = plainText(data);
  if (text.split(/\s+/).filter(Boolean).length < 25) {
    toast("Add more content before scoring — there is not enough to assess yet.", true);
    return;
  }

  const button = $("analyzeCvBtn");
  const apiBase = getApiBase();
  button.disabled = true;

  try {
    const response = await fetch(`${apiBase}/api/analyze/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_text: text,
        job_description: ($("jobDescriptionTarget").value || "").trim(),
      }),
    });
    if (!response.ok) throw new Error(await describeApiError(response, "Scoring failed."));

    const result = await response.json();
    const score = result.resume_score;
    const actions = result.feedback?.priority_actions || [];

    $("scoreHeadline").textContent = `${score}/100 · ${scoreBand(score)}`;
    $("scoreBody").innerHTML = `
      <div class="breakdown-track" style="margin-bottom:18px">
        <div class="breakdown-fill" data-tone="${scoreTone(score)}" style="transform:scaleX(${score / 100})"></div>
      </div>
      <p class="muted">${escapeHtml(result.feedback?.verdict || "")}</p>
      ${
        actions.length
          ? `<h4 style="margin-top:20px">Fix these first</h4>
             <ol class="actions">${actions
               .slice(0, 5)
               .map(
                 (action) => `
                 <li class="action">
                   <span class="action-title">${escapeHtml(action.title)}</span>
                   <p class="action-detail">${escapeHtml(action.detail)}</p>
                   <span class="action-meta">
                     ${
                       action.impact_points
                         ? `<span class="action-impact">+${action.impact_points}</span>`
                         : '<span class="action-impact is-zero">Worth doing</span>'
                     }
                     <span class="action-effort">${escapeHtml(action.effort || "")}</span>
                   </span>
                 </li>`
               )
               .join("")}</ol>`
          : '<p class="muted">Nothing left to fix. This CV passes every check.</p>'
      }`;
    $("scorePanel").hidden = false;
    $("scorePanel").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    toast(error instanceof TypeError ? describeNetworkError(apiBase) : error.message, true);
  } finally {
    button.disabled = false;
  }
}

/* ---- tailor to a job ----------------------------------------------------- */

async function checkAgainstJob() {
  const jd = ($("jobDescriptionTarget").value || "").trim();
  if (!jd) {
    toast("Paste the job description first.", true);
    $("jobDescriptionTarget").focus();
    return;
  }

  const data = readForm();
  const button = $("rewriteBtn");
  const label = button.querySelector("span");
  const apiBase = getApiBase();

  button.disabled = true;
  label.textContent = "Checking…";

  try {
    const response = await fetch(`${apiBase}/api/rewrite-cv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        summary: data.summary,
        experience: data.experience,
        job_description: jd,
      }),
    });
    if (!response.ok) throw new Error(await describeApiError(response, "The check failed."));

    const result = await response.json();
    const blocks = [];

    if (result.missing_skills?.length) {
      blocks.push(`
        <h4 style="margin-top:18px">This job asks for, and your CV does not evidence</h4>
        <div class="chips">${result.missing_skills
          .map((skill) => `<span class="chip is-missing">${escapeHtml(skill)}</span>`)
          .join("")}</div>`);
    } else {
      blocks.push(
        '<div class="callout is-info" style="margin-top:18px">Your CV already evidences every skill this posting names.</div>'
      );
    }

    if (result.rewrite_suggestions?.length) {
      blocks.push(`
        <h4 style="margin-top:20px">Suggested rewrites</h4>
        ${result.rewrite_suggestions
          .map(
            (item) => `
            <div class="rewrite">
              <div class="rewrite-before"><span>Before</span><span>${escapeHtml(item.original)}</span></div>
              <div class="rewrite-after"><span>After</span><span>${escapeHtml(item.improved)}</span></div>
            </div>`
          )
          .join("")}`);
    }

    if (result.suggestions?.length) {
      blocks.push(`
        <h4 style="margin-top:20px">What to change</h4>
        <ul class="list">${result.suggestions.map((tip) => `<li>${escapeHtml(tip)}</li>`).join("")}</ul>`);
    }

    if (result.note) {
      blocks.push(`<p class="field-hint" style="margin-top:14px">${escapeHtml(result.note)}</p>`);
    }

    $("rewriteOutput").innerHTML = blocks.join("");
    toast("Checked against the posting.");
  } catch (error) {
    toast(error instanceof TypeError ? describeNetworkError(apiBase) : error.message, true);
  } finally {
    button.disabled = false;
    label.textContent = "Check against this job";
  }
}

/* ---- init ---------------------------------------------------------------- */

mountChrome();
initTheme();
mountApiSetting();

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => selectTab(tab.dataset.tab));
});

document.querySelectorAll(".template-option").forEach((option) => {
  option.addEventListener("click", () => applyTemplate(option.dataset.template));
});

document.querySelectorAll("[data-field-select]").forEach((select) => {
  select.addEventListener("change", () => applyField(select.value));
});

$("addExperience").addEventListener("click", () => addEntry("experience"));
$("addEducation").addEventListener("click", () => addEntry("education"));
$("addProject").addEventListener("click", () => addEntry("projects"));

// One delegated listener covers every field, including ones added later.
document.querySelector(".builder-form").addEventListener("input", (event) => {
  if (event.target.matches("input, textarea")) refresh();
});

document.querySelector(".builder-form").addEventListener("click", (event) => {
  const remove = event.target.closest("[data-remove]");
  if (!remove) return;
  remove.closest(".entry").remove();
  refresh();
});

$("downloadCvBtn").addEventListener("click", exportPdf);
$("analyzeCvBtn").addEventListener("click", scoreCv);
$("clearCvBtn").addEventListener("click", () => {
  if (!window.confirm("Clear everything and start over? This cannot be undone.")) return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* nothing to clear */
  }
  window.location.reload();
});

try {
  const saved = localStorage.getItem(TEMPLATE_KEY);
  if (saved) applyTemplate(saved);
} catch {
  /* keep the default template */
}

try {
  applyField(localStorage.getItem(FIELD_KEY) || "general");
} catch {
  applyField("general");
}

const hadSavedWork = restore();
if (!hadSavedWork) {
  // Start with one of each so the form is never a wall of empty buttons.
  addEntry("experience", {}, true);
  addEntry("education", {}, true);
}
refresh();
if (hadSavedWork) toast("Restored your saved CV.");
