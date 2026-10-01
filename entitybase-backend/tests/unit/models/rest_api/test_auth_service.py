"""Unit tests for the auth service (hashing and tokens)."""

import pytest

from models.rest_api.entitybase.v1.services.auth_service import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


SECRET = "unit-test-secret"


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self) -> None:
        stored = hash_password("correct horse battery staple")
        assert stored.startswith("scrypt$")
        assert verify_password("correct horse battery staple", stored)
        assert not verify_password("wrong", stored)

    def test_hashes_are_salted(self) -> None:
        assert hash_password("same") != hash_password("same")

    def test_verify_rejects_malformed_stored_hash(self) -> None:
        assert not verify_password("pw", "not-a-hash")
        assert not verify_password("pw", "md5$aa$bb")
        assert not verify_password("pw", "")
        assert not verify_password("", "scrypt$aa$bb")


class TestTokens:
    def test_create_and_decode_roundtrip(self) -> None:
        token = create_token(90001, "alice", SECRET, 1)
        payload = decode_token(token, SECRET)
        assert payload.user_id == 90001
        assert payload.username == "alice"

    def test_decode_rejects_tampered_token(self) -> None:
        token = create_token(90001, "alice", SECRET, 1)
        header, body, _sig = token.split(".")
        forged = f"{header}.{body}.AAAA"
        with pytest.raises(ValueError):
            decode_token(forged, SECRET)

    def test_decode_rejects_wrong_secret(self) -> None:
        token = create_token(90001, "alice", SECRET, 1)
        with pytest.raises(ValueError):
            decode_token(token, "other-secret")

    def test_decode_rejects_expired_token(self) -> None:
        token = create_token(90001, "alice", SECRET, 0)
        # expiry_hours=0 means exp is now; decode fails within a second
        with pytest.raises(ValueError, match="expired"):
            decode_token(token, SECRET)

    def test_decode_rejects_malformed_token(self) -> None:
        with pytest.raises(ValueError):
            decode_token("garbage", SECRET)

    def test_create_requires_secret(self) -> None:
        with pytest.raises(ValueError):
            create_token(1, "alice", "", 1)

    def test_decode_requires_secret(self) -> None:
        token = create_token(1, "alice", SECRET, 1)
        with pytest.raises(ValueError):
            decode_token(token, "")
