"""Offline authentication tests: ephemeral RSA keys, no Azure or database calls."""

import secrets
import sys
import time
import unittest
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from security.identity import (  # noqa: E402
    AuthSettings,
    EntraTokenVerifier,
    Principal,
    create_current_user_dependency,
)


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = AuthSettings.load()
        # Private signing keys are generated in memory and never saved/logged.
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.verifier = EntraTokenVerifier(
            self.settings, key_provider=lambda token: self.key.public_key()
        )

    def claims(self, **changes):
        now = int(time.time())
        claims = {
            "iss": self.settings.issuer,
            "aud": self.settings.api_client_id,
            "tid": self.settings.tenant_id,
            "oid": str(uuid4()),
            "azp": self.settings.swagger_client_id,
            "ver": "2.0",
            "iat": now,
            "nbf": now - 1,
            "exp": now + 300,
            "scp": "access_as_user",
        }
        claims.update(changes)
        return claims

    def sign(self, claims, key=None):
        return jwt.encode(
            claims, key or self.key, algorithm="RS256", headers={"kid": "offline-test"}
        )

    def rejected(self, claims, code=401):
        token = self.sign(claims)
        with self.assertRaises(HTTPException) as result:
            self.verifier.verify(token)
        self.assertEqual(result.exception.status_code, code)
        self.assertNotIn(token, result.exception.detail)

    def test_valid_user(self):
        claims = self.claims()
        self.assertEqual(
            self.verifier.verify(self.sign(claims)),
            Principal(self.settings.tenant_id, claims["oid"]),
        )

    def test_two_users_have_distinct_verified_principals(self):
        a, b = self.claims(), self.claims()
        self.assertNotEqual(
            self.verifier.verify(self.sign(a)), self.verifier.verify(self.sign(b))
        )

    def test_expired(self):
        self.rejected(self.claims(exp=int(time.time()) - 120))

    def test_not_yet_valid(self):
        self.rejected(self.claims(nbf=int(time.time()) + 120))

    def test_future_issue_time(self):
        self.rejected(self.claims(iat=int(time.time()) + 120))

    def test_wrong_audience(self):
        self.rejected(self.claims(aud=str(uuid4())))

    def test_multiple_audiences_rejected(self):
        self.rejected(self.claims(aud=[self.settings.api_client_id, str(uuid4())]))

    def test_wrong_issuer(self):
        self.rejected(self.claims(iss="https://example.invalid/v2.0"))

    def test_wrong_tenant_even_with_expected_issuer(self):
        self.rejected(self.claims(tid=str(uuid4())))

    def test_missing_required_claims(self):
        for claim in ("exp", "iat", "nbf", "iss", "aud", "tid", "oid", "ver", "azp"):
            with self.subTest(claim=claim):
                claims = self.claims()
                del claims[claim]
                self.rejected(claims)

    def test_invalid_user_identifier(self):
        for value in ("not-a-uuid", None, [], {}):
            with self.subTest(value=type(value).__name__):
                self.rejected(self.claims(oid=value))

    def test_missing_or_incorrect_delegated_scope(self):
        for value in (None, "", "other_scope", ["access_as_user"]):
            with self.subTest(value=type(value).__name__):
                self.rejected(self.claims(scp=value), code=403)

    def test_application_identity_rejected(self):
        self.rejected(self.claims(idtyp="app"), code=403)

    def test_unapproved_client_rejected(self):
        self.rejected(self.claims(azp=str(uuid4())), code=403)

    def test_wrong_token_version(self):
        self.rejected(self.claims(ver="1.0"))

    def test_forged_signature(self):
        with self.assertRaises(HTTPException) as result:
            self.verifier.verify(self.sign(self.claims(), self.other_key))
        self.assertEqual(result.exception.status_code, 401)

    def test_disallowed_algorithms(self):
        for algorithm, key in (("none", None), ("HS256", secrets.token_bytes(32))):
            with self.subTest(algorithm=algorithm):
                token = jwt.encode(
                    self.claims(), key, algorithm=algorithm, headers={"kid": "offline-test"}
                )
                with self.assertRaises(HTTPException) as result:
                    self.verifier.verify(token)
                self.assertEqual(result.exception.status_code, 401)

    def test_malformed_and_oversized_input(self):
        for token in ("not-a-token", "x" * 16_385):
            with self.subTest(length=len(token)):
                with self.assertRaises(HTTPException) as result:
                    self.verifier.verify(token)
                self.assertEqual(result.exception.status_code, 401)

    def test_identity_provider_unavailable_is_sanitized(self):
        def offline(token):
            raise PyJWKClientConnectionError("synthetic internal transport detail")

        verifier = EntraTokenVerifier(self.settings, key_provider=offline)
        token = self.sign(self.claims())
        with self.assertRaises(HTTPException) as result:
            verifier.verify(token)
        self.assertEqual(result.exception.status_code, 503)
        self.assertNotIn("transport detail", result.exception.detail)
        self.assertNotIn(token, result.exception.detail)

    def client(self):
        app = FastAPI()
        current_user = create_current_user_dependency(self.settings, self.verifier)

        @app.get("/whoami")
        def whoami(user: Principal = Depends(current_user)):
            return {"tenant_id": user.tenant_id, "object_id": user.object_id}

        return TestClient(app)

    def test_http_requires_bearer_authentication(self):
        with self.client() as client:
            response = client.get("/whoami")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_http_accepts_verified_identity(self):
        claims = self.claims()
        with self.client() as client:
            response = client.get(
                "/whoami", headers={"Authorization": "Bearer " + self.sign(claims)}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["object_id"], claims["oid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
