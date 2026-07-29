from fastapi.testclient import TestClient

from app.core.config import settings


def _csrf_headers(client: TestClient) -> dict[str, str]:
  response = client.get("/api/v1/auth/csrf")
  assert response.status_code == 200
  token = response.json()["csrf_token"]
  return {"X-CSRF-Token": token}


def test_register_login_me_logout(client: TestClient) -> None:
  headers = _csrf_headers(client)
  register = client.post(
    "/api/v1/auth/register",
    json={"email": "alice@example.com", "password": "password123"},
    headers=headers,
  )
  assert register.status_code == 200
  assert register.json()["user"]["email"] == "alice@example.com"
  assert "verification_token" in register.json()

  headers = _csrf_headers(client)
  login = client.post(
    "/api/v1/auth/login",
    json={"email": "alice@example.com", "password": "password123"},
    headers=headers,
  )
  assert login.status_code == 200
  assert client.cookies.get("session_id")

  me = client.get("/api/v1/auth/me")
  assert me.status_code == 200
  assert me.json()["email"] == "alice@example.com"

  headers = _csrf_headers(client)
  logout = client.post("/api/v1/auth/logout", headers=headers)
  assert logout.status_code == 200

  me_after = client.get("/api/v1/auth/me")
  assert me_after.status_code == 401


def test_chat_with_session_cookie(client: TestClient) -> None:
  headers = _csrf_headers(client)
  client.post(
    "/api/v1/auth/register",
    json={"email": "bob@example.com", "password": "password123"},
    headers=headers,
  )
  headers = _csrf_headers(client)
  client.post(
    "/api/v1/auth/login",
    json={"email": "bob@example.com", "password": "password123"},
    headers=headers,
  )
  response = client.post("/api/v1/chat", json={"question": "hello"})
  assert response.status_code == 200
  assert "answer" in response.json()


def test_verify_email_and_password_reset(client: TestClient) -> None:
  headers = _csrf_headers(client)
  register = client.post(
    "/api/v1/auth/register",
    json={"email": "carol@example.com", "password": "password123"},
    headers=headers,
  )
  verify_token = register.json()["verification_token"]

  headers = _csrf_headers(client)
  verified = client.post(
    "/api/v1/auth/verify-email",
    json={"token": verify_token},
    headers=headers,
  )
  assert verified.status_code == 200
  assert verified.json()["user"]["email_verified"] is True

  headers = _csrf_headers(client)
  forgot = client.post(
    "/api/v1/auth/forgot-password",
    json={"email": "carol@example.com"},
    headers=headers,
  )
  assert forgot.status_code == 200
  reset_token = forgot.json()["reset_token"]

  headers = _csrf_headers(client)
  reset = client.post(
    "/api/v1/auth/reset-password",
    json={"token": reset_token, "password": "newpassword1"},
    headers=headers,
  )
  assert reset.status_code == 200

  headers = _csrf_headers(client)
  login = client.post(
    "/api/v1/auth/login",
    json={"email": "carol@example.com", "password": "newpassword1"},
    headers=headers,
  )
  assert login.status_code == 200


def test_oauth_providers_empty_without_config(client: TestClient, monkeypatch) -> None:
  monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
  monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")
  response = client.get("/api/v1/auth/oauth/providers")
  assert response.status_code == 200
  assert response.json()["providers"] == []


def test_dev_token_still_works_when_enabled(client: TestClient) -> None:
  response = client.post("/api/v1/auth/token")
  assert response.status_code == 200
  assert "access_token" in response.json()
