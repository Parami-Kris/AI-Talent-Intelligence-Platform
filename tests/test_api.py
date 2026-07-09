from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rank_candidates_endpoint_without_education_requirement():
    jd = {
        "job_title": "Backend Engineer",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "experience_required": "1 year",
        "education_required": "",
    }
    candidates = [
        {
            "name": "Strong Candidate",
            "normalized_skills": ["Python"],
            "experience": [
                {"job_title": "Dev", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}
            ],
        }
    ]

    response = client.post(
        "/rank-candidates",
        json={"jd": jd, "candidates": candidates},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["candidate_name"] == "Strong Candidate"
    assert body["results"][0]["is_eligible"] is True