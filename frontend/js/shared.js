/* ============================================================================
   Shared frontend utilities: theme, API base, toasts, escaping, chrome.
   Loaded by every page before its own script.
   ========================================================================= */

const THEME_KEY = "sca.theme";
const API_KEY = "sca.apiBase";

/* ---- API base -------------------------------------------------------------
   The API runs locally. There is no hosted fallback: pointing at a server that
   does not exist is how every page used to fail silently when opened from a
   file:// URL or any host that was not localhost.
--------------------------------------------------------------------------- */
const LOCAL_API = "http://localhost:5000";

export function defaultApiBase() {
  const { protocol, hostname, origin } = window.location;
  // Served from a real web server that is not the dev static host? Assume the
  // API sits behind the same origin. Otherwise talk to the local API directly.
  if (protocol.startsWith("http") && hostname && hostname !== "localhost" && hostname !== "127.0.0.1") {
    return origin;
  }
  return LOCAL_API;
}

export function getApiBase() {
  let stored = "";
  try {
    stored = localStorage.getItem(API_KEY) || "";
  } catch {
    stored = "";
  }
  return (stored || defaultApiBase()).replace(/\/+$/, "");
}

export function setApiBase(value) {
  try {
    const cleaned = String(value || "").trim().replace(/\/+$/, "");
    if (cleaned) localStorage.setItem(API_KEY, cleaned);
    else localStorage.removeItem(API_KEY);
  } catch {
    /* storage unavailable (private mode); the in-memory default still works */
  }
}

/* ---- theme --------------------------------------------------------------- */
export function resolveTheme() {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* fall through to the OS preference */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    const isDark = theme === "dark";
    const icon = button.querySelector("i");
    if (icon) icon.className = isDark ? "fa-solid fa-sun" : "fa-solid fa-moon";
    button.setAttribute("aria-label", isDark ? "Switch to light theme" : "Switch to dark theme");
  });
}

export function initTheme() {
  applyTheme(resolveTheme());
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next =
        (document.documentElement.getAttribute("data-theme") || "light") === "light" ? "dark" : "light";
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch {
        /* not persisting is acceptable; the toggle still works this session */
      }
      applyTheme(next);
    });
  });
}

/* ---- escaping ------------------------------------------------------------ */
export function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Only emit links the browser can safely navigate to. */
export function safeUrl(value = "") {
  const trimmed = String(value).trim();
  if (!trimmed) return "";
  if (/^(https?:)?\/\//i.test(trimmed)) return escapeHtml(trimmed);
  if (/^[a-z][a-z0-9+.-]*:/i.test(trimmed)) return ""; // javascript:, data:, vbscript:
  return escapeHtml(`https://${trimmed}`);
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

/* ---- toast --------------------------------------------------------------- */
let toastTimer = null;

export function toast(message, isError = false) {
  const element = document.getElementById("toast");
  if (!element) {
    (isError ? console.error : console.info)(message);
    return;
  }
  element.textContent = message;
  element.classList.toggle("is-error", Boolean(isError));
  element.classList.add("is-visible");
  clearTimeout(toastTimer);
  // Errors need longer than confirmations: the reader has to act on them.
  toastTimer = setTimeout(() => element.classList.remove("is-visible"), isError ? 6000 : 3000);
}

/* ---- uploads ------------------------------------------------------------- */
export const ALLOWED_EXTENSIONS = new Set(["pdf", "docx", "txt", "png", "jpg", "jpeg", "webp"]);
export const MAX_FILE_BYTES = 10 * 1024 * 1024;

export function validateFile(file) {
  if (!file) return "Choose a file first.";
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return `${file.name} is a .${ext} file. Upload a PDF, DOCX, TXT, PNG, JPG, or WEBP.`;
  }
  if (file.size > MAX_FILE_BYTES) {
    return `${file.name} is ${formatBytes(file.size)}. The limit is 10 MB per file.`;
  }
  if (file.size === 0) return `${file.name} is empty.`;
  return null;
}

/* ---- API errors ---------------------------------------------------------- */
/** Turn any failed response into a sentence naming the problem and the fix. */
export async function describeApiError(response, fallback) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const data = await response.json();
      if (data?.error) return data.error;
    } catch {
      /* body was not valid JSON after all */
    }
  }
  if (response.status === 413) return "That upload is too large for the server to accept.";
  if (response.status >= 500) return "The analyzer hit an internal error. Check the API console for details.";
  return fallback;
}

