const cvThemeToggle = document.getElementById("cvThemeToggle");
const savedTheme = localStorage.getItem("resumeAnalyzerTheme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);

function updateCVThemeButton(theme) {
  const icon = cvThemeToggle.querySelector("i");
  if (theme === "dark") {
    icon.className = "fa-solid fa-sun";
  } else {
    icon.className = "fa-solid fa-moon";
  }
}

updateCVThemeButton(savedTheme);
cvThemeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("resumeAnalyzerTheme", next);
  updateCVThemeButton(next);
});

const tabBtns = document.querySelectorAll(".tab-btn");
const tabContents = document.querySelectorAll(".tab-content");

tabBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabBtns.forEach((b) => b.classList.remove("active"));
    tabContents.forEach((tc) => tc.classList.remove("active"));

    btn.classList.add("active");
    const tabId = btn.dataset.tab + "-tab";
    document.getElementById(tabId).classList.add("active");
  });
});

const fullNameInput = document.getElementById("fullName");
const emailInput = document.getElementById("email");
const phoneInput = document.getElementById("phone");
const locationInput = document.getElementById("location");
const linkedinInput = document.getElementById("linkedin");
const summaryInput = document.getElementById("summary");
const skillsInput = document.getElementById("skillsInput");
const experienceList = document.getElementById("experienceList");
const educationList = document.getElementById("educationList");
const projectsList = document.getElementById("projectsList");

const addExperienceBtn = document.getElementById("addExperienceBtn");
const addEducationBtn = document.getElementById("addEducationBtn");
const addProjectBtn = document.getElementById("addProjectBtn");
const downloadCvBtn = document.getElementById("downloadCvBtn");
const previewCvBtn = document.getElementById("previewCvBtn");
const toast = document.getElementById("toast");
const cvTemplateSelect = document.getElementById("cvTemplateSelect");
const rewriteCvBtn = document.getElementById("rewriteCvBtn");
const rewriteSuggestions = document.getElementById("rewriteSuggestions");
const jobDescriptionTarget = document.getElementById("jobDescriptionTarget");

const DEFAULT_API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:5000"
    : "https://smart-resume-analyzer-api.onrender.com";

const savedApiBase = localStorage.getItem("resumeAnalyzerApiBase") || DEFAULT_API_BASE;
let sectionIdCounter = 0;

let cvData = {
  fullName: "",
  email: "",
  phone: "",
  location: "",
  linkedin: "",
  summary: "",
  skills: [],
  experience: [],
  education: [],
  projects: [],
};

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.style.borderColor = isError ? "#e63946" : "";
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function updatePreview() {
  cvData.fullName = fullNameInput.value || "Your Name";
  cvData.email = emailInput.value;
  cvData.phone = phoneInput.value;
  cvData.location = locationInput.value;
  cvData.linkedin = linkedinInput.value;
  cvData.summary = summaryInput.value;

  document.getElementById("previewName").textContent = cvData.fullName;
  document.getElementById("previewSummary").textContent = cvData.summary;

  const contactParts = [];
  if (cvData.email) contactParts.push(cvData.email);
  if (cvData.phone) contactParts.push(cvData.phone);
  if (cvData.location) contactParts.push(cvData.location);

  document.getElementById("previewEmail").textContent = cvData.email;
  document.getElementById("previewPhone").textContent = cvData.phone;
  document.getElementById("previewLocation").textContent = cvData.location;

  updateAllPreviews();
}

function addExperienceField(data = {}) {
  const id = ++sectionIdCounter;
  const html = `
    <div class="form-section" id="exp-${id}">
      <div class="section-header">
        <h4>Work Experience</h4>
        <button class="remove-btn" onclick="removeExperience(${id})">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Job Title *</label>
          <input type="text" class="exp-title" value="${data.title || ""}" placeholder="Senior Engineer" />
        </div>
        <div class="form-group">
          <label>Company *</label>
          <input type="text" class="exp-company" value="${data.company || ""}" placeholder="Tech Company" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Start Date</label>
          <input type="text" class="exp-start" value="${data.start || ""}" placeholder="Jan 2020" />
        </div>
        <div class="form-group">
          <label>End Date</label>
          <input type="text" class="exp-end" value="${data.end || ""}" placeholder="Present" />
        </div>
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea rows="3" class="exp-desc" placeholder="Describe your responsibilities and achievements...">${data.description || ""}</textarea>
      </div>
    </div>
  `;
  experienceList.insertAdjacentHTML("beforeend", html);
  attachExperienceListeners(id);
}

function attachExperienceListeners(id) {
  const section = document.getElementById(`exp-${id}`);
  section
    .querySelectorAll("input, textarea")
    .forEach((field) => field.addEventListener("change", updateAllPreviews));
}

function removeExperience(id) {
  document.getElementById(`exp-${id}`).remove();
  updateAllPreviews();
}

