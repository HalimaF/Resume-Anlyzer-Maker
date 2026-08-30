"""Optional LLM enrichment through any OpenAI-compatible endpoint.

This layer is strictly additive. The deterministic analyzer produces the score
and the ranked actions on its own; the model only adds things rules are bad at:
naming skills that are not in the catalog, and writing feedback in the
candidate's own context. Every failure path returns ``None`` and the request
completes normally, so a missing, slow, or broken model never costs a user
their analysis.

Works with any server that speaks the OpenAI chat-completions shape:

    Ollama (local, free, open source, no key)
        LLM_BASE_URL=http://localhost:11434/v1   LLM_MODEL=llama3.1:8b
    Groq (free tier, hosted open-source models)
        LLM_BASE_URL=https://api.groq.com/openai/v1
        LLM_MODEL=llama-3.3-70b-versatile        LLM_API_KEY=gsk_...
    OpenRouter (free-tier open models)
        LLM_BASE_URL=https://openrouter.ai/api/v1
        LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free   LLM_API_KEY=sk-or-...
    llama.cpp / LM Studio / vLLM: point LLM_BASE_URL at the local server.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Resume text is personal data. Cap what leaves the process and say so in the
# UI, rather than streaming an entire document to a third party by default.
MAX_CHARS_SENT = 6000

_SYSTEM_PROMPT = (
    "You are a precise resume reviewer assisting an automated analyzer. "
    "You never invent experience the candidate did not describe. "
    "You reply with a single JSON object and no other text."
)

_USER_TEMPLATE = """Analyse this resume{jd_clause}.

A rule-based engine already detected these skills:
{known_skills}

RESUME
------
{resume}
{jd_block}

Return a JSON object with exactly these keys:
{{
  "additional_skills": [
      "skills clearly evidenced by the resume that are missing from the list above.
       Only include a skill if the resume shows concrete evidence. Maximum 12."
  ],
  "overstated_claims": [
      "at most 3 short notes on claims the resume asserts without any supporting
       evidence. Empty list if none."
  ],
  "rewrite_suggestions": [
      {{"original": "an exact bullet from the resume that is weak",
        "improved": "the same bullet rewritten with a concrete action and a
                     measurable outcome. Never invent a number: if none exists,
                     use a placeholder like [X%] the candidate must fill in."}}
  ],
  "summary": "two sentences on this candidate's strongest positioning for the target role"
}}

Return at most 4 rewrite_suggestions. Output only the JSON object."""


def _config(app_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "enabled": bool(app_config.get("LLM_ENABLED")),
        "base_url": str(app_config.get("LLM_BASE_URL", "")).rstrip("/"),
        "model": str(app_config.get("LLM_MODEL", "")),
        "api_key": str(app_config.get("LLM_API_KEY", "")),
        "timeout": int(app_config.get("LLM_TIMEOUT", 45)),
    }


def status(app_config: Dict[str, Any]) -> Dict[str, Any]:
    """What the UI needs to describe the enrichment layer honestly."""
    cfg = _config(app_config)
    configured = bool(cfg["enabled"] and cfg["base_url"] and cfg["model"])
    return {
        "enabled": configured,
        "model": cfg["model"] if configured else None,
        "endpoint": cfg["base_url"] if configured else None,
        "sends_resume_text": configured,
        "max_chars_sent": MAX_CHARS_SENT if configured else 0,
    }


def _extract_json(content: str) -> Optional[Dict[str, Any]]:
    """Pull a JSON object out of a model reply.

    Small open models routinely wrap JSON in prose or a code fence even when
    told not to, so parse defensively rather than trusting the format.
    """
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()

    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost brace-delimited span.
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(content[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _string_list(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    out = [str(item).strip() for item in value if isinstance(item, (str, int, float)) and str(item).strip()]
    return out[:limit]


def _rewrites(value: Any, limit: int) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        original = str(item.get("original", "")).strip()
        improved = str(item.get("improved", "")).strip()
        if original and improved:
            out.append({"original": original[:400], "improved": improved[:400]})
    return out[:limit]


def enrich_analysis(
    app_config: Dict[str, Any],
    resume_text: str,
    job_description: str,
    known_skills: List[str],
) -> Optional[Dict[str, Any]]:
    """Ask the configured model for what rules cannot see.

    Returns ``None`` whenever enrichment is unavailable or unusable, which the
    caller treats as "no enrichment" rather than as an error.
    """
    cfg = _config(app_config)
    if not (cfg["enabled"] and cfg["base_url"] and cfg["model"]):
        return None

    resume = (resume_text or "").strip()[:MAX_CHARS_SENT]
    if not resume:
        return None

    jd = (job_description or "").strip()[:2000]
    prompt = _USER_TEMPLATE.format(
        jd_clause=" against the target job description" if jd else "",
        known_skills=", ".join(known_skills[:60]) or "(none detected)",
        resume=resume,
        jd_block=f"\n\nTARGET JOB DESCRIPTION\n----------------------\n{jd}" if jd else "",
    )

    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        # Honoured by most OpenAI-compatible servers; harmlessly ignored by others.
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            f"{cfg['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=cfg["timeout"],
        )
        if response.status_code >= 400:
            logger.warning("LLM enrichment failed: HTTP %s %s", response.status_code, response.text[:200])
            return None
        body = response.json()
        content = body["choices"][0]["message"]["content"]
    except requests.RequestException as exc:
        logger.warning("LLM enrichment unreachable: %s", exc)
        return None
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("LLM enrichment returned an unexpected shape: %s", exc)
        return None

    parsed = _extract_json(content)
    if parsed is None:
        logger.warning("LLM enrichment returned unparseable content")
        return None

    known_lower = {skill.lower() for skill in known_skills}
    additional = [
        skill for skill in _string_list(parsed.get("additional_skills"), 12)
        if skill.lower() not in known_lower
    ]

    result = {
        "additional_skills": additional,
        "overstated_claims": _string_list(parsed.get("overstated_claims"), 3),
        "rewrite_suggestions": _rewrites(parsed.get("rewrite_suggestions"), 4),
        "summary": str(parsed.get("summary", "")).strip()[:600] or None,
        "model": cfg["model"],
    }

    # Nothing usable came back; report absence rather than an empty section.
    if not any((result["additional_skills"], result["overstated_claims"],
                result["rewrite_suggestions"], result["summary"])):
        return None
    return result
