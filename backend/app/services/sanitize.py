"""HTML sanitizing for untrusted email content.

This is HALF the defence. The other half is rendering the result inside a sandboxed
iframe on a SEPARATE ORIGIN. Never rely on either alone — see docs/SECURITY.md section 1.

nh3 (Rust `ammonia` bindings). Do NOT substitute `bleach`: it is archived and deprecated.
"""

import nh3

# Deliberately narrow. Anything not listed is stripped.
ALLOWED_TAGS: set[str] = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "caption",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}

ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}

# Note the omissions: no `javascript:`, no `data:` (SVG data URLs can carry script).
ALLOWED_SCHEMES: set[str] = {"http", "https", "mailto"}


def sanitize_email_html(raw_html: str) -> str:
    """Strip everything that could execute, exfiltrate, or phish.

    Removes: <script>, <style>, <iframe>, <object>, <embed>, <form>, all on* handlers,
    and javascript:/data: URLs.
    """
    return nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )


def strip_remote_images(html: str) -> str:
    """Neutralise tracking pixels by default.

    Loading remote images leaks the user's IP and confirms the address is live. For a
    privacy tool that is a product failure, not a minor leak. The UI offers an explicit
    "load images" affordance; when used, images are proxied server-side.
    """
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS - {"img"},
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )
