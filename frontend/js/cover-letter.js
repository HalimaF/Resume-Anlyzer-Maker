/* ============================================================================
   Cover Letter: the letter is rebuilt from the form on every keystroke.

   Wording is chosen deterministically from the inputs rather than at random.
   The old version picked an opening with Math.random(), so the same form
   produced a different letter each time it regenerated - which reads as a bug
   to anyone who notices, and makes the output impossible to iterate on.
   ========================================================================= */

import { escapeHtml, initTheme, mountChrome, safeUrl, toast } from "./shared.js";

const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "sca.letter";

const FIELDS = [
  "fullName",
  "email",
  "phone",
  "linkedIn",
  "website",
  "jobTitle",
  "companyName",
  "hireManagerName",
  "jobDescription",
  "resumeHighlights",
  "whyCompany",
];

let tone = "professional";
let layout = "modern";
let saveTimer = null;

/* ---- copy ----------------------------------------------------------------
   Two openings per tone. Which one is used depends on whether the writer
   supplied a reason for wanting this company - a real signal, not a coin flip.
-------------------------------------------------------------------------- */
const COPY = {
  professional: {
    opening: (role, company) =>
      `I am writing to apply for the ${role} position at ${company}. My background maps closely to what the role requires, and I believe I can contribute from early on.`,
    openingWithReason: (role, company) =>
      `I am writing to apply for the ${role} position at ${company}. It is a role I have been watching for, and my background maps closely to what it requires.`,
    bodyLead: "Across my career I have focused on work that can be measured.",
    bodyLeadNoHighlights: (role) =>
      `My experience covers the core responsibilities of this ${role} role, and I am comfortable taking ownership of them from the start.`,
    closing: (company) =>
      `I would welcome the chance to discuss how my experience fits what ${company} needs. Thank you for your time and consideration.`,
    signoff: "Sincerely,",
  },
  warm: {
    opening: (role, company) =>
      `I was glad to see the ${role} opening at ${company}, and I would very much like to be considered for it.`,
    openingWithReason: (role, company) =>
      `I was glad to see the ${role} opening at ${company} — it is the kind of team I have wanted to join for a while.`,
    bodyLead: "What I enjoy most is work where the result is visible.",
    bodyLeadNoHighlights: (role) =>
      `I have spent my career doing the work this ${role} role calls for, and I genuinely enjoy it.`,
    closing: (company) =>
      `I would love to talk about how I could help at ${company}. Thank you for taking the time to read this.`,
    signoff: "Best regards,",
  },
  technical: {
    opening: (role, company) =>
      `I am applying for the ${role} position at ${company}. Below is the specific evidence that I can do the work.`,
    openingWithReason: (role, company) =>
      `I am applying for the ${role} position at ${company}. The problems described in the posting are ones I have solved before, with results I can point to.`,
    bodyLead: "The most relevant results from my recent work:",
    bodyLeadNoHighlights: (role) =>
      `My technical background covers the requirements listed for this ${role} role, and I can walk through specific implementations on request.`,
    closing: (company) =>
      `I am happy to go deeper on any of the above, including trade-offs and what I would do differently. Thank you for considering my application.`,
    signoff: "Best regards,",
  },
  direct: {
    opening: (role, company) => `I want the ${role} role at ${company}. Here is why I am a strong fit.`,
    openingWithReason: (role, company) =>
      `I want the ${role} role at ${company}, and I have a specific reason for it.`,
    bodyLead: "What I have delivered:",
    bodyLeadNoHighlights: (role) =>
      `I have done this ${role} job before and I know what the first ninety days need to look like.`,
    closing: (company) =>
      `I would like to talk. If my background fits what ${company} is looking for, I am ready to start the conversation.`,
    signoff: "Kind regards,",
  },
};

/* ---- reading the form ---------------------------------------------------- */

function readForm() {
  const data = {};
  FIELDS.forEach((key) => {
    data[key] = $(key).value.trim();
  });
  data.highlights = data.resumeHighlights
    .split("\n")
    .map((line) => line.replace(/^[-*•·]\s*/, "").trim())
    .filter(Boolean)
    .slice(0, 4);
  return data;
}

/* ---- letter assembly ----------------------------------------------------- */

