import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("IQBTS_SECRET_KEY", "testing-secret")

from src.servicios.api import _active_sessions, app
from src.servicios.iqoption_auth import IQOptionAuthResult


class APILoginTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        _active_sessions.clear()

    def tearDown(self):
        _active_sessions.clear()

    def test_login_success(self):
        with patch("src.servicios.api.authenticate") as mock_auth:
            mock_client = MagicMock()
            mock_auth.return_value = IQOptionAuthResult(True, "success", mock_client)

            response = self.client.post(
                "/login",
                json={"username": "user@example.com", "password": "secret"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("token", payload)
        self.assertEqual(payload["message"], "Login successful")
        mock_auth.assert_called_once_with("user@example.com", "secret")
        self.assertIs(_active_sessions["user@example.com"], mock_client)

    def test_login_invalid_credentials(self):
        with patch("src.servicios.api.authenticate") as mock_auth:
            mock_auth.return_value = IQOptionAuthResult(False, "Invalid login", None)

            response = self.client.post(
                "/login",
                json={"username": "user@example.com", "password": "bad"},
            )

        self.assertEqual(response.status_code, 401)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Invalid credentials")
        self.assertEqual(payload["reason"], "Invalid login")
        mock_auth.assert_called_once_with("user@example.com", "bad")
        self.assertNotIn("user@example.com", _active_sessions)

    def test_login_missing_fields_returns_bad_request(self):
        response = self.client.post(
            "/login", json={"username": "user@example.com"}
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Username and password required")

    def test_protected_route_requires_token(self):
        response = self.client.get("/protected")

        self.assertEqual(response.status_code, 401)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Token is missing")

    def test_protected_route_with_valid_token(self):
        with patch("src.servicios.api.authenticate") as mock_auth:
            mock_client = MagicMock()
            mock_auth.return_value = IQOptionAuthResult(True, "success", mock_client)

            login_response = self.client.post(
                "/login",
                json={"username": "user@example.com", "password": "secret"},
            )

        token = login_response.get_json()["token"]
        response = self.client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Hello user@example.com")
        self.assertTrue(payload["iqoption_session_active"])

    def test_logout_clears_session_and_closes_client(self):
        with patch("src.servicios.api.authenticate") as mock_auth:
            mock_client = MagicMock()
            mock_auth.return_value = IQOptionAuthResult(True, "success", mock_client)

            login_response = self.client.post(
                "/login",
                json={"username": "user@example.com", "password": "secret"},
            )

        token = login_response.get_json()["token"]
        response = self.client.post(
            "/logout", headers={"Authorization": f"Bearer {token}"}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Logout successful")
        self.assertTrue(payload["session_cleared"])
        self.assertNotIn("user@example.com", _active_sessions)
        mock_client.close.assert_called_once()

    def test_login_replaces_existing_session_closing_previous(self):
        with patch("src.servicios.api.authenticate") as mock_auth:
            first_client = MagicMock()
            second_client = MagicMock()
            mock_auth.side_effect = [
                IQOptionAuthResult(True, "success", first_client),
                IQOptionAuthResult(True, "success", second_client),
            ]

            first_response = self.client.post(
                "/login",
                json={"username": "user@example.com", "password": "secret"},
            )
            second_response = self.client.post(
                "/login",
                json={"username": "user@example.com", "password": "secret"},
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        first_client.close.assert_called_once()
        self.assertIs(_active_sessions["user@example.com"], second_client)
        self.assertEqual(mock_auth.call_count, 2)


if __name__ == "__main__":
    unittest.main()
