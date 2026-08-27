"""MIME parsing for inbound mail.

Uses the standard library `email` package. This is deliberate: `BytesParser` with
`policy.default` handles multipart nesting, transfer encodings and charsets correctly,
and it is maintained under Python's security release process. A third-party parser here
would add CVE surface on our most-exposed input path in exchange for nothing.

See docs/TECH_STACK.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime


@dataclass(slots=True)
class ParsedAttachment:
    filename: str
    content_type: str
    size_bytes: int


@dataclass(slots=True)
class ParsedEmail:
    sender: str
    recipients: list[str]
    subject: str
    text_body: str
    html_body: str | None
    received_at: datetime
    attachments: list[ParsedAttachment] = field(default_factory=list)


def parse(raw: bytes) -> ParsedEmail:
    """Parse a raw RFC 5322 message.

    The parser is lenient by design — real mail is malformed constantly and a temp-mail
    service that rejects imperfect messages fails at its one job.
    """
    msg: EmailMessage = BytesParser(policy=policy.default).parsebytes(raw)

    text_body = ""
    html_body: str | None = None
    attachments: list[ParsedAttachment] = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = part.get_content_disposition()
            content_type = part.get_content_type()

            if disposition == "attachment":
                payload = part.get_payload(decode=True) or b""
                attachments.append(
                    ParsedAttachment(
                        filename=part.get_filename() or "unnamed",
                        content_type=content_type,
                        size_bytes=len(payload),
                    )
                )
            elif content_type == "text/plain" and not text_body:
                text_body = _decode(part)
            elif content_type == "text/html" and html_body is None:
                html_body = _decode(part)
    else:
        if msg.get_content_type() == "text/html":
            html_body = _decode(msg)
        else:
            text_body = _decode(msg)

    return ParsedEmail(
        sender=str(msg.get("From", "")),
        recipients=[str(r) for r in msg.get_all("To", [])],
        subject=str(msg.get("Subject", "(no subject)")),
        text_body=text_body,
        html_body=html_body,
        received_at=_received_at(msg),
        attachments=attachments,
    )


def _decode(part: EmailMessage) -> str:
    """Decode a part to text, tolerating a wrong or missing charset."""
    payload = part.get_payload(decode=True)
    # get_payload is typed as a union; a non-bytes result means this part carries no
    # decodable content, which for our purposes is the same as empty.
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        # Charset the sender named does not exist. Fall back rather than drop the mail.
        return payload.decode("utf-8", errors="replace")


def _received_at(msg: EmailMessage) -> datetime:
    raw_date = msg.get("Date")
    if raw_date:
        try:
            return parsedate_to_datetime(str(raw_date))
        except (TypeError, ValueError):
            pass
    return datetime.now(UTC)
