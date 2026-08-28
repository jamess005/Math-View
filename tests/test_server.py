"""API contract: sequences out, structured parse errors on bad input."""

from fastapi.testclient import TestClient

from mathview.server import create_app

client = TestClient(create_app())


def test_topics_are_listed():
    response = client.get("/api/topics")

    assert response.status_code == 200
    assert set(response.json()["topics"]) >= {"growth", "functions"}


def test_growth_sequence_returns_five_steps():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["n", "n^2"], "params": {}}
    )

    assert response.status_code == 200
    assert len(response.json()["steps"]) == 5


def test_parse_error_returns_400_with_an_offset():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["n^^2"], "params": {}}
    )

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["input"] == "n^^2"
    assert isinstance(body["offset"], int)


def test_unknown_topic_returns_404():
    response = client.post(
        "/api/sequence", json={"topic": "nope", "rows": ["n"], "params": {}}
    )

    assert response.status_code == 404


def test_index_is_served():
    response = client.get("/")

    assert response.status_code == 200
    assert "MathView" in response.text


def test_unmatched_brackets_return_a_readable_400():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["(1+2"], "params": {}}
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "check the brackets - they do not match"


def test_too_many_rows_returns_400():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["n"] * 7, "params": {}}
    )

    assert response.status_code == 400


def test_a_non_positive_range_returns_400():
    response = client.post(
        "/api/sequence",
        json={"topic": "growth", "rows": ["n"], "params": {"n_max": 0}},
    )

    assert response.status_code == 400


def test_the_functions_topic_is_reachable():
    response = client.post(
        "/api/sequence",
        json={"topic": "functions", "rows": ["f(x) = 2x + 3"], "params": {"x": 4}},
    )

    assert response.status_code == 200
    assert response.json()["steps"][-1]["title"] == "f(4) = 11"