function addEducationField(data = {}) {
  const id = ++sectionIdCounter;
  const html = `
    <div class="form-section" id="edu-${id}">
      <div class="section-header">
        <h4>Education</h4>
        <button class="remove-btn" onclick="removeEducation(${id})">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Degree *</label>
          <input type="text" class="edu-degree" value="${data.degree || ""}" placeholder="Bachelor of Science" />
        </div>
        <div class="form-group">
          <label>University *</label>
          <input type="text" class="edu-school" value="${data.school || ""}" placeholder="University Name" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Field of Study</label>
          <input type="text" class="edu-field" value="${data.field || ""}" placeholder="Computer Science" />
        </div>
        <div class="form-group">
          <label>Graduation Year</label>
          <input type="text" class="edu-year" value="${data.year || ""}" placeholder="2020" />
        </div>
      </div>
    </div>
  `;
  educationList.insertAdjacentHTML("beforeend", html);
  attachEducationListeners(id);
}

function attachEducationListeners(id) {
  const section = document.getElementById(`edu-${id}`);
  section
    .querySelectorAll("input, textarea")
    .forEach((field) => field.addEventListener("change", updateAllPreviews));
}

function removeEducation(id) {
  document.getElementById(`edu-${id}`).remove();
  updateAllPreviews();
}

function addProjectField(data = {}) {
  const id = ++sectionIdCounter;
  const html = `
    <div class="form-section" id="proj-${id}">
      <div class="section-header">
        <h4>Project</h4>
        <button class="remove-btn" onclick="removeProject(${id})">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Project Name *</label>
          <input type="text" class="proj-name" value="${data.name || ""}" placeholder="Project Name" />
        </div>
        <div class="form-group">
          <label>Link (Optional)</label>
          <input type="url" class="proj-link" value="${data.link || ""}" placeholder="https://..." />
        </div>
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea rows="2" class="proj-desc" placeholder="Describe the project and your role...">${data.description || ""}</textarea>
      </div>
    </div>
  `;
  projectsList.insertAdjacentHTML("beforeend", html);
  attachProjectListeners(id);
}

function applyTemplate(templateName) {
  const preview = document.getElementById("cvPreview");
  preview.classList.remove("template-modern", "template-classic", "template-minimal");
  preview.classList.add(`template-${templateName}`);
}

