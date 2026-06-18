from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
  response = client.get("/health")
  assert response.status_code == 200
  assert response.json()["status"] == "UP"


def test_live(client: TestClient) -> None:
  response = client.get("/live")
  assert response.status_code == 200
  assert response.json()["status"] == "ALIVE"


def test_create_token(client: TestClient) -> None:
  response = client.post("/api/v1/auth/token")
  assert response.status_code == 200
  assert "access_token" in response.json()


def test_chat_requires_auth(client: TestClient) -> None:
  response = client.post("/api/v1/chat", json={"question": "hello"})
  assert response.status_code == 401


def test_chat_with_auth(client: TestClient) -> None:
  token = client.post("/api/v1/auth/token").json()["access_token"]
  response = client.post(
    "/api/v1/chat",
    json={"question": "hello"},
    headers={"Authorization": f"Bearer {token}"},
  )
  assert response.status_code == 200
  assert "answer" in response.json()
