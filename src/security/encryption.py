"""Encryption at rest for student PII (N3).

Two pieces work together on any column that needs to be both encrypted
*and* searchable by exact value (like `Student.student_number`):

- `EncryptedString`: a SQLAlchemy column type that transparently
  encrypts on write and decrypts on read using Fernet (AES-128-CBC +
  HMAC, from the `cryptography` package). Application code just
  assigns/reads plain strings - the encryption is invisible above this
  layer.
- `blind_index()`: Fernet is deliberately non-deterministic (a random
  nonce means encrypting the same value twice gives different
  ciphertext), so an encrypted column can't be queried with
  `WHERE student_number = ?` or given a meaningful UNIQUE constraint.
  `blind_index()` produces a deterministic HMAC-SHA256 of the
  *normalised* value instead; that goes in a companion `..._hash`
  column that IS indexed/unique, and every lookup filters on the hash,
  never the encrypted column. See `Student.student_number_hash` in
  src/db/models.py.

Never encrypt something you also need a `LIKE` search or ordering over -
this pattern only supports exact-match lookups.
"""

from __future__ import annotations

import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from src.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedString(TypeDecorator):
    """A String column that is encrypted at rest with Fernet.

    Usage is exactly like `String(n)` - the ciphertext is base64 text,
    which is why `impl` is `String` rather than a binary type; give the
    column extra length headroom (ciphertext runs longer than
    plaintext) via the `length` argument.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken as exc:
            # A wrong/rotated ENCRYPTION_KEY should fail loudly, not
            # silently return garbage or None (N5: don't trust corrupted
            # data implicitly).
            raise ValueError(
                "Could not decrypt a stored value - ENCRYPTION_KEY may be "
                "wrong or has rotated without re-encrypting existing rows."
            ) from exc


def blind_index(value: str) -> str:
    """Deterministic HMAC-SHA256 of a normalised value, for exact-match
    lookups against an EncryptedString column. Not a secret by itself -
    it only needs to be unpredictable enough that someone with read
    access to the database can't trivially reverse it to the original
    student number, which HMAC with a server-side key provides.
    """
    key = get_settings().encryption_key
    key_bytes = key.encode() if isinstance(key, str) else key
    normalised = value.strip().upper()
    return hmac.new(key_bytes, normalised.encode(), hashlib.sha256).hexdigest()