function lowerFirst(text) {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

function stripTrailingPeriod(text) {
  return text.replace(/\.\s*$/, "");
}

function buildBody(data, copy) {
  const paragraphs = [];

  const role = escapeHtml(data.jobTitle || "the role");
  const company = escapeHtml(data.companyName || "your organisation");

  paragraphs.push(data.whyCompany ? copy.openingWithReason(role, company) : copy.opening(role, company));

  if (data.highlights.length) {
    const items = data.highlights.map((line) => escapeHtml(stripTrailingPeriod(line)));
    // Build a readable sentence rather than dumping a comma-joined blob.
    const listed =
      items.length === 1
        ? lowerFirst(items[0])
        : items
            .slice(0, -1)
            .map(lowerFirst)
            .join("; ") + `; and ${lowerFirst(items[items.length - 1])}`;
    paragraphs.push(`${copy.bodyLead} I ${listed}.`);
  } else {
    paragraphs.push(copy.bodyLeadNoHighlights(role));
  }

  const closingParts = [];
  if (data.whyCompany) closingParts.push(escapeHtml(data.whyCompany));
  closingParts.push(copy.closing(company));
  paragraphs.push(closingParts.join(" "));

  return paragraphs;
}

function render() {
  const data = readForm();
  save(data);

  const ready = data.fullName && data.jobTitle && data.companyName;
  $("letterEmpty").hidden = Boolean(ready);
  $("letterContent").hidden = !ready;
  $("letter").className = `letter style-${layout}`;

  if (!ready) {
    const missing = [];
    if (!data.fullName) missing.push("your name");
    if (!data.jobTitle) missing.push("the job title");
    if (!data.companyName) missing.push("the company");
    $("letterEmpty").textContent = `Add ${missing.join(", ")} and the letter appears here.`;
    $("letterStats").innerHTML = "";
    return;
  }

  const copy = COPY[tone] || COPY.professional;
  const paragraphs = buildBody(data, copy);

  const contact = [];
  if (data.email) contact.push(`<span>${escapeHtml(data.email)}</span>`);
  if (data.phone) contact.push(`<span>${escapeHtml(data.phone)}</span>`);
  const linkedIn = safeUrl(data.linkedIn);
  if (linkedIn) contact.push(`<span><a href="${linkedIn}" target="_blank" rel="noopener noreferrer">LinkedIn</a></span>`);
  const website = safeUrl(data.website);
  if (website) contact.push(`<span><a href="${website}" target="_blank" rel="noopener noreferrer">Portfolio</a></span>`);

  const today = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const greeting = data.hireManagerName
    ? `Dear ${escapeHtml(data.hireManagerName)},`
    : "Dear Hiring Manager,";

  $("letterContent").innerHTML = `
    <div class="letter-sender">
      <strong>${escapeHtml(data.fullName)}</strong>
      ${contact.join("")}
    </div>
    <p class="letter-date">${escapeHtml(today)}</p>
    <div class="letter-to">
      <span>${escapeHtml(data.companyName)}</span>
      <span>Re: ${escapeHtml(data.jobTitle)}</span>
    </div>
    <p class="letter-greeting">${greeting}</p>
    <div class="letter-body">
      ${paragraphs.map((paragraph) => `<p>${paragraph}</p>`).join("")}
    </div>
    <div class="letter-signoff">
      <p>${escapeHtml(copy.signoff)}</p>
      <p class="name">${escapeHtml(data.fullName)}</p>
    </div>`;

  const words = ($("letterContent").innerText || "").split(/\s+/).filter(Boolean).length;
  const tooLong = words > 400;
  $("letterStats").innerHTML = `
    <span class="${tooLong ? "over" : ""}"><b>${words}</b> words</span>
    <span>${tooLong ? "trim toward 250–350" : "a good length"}</span>`;
}

/* ---- persistence --------------------------------------------------------- */

function save(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...data, tone, layout }));
    const state = $("saveState");
    state.textContent = "Saved";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      state.textContent = "";
    }, 1600);
  } catch {
    /* private mode: the letter still works, it just will not persist */
  }
}

function restore() {
  let data;
  try {
    data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  } catch {
    return false;
  }
  if (!data) return false;

  FIELDS.forEach((key) => {
    if (typeof data[key] === "string") $(key).value = data[key];
  });
  if (data.tone) setTone(data.tone);
  if (data.layout) setLayout(data.layout);
  return true;
}

/* ---- option groups ------------------------------------------------------- */

function setTone(value) {
  tone = COPY[value] ? value : "professional";
  document.querySelectorAll("[data-tone]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.tone === tone));
  });
}

function setLayout(value) {
  layout = value;
  document.querySelectorAll("[data-style]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.style === layout));
  });
}

/* ---- actions ------------------------------------------------------------- */

async function copyLetter() {
  const content = $("letterContent");
  if (content.hidden) {
    toast("Fill in your name, the job title, and the company first.", true);
    return;
  }
  try {
    await navigator.clipboard.writeText(content.innerText.trim());
    toast("Letter copied to the clipboard.");
  } catch {
    toast("Your browser blocked clipboard access. Select the letter and copy it manually.", true);
  }
}

function printLetter() {
  const content = $("letterContent");
  if (content.hidden) {
    toast("Fill in your name, the job title, and the company first.", true);
    return;
  }

  const name = $("fullName").value.trim() || "Cover letter";
  const printWindow = window.open("", "_blank", "width=900,height=1000");
  if (!printWindow) {
    toast("Your browser blocked the print window. Allow pop-ups for this page and try again.", true);
    return;
  }

  const styles = Array.from(document.styleSheets)
    .filter((sheet) => sheet.href?.includes("cover-letter.css"))
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
<title>${escapeHtml(name)} — Cover Letter</title>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Schibsted+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
${styles}
:root { color-scheme: light; }
body { margin: 0; background: #fff; }
.letter { box-shadow: none; border-radius: 0; max-width: 190mm; margin: 0 auto; padding: 20mm 18mm; }
@page { size: A4; margin: 0; }
</style>
</head><body><article class="letter style-${layout}">${content.innerHTML}</article></body></html>`);
  printWindow.document.close();

  // Wait for layout and webfonts before printing; whichever fires first wins.
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

/* ---- init ---------------------------------------------------------------- */

mountChrome();
initTheme();

document.querySelectorAll("[data-tone]").forEach((button) => {
  button.addEventListener("click", () => {
    setTone(button.dataset.tone);
    render();
  });
});

document.querySelectorAll("[data-style]").forEach((button) => {
  button.addEventListener("click", () => {
    setLayout(button.dataset.style);
    render();
  });
});

document.querySelector("main").addEventListener("input", (event) => {
  if (event.target.matches("input, textarea")) render();
});

$("copyBtn").addEventListener("click", copyLetter);
$("printBtn").addEventListener("click", printLetter);
$("clearBtn").addEventListener("click", () => {
  if (!window.confirm("Clear the form and start over? This cannot be undone.")) return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* nothing to clear */
  }
  window.location.reload();
});

const restored = restore();
render();
if (restored) toast("Restored your saved letter.");