/** A connection failure is the single most common problem: say what to do. */
export function describeNetworkError(apiBase) {
  return `Cannot reach the API at ${apiBase}. Start it with "python run.py" in the backend folder, or set a different address under Settings.`;
}

/* ---- page chrome --------------------------------------------------------- */
const NAV = [
  { href: "./import.html", label: "Import" },
  { href: "./analyzer.html", label: "Analyzer" },
  { href: "./job-finder.html", label: "Job Match" },
  { href: "./cv-maker.html", label: "CV Maker" },
  { href: "./cover-letter-generator.html", label: "Cover Letter" },
  { href: "./bulk-analyzer.html", label: "Bulk Review" },
];

/** Render the shared top bar so navigation cannot drift between pages. */
export function mountChrome() {
  const host = document.getElementById("topbar");
  if (!host) return;

  const current = window.location.pathname.split("/").pop() || "index.html";
  const links = NAV.map((item) => {
    const file = item.href.replace("./", "");
    const active = file === current ? ' aria-current="page"' : "";
    return `<a href="${item.href}"${active}>${escapeHtml(item.label)}</a>`;
  }).join("");

  host.className = "topbar";
  host.innerHTML = `
    <div class="topbar-inner">
      <a class="wordmark" href="./index.html">Career<span>.</span>Desk</a>
      <nav class="topnav" aria-label="Tools">${links}</nav>
      <button class="icon-btn" data-theme-toggle type="button" aria-label="Switch theme">
        <i class="fa-solid fa-moon" aria-hidden="true"></i>
      </button>
    </div>`;
}

/* ---- settings disclosure ------------------------------------------------- */
/** Wire the shared "API address" field found in each page's Settings block. */
export function mountApiSetting() {
  const input = document.getElementById("apiBase");
  if (!input) return;
  input.value = getApiBase();
  input.placeholder = defaultApiBase();
  input.addEventListener("change", () => {
    setApiBase(input.value);
    input.value = getApiBase();
    toast(`API address set to ${getApiBase()}`);
  });

  const reset = document.getElementById("apiBaseReset");
  if (reset) {
    reset.addEventListener("click", () => {
      setApiBase("");
      input.value = getApiBase();
      toast("API address reset to the default.");
    });
  }
}

/* ---- drop zones ---------------------------------------------------------- */
/**
 * Wire a drop zone to a file input.
 * `onFiles` receives a FileList; the caller decides how many it keeps.
 */
export function mountDropZone(zoneId, inputId, onFiles) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  ["dragenter", "dragover"].forEach((name) =>
    zone.addEventListener(name, (event) => {
      event.preventDefault();
      zone.classList.add("is-active");
    })
  );
  ["dragleave", "dragend", "drop"].forEach((name) =>
    zone.addEventListener(name, (event) => {
      event.preventDefault();
      zone.classList.remove("is-active");
    })
  );

  zone.addEventListener("drop", (event) => {
    if (event.dataTransfer?.files?.length) onFiles(event.dataTransfer.files);
  });
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", (event) => {
    if (event.target.files?.length) onFiles(event.target.files);
    // Reset so re-picking the same file still fires a change event.
    input.value = "";
  });
}

/* ---- downloads ----------------------------------------------------------- */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/* ---- score bands --------------------------------------------------------- */
export function scoreTone(score) {
  if (score >= 85) return "excellent";
  if (score >= 70) return "good";
  if (score >= 55) return "fair";
  return "poor";
}

export function scoreBand(score) {
  if (score >= 85) return "Ready to send";
  if (score >= 70) return "Nearly there";
  if (score >= 55) return "Needs work";
  return "Not screening-ready";
}

/** Count a number up to its final value once, as the single authored moment. */
export function animateNumber(element, target, duration = 900) {
  if (!element) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (reduce) {
    element.textContent = String(target);
    return;
  }
  const start = performance.now();
  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    // Exponential ease-out, matching the meters.
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = String(Math.round(target * eased));
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
