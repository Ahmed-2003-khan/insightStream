def test_query_without_auth_returns_403(client):
    response = client.post(
        "/api/v1/intelligence/query",
        json={"query": "test question"}
    )
    assert response.status_code == 403

def test_query_with_wrong_key_returns_403(client):
    response = client.post(
        "/api/v1/intelligence/query",
        json={"query": "test question"},
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 403

def test_query_with_correct_key_returns_200(client, auth_headers):
    response = client.post(
        "/api/v1/intelligence/query",
        json={"query": "test question"},
        headers=auth_headers
    )
    assert response.status_code == 200

def test_query_response_has_required_fields(client, auth_headers):
    response = client.post(
        "/api/v1/intelligence/query",
        json={"query": "test question"},
        headers=auth_headers
    )
    data = response.json()
    assert "report" in data
    assert "cache_hit" in data
    assert "signal_label" in data
    assert "signal_confidence" in data

def test_ingest_without_auth_returns_403(client):
    response = client.post(
        "/api/v1/intelligence/ingest/news",
        json={"topic": "Microsoft AI"}
    )
    assert response.status_code == 403

def test_reports_endpoint_requires_auth(client):
    response = client.get("/api/v1/intelligence/reports")
    assert response.status_code == 403

def test_reports_endpoint_returns_list(client, auth_headers):
    response = client.get(
        "/api/v1/intelligence/reports",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "reports" in data
    assert isinstance(data["reports"], list)

def test_query_empty_string_returns_422(client, auth_headers):
    response = client.post(
        "/api/v1/intelligence/query",
        json={"query": ""},
        headers=auth_headers
    )
    # Empty query should be rejected at validation level
    assert response.status_code in [422, 400]
