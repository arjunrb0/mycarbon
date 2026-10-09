import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import site_content


@pytest.mark.parametrize("url,ok", [
    ("", False),
    ("   ", False),
    ("https://youtu.be/abc123", True),
    ("https://www.youtube.com/watch?v=abc123", True),
    ("https://vimeo.com/12345", True),
    ("http://youtu.be/abc123", False),              # not https
    ("https://evil.example.com/video.mp4", False),  # not a video host
    ("javascript:alert(1)", False),
])
def test_only_https_youtube_or_vimeo_links_are_embedded(monkeypatch, url, ok):
    monkeypatch.setattr(site_content, "VIDEO_URL", url)
    assert (site_content.video_url() is not None) is ok


def test_editing_notes_are_stripped(tmp_path, monkeypatch):
    f = tmp_path / "about.md"
    f.write_text("<!-- private note\nover lines -->\nHello **world**.\n", encoding="utf-8")
    monkeypatch.setattr(site_content, "ABOUT_PATH", str(f))
    assert site_content.about_markdown() == "Hello **world**."


def test_missing_or_comment_only_write_up_is_hidden(tmp_path, monkeypatch):
    monkeypatch.setattr(site_content, "ABOUT_PATH", str(tmp_path / "nope.md"))
    assert site_content.about_markdown() is None
    f = tmp_path / "only_note.md"
    f.write_text("<!-- just a note -->", encoding="utf-8")
    monkeypatch.setattr(site_content, "ABOUT_PATH", str(f))
    assert site_content.about_markdown() is None


def test_shipped_write_up_has_no_draft_text():
    text = site_content.about_markdown()
    assert text and "DRAFT" not in text
