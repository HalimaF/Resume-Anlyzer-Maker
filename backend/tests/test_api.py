from io import BytesIO


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_skills_endpoint_returns_list(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    data = response.get_json()
    assert "skills" in data
    assert data["count"] > 0


def test_skills_endpoint_supports_query(client):
    response = client.get("/api/skills?q=react")
    assert response.status_code == 200
    data = response.get_json()
    assert any("react" in skill.lower() for skill in data["skills"])


def test_analyze_text_endpoint(client):
    payload = {
        "resume_text": "Python Flask SQL Experience Education Projects Skills Docker",
        "job_description": "Need python flask docker and kubernetes experience",
    }
    response = client.post("/api/analyze/text", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert "resume_score" in data
    assert "detected_skills" in data
    assert "structure_analysis" in data
    assert "feedback" in data
    assert data["job_description_analysis"] is not None


def test_analyze_upload_endpoint_with_monkeypatched_extractor(client, monkeypatch):
    def fake_extract_text(_):
        return "Python Flask SQL Skills Experience Education Projects"

    monkeypatch.setattr("app.routes.extract_resume_text", fake_extract_text)

    data = {
        "resume": (BytesIO(b"fake pdf"), "resume.pdf"),
        "job_description": "Python and Flask",
    }
    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    payload = response.get_json()
    assert "Python" in payload["detected_skills"]
    assert "structure_analysis" in payload


def test_analyze_text_endpoint_validates_input(client):
    response = client.post("/api/analyze/text", json={"resume_text": "   "})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_ats_check_endpoint(client):
    payload = {
        "resume_text": "John Doe john@example.com +1 555 123 4567 Experience Education Skills Built APIs with Python Flask",
    }
    response = client.post("/api/ats-check", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "ats_score" in data
    assert "checks" in data
    assert "recommendations" in data
