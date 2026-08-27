"""Address generation tests — these guard docs/SECURITY.md section 2."""

import pytest

from app.services.addresses import (
    generate_local_part,
    hash_token,
    issue_possession_token,
    verify_token,
)

SECRET = "test-secret-key"


def test_rejects_insufficient_entropy() -> None:
    with pytest.raises(ValueError, match="at least 8 bytes"):
        generate_local_part(4)


def test_addresses_are_unique() -> None:
    generated = {generate_local_part(12) for _ in range(1000)}
    assert len(generated) == 1000


def test_addresses_are_not_sequential() -> None:
    """Consecutive addresses must not share a predictable prefix.

    A counter or timestamp source would leak the whole namespace from one sample.
    """
    samples = [generate_local_part(12) for _ in range(50)]
    assert len({s[:6] for s in samples}) == 50


def test_token_roundtrip() -> None:
    token = issue_possession_token()
    assert verify_token(token, hash_token(token, SECRET), SECRET)


def test_wrong_token_rejected() -> None:
    stored = hash_token(issue_possession_token(), SECRET)
    assert not verify_token(issue_possession_token(), stored, SECRET)
