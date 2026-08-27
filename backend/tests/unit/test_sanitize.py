"""Sanitizer tests — these guard docs/SECURITY.md section 1.

If one of these fails, do not adjust the test. Fix the sanitizer.
"""

from app.services.sanitize import sanitize_email_html, strip_remote_images


def test_strips_script_tags() -> None:
    assert "<script>" not in sanitize_email_html("<p>hi</p><script>alert(1)</script>")


def test_strips_event_handlers() -> None:
    assert "onerror" not in sanitize_email_html('<img src="x" onerror="alert(1)">')


def test_strips_javascript_urls() -> None:
    assert "javascript:" not in sanitize_email_html('<a href="javascript:alert(1)">x</a>')


def test_strips_data_urls() -> None:
    # SVG data URLs can carry script.
    result = sanitize_email_html('<img src="data:image/svg+xml;base64,PHN2Zz4=">')
    assert "data:" not in result


def test_strips_iframes_and_forms() -> None:
    result = sanitize_email_html('<iframe src="//evil"></iframe><form action="//evil"></form>')
    assert "<iframe" not in result
    assert "<form" not in result


def test_keeps_safe_formatting() -> None:
    result = sanitize_email_html("<p>Hello <strong>world</strong></p>")
    assert "<strong>" in result


def test_adds_noopener_to_links() -> None:
    assert "noopener" in sanitize_email_html('<a href="https://example.com">x</a>')


def test_strip_remote_images_removes_tracking_pixels() -> None:
    assert "<img" not in strip_remote_images('<p>hi</p><img src="https://track.example/p.gif">')
