/* ============================================================================
   Import: LinkedIn export or existing CV -> filled CV Maker.
   ========================================================================= */

import {
  describeApiError,
  describeNetworkError,
  escapeHtml,
  formatBytes,
  getApiBase,
  initTheme,
  mountChrome,
  mountDropZone,
  toast,
  validateFile,
} from "./shared.js";

const $ = (id) => document.getElementById(id);
const CV_STORAGE_KEY = "sca.cv";

const el = {
  fileLine: $("fileLine"),
  pasteBox: $("pasteBox"),
  importBtn: $("importBtn"),
  urlHelp: $("urlHelp"),
  loadingState: $("loadingState"),
  results: $("results"),
  sourceLabel: $("sourceLabel"),
  warnings: $("warnings"),
  foundFields: $("foundFields"),
  skillsPanel: $("skillsPanel"),
  skillGroups: $("skillGroups"),
  skillCount: $("skillCount"),
};

let selectedFile = null;
let parsed = null;

const LINKEDIN_URL_ONLY = /^(?:https?:\/\/)?(?:[a-z]{2,3}\.)?linkedin\.com\/\S*$/i;

/* ---- file selection ------------------------------------------------------ */

function setFile(file) {
  const error = validateFile(file);
  const icon = el.fileLine.querySelector("i");
  const text = el.fileLine.querySelector("span");

  if (error) {
    selectedFile = null;
    el.fileLine.classList.remove("has-file");
    icon.className = "fa-regular fa-circle";
    text.textContent = "No file chosen yet";
    toast(error, true);
    return;
  }

  selectedFile = file;
  el.fileLine.classList.add("has-file");
  icon.className = "fa-solid fa-circle-check";
  text.textContent = `${file.name} · ${formatBytes(file.size)}`;

  if (!el.fileLine.querySelector(".clear")) {
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "clear";
    clear.textContent = "Remove";
    clear.addEventListener("click", () => {
      selectedFile = null;
      el.fileLine.classList.remove("has-file");
      icon.className = "fa-regular fa-circle";
      text.textContent = "No file chosen yet";
      clear.remove();
    });
    el.fileLine.appendChild(clear);
  }
  // A chosen file wins over stale pasted text.
  el.urlHelp.hidden = true;
}

/* ---- view state ---------------------------------------------------------- */

function showLoading(isLoading) {
  el.loadingState.hidden = !isLoading;
  el.importBtn.disabled = isLoading;
  const label = el.importBtn.querySelector("span");
  if (label) label.textContent = isLoading ? "Reading…" : "Build my CV";
}

/* ---- rendering ----------------------------------------------------------- */

function row(label, value) {
  const empty = !value || (Array.isArray(value) && value.length === 0);
  const body = empty
    ? '<dd class="is-empty">not found</dd>'
    : `<dd>${value}</dd>`;
  return `<div class="found-row"><dt>${escapeHtml(label)}</dt>${body}</div>`;
}

function renderFound(data) {
  const p = data.profile;

  const contact = [p.email, p.phone, p.location].filter(Boolean).map(escapeHtml).join(" · ");

  const experience = (p.experience || [])
    .map(
      (item) => `
      <div class="found-entry">
        <strong>${escapeHtml(item.title || "Role")}</strong>
        <span>${escapeHtml(item.company || "")}</span>
        <span class="when">${escapeHtml([item.start, item.end].filter(Boolean).join(" – "))}</span>
      </div>`
    )
    .join("");

  const education = (p.education || [])
    .map(
      (item) => `
      <div class="found-entry">
        <strong>${escapeHtml([item.degree, item.field].filter(Boolean).join(", ") || "Qualification")}</strong>
        <span>${escapeHtml(item.school || "")}</span>
        <span class="when">${escapeHtml(item.year || "")}</span>
      </div>`
    )
    .join("");

  const skills = (p.skills || [])
    .slice(0, 30)
    .map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`)
    .join("");

  el.foundFields.innerHTML = [
    row("Name", p.fullName ? escapeHtml(p.fullName) : ""),
    row("Headline", p.title ? escapeHtml(p.title) : ""),
    row("Contact", contact),
    row("Summary", p.summary ? escapeHtml(p.summary.slice(0, 260)) + (p.summary.length > 260 ? "…" : "") : ""),
    row("Experience", experience),
    row("Education", education),
    row("Skills listed", skills ? `<div class="chips">${skills}</div>` : ""),
    row(
      "Certifications",
      (p.certifications || []).length
        ? `<div class="chips">${p.certifications.map((c) => `<span class="chip">${escapeHtml(c)}</span>`).join("")}</div>`
        : ""
    ),
  ].join("");

  el.sourceLabel.textContent =
    data.source === "linkedin" ? "from your LinkedIn export" : "from your CV";

  el.warnings.innerHTML = (data.warnings || []).length
    ? `<div class="callout is-warn" style="margin-bottom:16px">
         <strong>Could not find everything:</strong>
         <ul class="list" style="margin-top:8px">
           ${data.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}
         </ul>
       </div>`
    : "";

  const grouped = data.recognised_skills_by_category || {};
  const categories = Object.keys(grouped);
  if (categories.length) {
    el.skillsPanel.hidden = false;
    el.skillCount.textContent = `${(data.recognised_skills || []).length} across ${categories.length} areas`;
    el.skillGroups.innerHTML = categories
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
  } else {
    el.skillsPanel.hidden = true;
  }

  el.results.hidden = false;
  el.results.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---- import -------------------------------------------------------------- */

async function runImport() {
  const pasted = (el.pasteBox.value || "").trim();

  if (!selectedFile && !pasted) {
    toast("Drop a file, or paste your profile text.", true);
    return;
  }

  // A bare profile link is the one input that cannot work. Explain in place
  // rather than firing an error toast the reader has to decode.
  if (!selectedFile && LINKEDIN_URL_ONLY.test(pasted)) {
    el.urlHelp.hidden = false;
    el.urlHelp.scrollIntoView({ behavior: "smooth", block: "center" });
    toast("A profile link on its own cannot be read. See the steps below.", true);
    return;
  }

  const apiBase = getApiBase();
  showLoading(true);
  el.results.hidden = true;

  try {
    let response;
    if (selectedFile) {
      const form = new FormData();
      form.append("profile", selectedFile);
      response = await fetch(`${apiBase}/api/import/profile`, { method: "POST", body: form });
    } else {
      response = await fetch(`${apiBase}/api/import/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: pasted }),
      });
    }

    if (!response.ok) {
      // The URL case answers with instructions, not just a message.
      const data = await response.json().catch(() => ({}));
      if (data.how_to_fix) {
        el.urlHelp.hidden = false;
        el.urlHelp.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      throw new Error(data.error || (await describeApiError(response, "The import failed.")));
    }

    parsed = await response.json();
    el.urlHelp.hidden = true;
    renderFound(parsed);

    const found = parsed.fields_found;
    toast(
      found >= 5
        ? "Imported. Check it over, then open it in the CV Maker."
        : `Imported ${found} of 6 sections. Fill the rest in the CV Maker.`,
      found < 3
    );
  } catch (error) {
    toast(error instanceof TypeError ? describeNetworkError(apiBase) : error.message, true);
  } finally {
    showLoading(false);
  }
}

