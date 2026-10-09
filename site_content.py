"""
Editable site content, kept out of the page code.

To add the demo video: upload it to YouTube (unlisted is fine), then paste the
link below, e.g. VIDEO_URL = "https://youtu.be/abc123". While it's empty the
home page simply leaves the video out, so the live site never shows a broken
or blank player. Video files themselves don't belong in the repo: Streamlit
Cloud downloads the whole repo on every deploy.

The "About this project" write-up lives in content/about_project.md.
"""

import os
import re
from urllib.parse import urlparse

VIDEO_URL = ""

ABOUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "content", "about_project.md")

_VIDEO_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
                "vimeo.com", "www.vimeo.com"}


def video_url():
    """The video link if it's a usable YouTube/Vimeo URL, otherwise None."""
    url = (VIDEO_URL or "").strip()
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in _VIDEO_HOSTS:
        return None
    return url


def about_markdown():
    """The project write-up, or None if the file is missing or empty."""
    try:
        with open(ABOUT_PATH, encoding="utf-8") as f:
            text = f.read().strip()
    except OSError:
        return None
    # Editing notes go in <!-- comments --> and must never reach the live site.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
    return text or None