async function rewriteCvWithAI() {
  const data = collectCVData();
  const jdText = (jobDescriptionTarget?.value || "").trim();

  if (!jdText) {
    showToast("Please paste a target job description first.", true);
    return;
  }

  if (!data.summary && data.experience.length === 0) {
    showToast("Add summary or experience content before rewriting.", true);
    return;
  }

  rewriteCvBtn.disabled = true;
  rewriteCvBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Rewriting...';

  try {
    const response = await fetch(`${savedApiBase}/api/rewrite-cv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        summary: data.summary,
        experience: data.experience,
        job_description: jdText,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Rewrite failed.");
    }

    const result = await response.json();

    if (typeof result.rewritten_summary === "string") {
      summaryInput.value = result.rewritten_summary;
    }

    const expSections = Array.from(document.querySelectorAll("#experienceList .form-section"));
    (result.rewritten_experience || []).forEach((item, idx) => {
      const sec = expSections[idx];
      if (!sec) return;
      const desc = sec.querySelector(".exp-desc");
      if (desc && item.description) {
        desc.value = item.description;
      }
    });

    const suggestions = result.suggestions || [];
    rewriteSuggestions.innerHTML = suggestions.length
      ? `<ul>${suggestions.map((s) => `<li>${s}</li>`).join("")}</ul>`
      : "";

    updateAllPreviews();
    showToast("CV rewritten for the selected job.");
  } catch (error) {
    showToast(error.message || "Unable to rewrite CV.", true);
  } finally {
    rewriteCvBtn.disabled = false;
    rewriteCvBtn.innerHTML = '<i class="fa-solid fa-robot"></i> Analyze & Rewrite CV';
  }
}

function attachProjectListeners(id) {
  const section = document.getElementById(`proj-${id}`);
  section
    .querySelectorAll("input, textarea")
    .forEach((field) => field.addEventListener("change", updateAllPreviews));
}

function removeProject(id) {
  document.getElementById(`proj-${id}`).remove();
  updateAllPreviews();
}

function collectCVData() {
  cvData.fullName = fullNameInput.value || "Your Name";
  cvData.email = emailInput.value;
  cvData.phone = phoneInput.value;
  cvData.location = locationInput.value;
  cvData.linkedin = linkedinInput.value;
  cvData.summary = summaryInput.value;

  cvData.skills = skillsInput.value
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s);

  cvData.experience = Array.from(document.querySelectorAll("#experienceList .form-section")).map((sec) => ({
    title: sec.querySelector(".exp-title").value,
    company: sec.querySelector(".exp-company").value,
    start: sec.querySelector(".exp-start").value,
    end: sec.querySelector(".exp-end").value,
    description: sec.querySelector(".exp-desc").value,
  }));

  cvData.education = Array.from(document.querySelectorAll("#educationList .form-section")).map((sec) => ({
    degree: sec.querySelector(".edu-degree").value,
    school: sec.querySelector(".edu-school").value,
    field: sec.querySelector(".edu-field").value,
    year: sec.querySelector(".edu-year").value,
  }));

  cvData.projects = Array.from(document.querySelectorAll("#projectsList .form-section")).map((sec) => ({
    name: sec.querySelector(".proj-name").value,
    link: sec.querySelector(".proj-link").value,
    description: sec.querySelector(".proj-desc").value,
  }));

  return cvData;
}

function updateAllPreviews() {
  const data = collectCVData();

  document.getElementById("previewName").textContent = data.fullName;
  document.getElementById("previewSummary").textContent = data.summary;
  document.getElementById("previewEmail").textContent = data.email;
  document.getElementById("previewPhone").textContent = data.phone;
  document.getElementById("previewLocation").textContent = data.location;

  let expHtml = "";
  data.experience.forEach((exp) => {
    if (exp.title || exp.company) {
      expHtml += `<div class="preview-item">
        <h4>${exp.title} at ${exp.company}</h4>
        ${exp.start || exp.end ? `<p class="date">${exp.start || ""} - ${exp.end || ""}</p>` : ""}
        ${exp.description ? `<p>${exp.description}</p>` : ""}
      </div>`;
    }
  });
  document.getElementById("previewExpList").innerHTML = expHtml || '<p class="empty">No experiences added</p>';

  let eduHtml = "";
  data.education.forEach((edu) => {
    if (edu.degree || edu.school) {
      eduHtml += `<div class="preview-item">
        <h4>${edu.degree}${edu.field ? " in " + edu.field : ""}</h4>
        <p>${edu.school}${edu.year ? " - " + edu.year : ""}</p>
      </div>`;
    }
  });
  document.getElementById("previewEduList").innerHTML = eduHtml || '<p class="empty">No education added</p>';

  let skillsHtml = "";
  data.skills.forEach((skill) => {
    skillsHtml += `<span class="skill-chip">${skill}</span>`;
  });
  document.getElementById("previewSkillsList").innerHTML = skillsHtml || '<p class="empty">No skills added</p>';

  let projHtml = "";
  data.projects.forEach((proj) => {
    if (proj.name) {
      projHtml += `<div class="preview-item">
        <h4>${proj.name}${proj.link ? ` <a href="${proj.link}" target="_blank"><i class="fa-solid fa-link"></i></a>` : ""}</h4>
        ${proj.description ? `<p>${proj.description}</p>` : ""}
      </div>`;
    }
  });
  document.getElementById("previewProjList").innerHTML = projHtml || '<p class="empty">No projects added</p>';

  document.getElementById("previewExp").style.display = data.experience.some((e) => e.title || e.company) ? "block" : "none";
  document.getElementById("previewEdu").style.display = data.education.some((e) => e.degree || e.school) ? "block" : "none";
  document.getElementById("previewSkills").style.display = data.skills.length > 0 ? "block" : "none";
  document.getElementById("previewProj").style.display = data.projects.some((p) => p.name) ? "block" : "none";
}

function generatePDF() {
  const data = collectCVData();

  if (!data.fullName || !data.email || !data.phone) {
    showToast("Please fill in Name, Email, and Phone fields.", true);
    return;
  }

  showToast("PDF generation started. This will open in a new tab.");

  // Create a simple PDF using HTML print
  const printContent = document.getElementById("cvPreview").innerHTML;
  const printWindow = window.open("", "", "height=600,width=800");
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${data.fullName} - CV</title>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; color: #333; }
        h2 { color: #2d6375; margin-top: 0; }
        h3 { color: #2d6375; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #2d6375; padding-bottom: 5px; }
        h4 { margin: 10px 0 3px 0; }
        p { margin: 5px 0; }
        .preview-summary { font-style: italic; margin-bottom: 10px; }
        .preview-contact { margin-bottom: 15px; }
        .preview-contact span { margin-right: 15px; }
        .preview-item { margin-bottom: 12px; }
        .date { color: #666; font-size: 0.95em; }
        .skill-chip { display: inline-block; background: #e8f4f8; color: #2d6375; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 0.9em; }
        @media print { body { margin: 10px; } }
      </style>
    </head>
    <body>
      ${printContent}
    </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
}

// Event listeners
fullNameInput.addEventListener("input", updatePreview);
emailInput.addEventListener("input", updatePreview);
phoneInput.addEventListener("input", updatePreview);
locationInput.addEventListener("input", updatePreview);
linkedinInput.addEventListener("input", updatePreview);
summaryInput.addEventListener("input", updatePreview);
skillsInput.addEventListener("input", updateAllPreviews);

addExperienceBtn.addEventListener("click", () => addExperienceField());
addEducationBtn.addEventListener("click", () => addEducationField());
addProjectBtn.addEventListener("click", () => addProjectField());

downloadCvBtn.addEventListener("click", generatePDF);
previewCvBtn.addEventListener("click", () => {
  document.querySelector(".cv-preview-section").scrollIntoView({ behavior: "smooth" });
});

if (cvTemplateSelect) {
  cvTemplateSelect.addEventListener("change", () => applyTemplate(cvTemplateSelect.value));
  applyTemplate(cvTemplateSelect.value || "modern");
}

if (rewriteCvBtn) {
  rewriteCvBtn.addEventListener("click", rewriteCvWithAI);
}

// Initialize
updatePreview();
