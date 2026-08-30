"""The LLM layer is optional, so its failure modes must be non-events."""

import sys
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services import llm  # noqa: E402

OFF = {"LLM_ENABLED": False, "LLM_BASE_URL": "http://x/v1", "LLM_MODEL": "m"}
ON = {"LLM_ENABLED": True, "LLM_BASE_URL": "http://x/v1", "LLM_MODEL": "m",
      "LLM_API_KEY": "", "LLM_TIMEOUT": 5}


def test_disabled_returns_none_without_any_network_call(monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("no request should be made when the layer is disabled")

    monkeypatch.setattr(requests, "post", explode)
    assert llm.enrich_analysis(OFF, "resume text", "", []) is None


def test_unreachable_endpoint_degrades_to_none(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "post", refuse)
    assert llm.enrich_analysis(ON, "resume text", "", []) is None


def test_http_error_degrades_to_none(monkeypatch):
    class Response:
        status_code = 500
        text = "internal error"

    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
    assert llm.enrich_analysis(ON, "resume text", "", []) is None


def _reply(content: str):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": content}}]}

    return lambda *a, **k: Response()


def test_unparseable_reply_degrades_to_none(monkeypatch):
    monkeypatch.setattr(requests, "post", _reply("I'm sorry, I can't do that."))
    assert llm.enrich_analysis(ON, "resume text", "", []) is None


def test_json_wrapped_in_a_code_fence_is_parsed(monkeypatch):
    monkeypatch.setattr(requests, "post", _reply(
        'Here you go:\n```json\n{"additional_skills": ["Stakeholder Management"], '
        '"summary": "Strong operator."}\n```'
    ))
    result = llm.enrich_analysis(ON, "resume text", "", [])
    assert result["additional_skills"] == ["Stakeholder Management"]
    assert result["summary"] == "Strong operator."


def test_skills_already_detected_are_not_duplicated(monkeypatch):
    monkeypatch.setattr(requests, "post", _reply('{"additional_skills": ["Python", "Rust"]}'))
    result = llm.enrich_analysis(ON, "resume text", "", ["Python"])
    assert result["additional_skills"] == ["Rust"]


def test_malformed_rewrite_entries_are_dropped(monkeypatch):
    monkeypatch.setattr(requests, "post", _reply(
        '{"rewrite_suggestions": [{"original": "did stuff", "improved": "Delivered [X%] gain"},'
        ' {"original": "no improved key"}, "not an object"]}'
    ))
    result = llm.enrich_analysis(ON, "resume text", "", [])
    assert result["rewrite_suggestions"] == [
        {"original": "did stuff", "improved": "Delivered [X%] gain"}
    ]


def test_resume_text_sent_is_capped(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": '{"summary": "ok"}'}}]}

    def capture(_url, **kwargs):
        captured["prompt"] = kwargs["json"]["messages"][1]["content"]
        return Response()

    monkeypatch.setattr(requests, "post", capture)
    llm.enrich_analysis(ON, "x" * 50_000, "", [])
    assert "x" * (llm.MAX_CHARS_SENT + 1) not in captured["prompt"]


def test_status_reports_disabled_without_leaking_config():
    reported = llm.status(OFF)
    assert reported["enabled"] is False
    assert reported["model"] is None
    assert reported["endpoint"] is None
