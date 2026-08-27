"""Inbox address generation and possession tokens.

Address enumeration is the classic breach in this product category: public catch-all
domains mean anyone who can guess an address can read the OTPs that land in it.

Two controls, and both are required:
  1. Enough entropy that guessing is infeasible.
  2. A possession token, so knowing the address is not sufficient to read it.

See docs/SECURITY.md section 2.
"""

import hmac
import secrets
from hashlib import sha256

# secrets, never random — `random` is not a CSPRNG and is seeded predictably.
_ALPHABET_NOTE = "token_urlsafe gives ~1.3 chars per byte of entropy"


def generate_local_part(entropy_bytes: int) -> str:
    """Generate the local part of an inbox address.

    Args:
        entropy_bytes: Must be >= 8 (64 bits). Enforced by Settings.
    """
    if entropy_bytes < 8:
        raise ValueError("address entropy must be at least 8 bytes (64 bits)")
    return secrets.token_urlsafe(entropy_bytes).lower().replace("_", "").replace("-", "")


def issue_possession_token() -> str:
    """Token handed to the creator of an inbox. Required to read it."""
    return secrets.token_urlsafe(32)


def hash_token(token: str, secret_key: str) -> str:
    """Store only the hash. A leaked database must not yield readable inboxes."""
    return hmac.new(secret_key.encode(), token.encode(), sha256).hexdigest()


def verify_token(token: str, token_hash: str, secret_key: str) -> bool:
    """Constant-time comparison — never use `==` on secrets."""
    return hmac.compare_digest(hash_token(token, secret_key), token_hash)