/* ---- handoff to the CV Maker --------------------------------------------- */

/** Reshape the parsed profile into exactly what the CV Maker restores. */
function toCvMakerShape(profile) {
  return {
    fullName: profile.fullName || "",
    email: profile.email || "",
    phone: profile.phone || "",
    location: profile.location || "",
    title: profile.title || "",
    linkedin: profile.linkedin || "",
    github: profile.github || "",
    summary: profile.summary || "",
    skills: profile.skills || [],
    experience: (profile.experience || []).map((item) => ({
      title: item.title || "",
      company: item.company || "",
      start: item.start || "",
      end: item.end || "",
      description: item.description || "",
    })),
    education: (profile.education || []).map((item) => ({
      degree: item.degree || "",
      school: item.school || "",
      field: item.field || "",
      year: item.year || "",
    })),
    projects: [],
  };
}

function openInMaker() {
  if (!parsed) return;
  try {
    const existing = localStorage.getItem(CV_STORAGE_KEY);
    if (existing && existing !== "null") {
      const proceed = window.confirm(
        "You already have a CV saved in the CV Maker. Replace it with this import?"
      );
      if (!proceed) return;
    }
    localStorage.setItem(CV_STORAGE_KEY, JSON.stringify(toCvMakerShape(parsed.profile)));
  } catch {
    toast("Could not save to this browser. Try a normal (non-private) window.", true);
    return;
  }
  window.location.href = "./cv-maker.html";
}

async function scoreIt() {
  if (!parsed) return;
  const apiBase = getApiBase();
  const profile = parsed.profile;

  // Rebuild a plain-text CV so the analyzer sees section headings.
  const lines = [profile.fullName, profile.title];
  lines.push([profile.email, profile.phone, profile.location].filter(Boolean).join(" | "));
  if (profile.summary) lines.push("", "SUMMARY", profile.summary);
  if (profile.experience?.length) {
    lines.push("", "EXPERIENCE");
    profile.experience.forEach((item) => {
      lines.push(`${item.title}, ${item.company} (${item.start} - ${item.end})`);
      (item.description || "").split("\n").filter(Boolean).forEach((d) => lines.push(`- ${d}`));
    });
  }
  if (profile.education?.length) {
    lines.push("", "EDUCATION");
    profile.education.forEach((item) =>
      lines.push([item.degree, item.field, item.school, item.year].filter(Boolean).join(", "))
    );
  }
  if (profile.certifications?.length) lines.push("", "CERTIFICATIONS", ...profile.certifications);
  if (profile.skills?.length) lines.push("", "SKILLS", profile.skills.join(", "));

  try {
    sessionStorage.setItem("sca.pendingResume", lines.filter(Boolean).join("\n"));
    window.location.href = "./analyzer.html?from=import";
  } catch {
    toast("Could not hand this to the analyzer. Open it in the CV Maker instead.", true);
  }
}

/* ---- init ---------------------------------------------------------------- */

mountChrome();
initTheme();
mountDropZone("dropZone", "fileInput", (files) => setFile(files[0]));

el.importBtn.addEventListener("click", runImport);
$("openInMakerBtn").addEventListener("click", openInMaker);
$("scoreItBtn").addEventListener("click", scoreIt);

// Recognise a pasted profile link as it is typed, before the button is pressed.
el.pasteBox.addEventListener("input", () => {
  const value = el.pasteBox.value.trim();
  el.urlHelp.hidden = !(value && LINKEDIN_URL_ONLY.test(value));
});
