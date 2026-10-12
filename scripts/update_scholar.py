#!/usr/bin/env python3
"""Refresh the latest ten Google Scholar publications, retaining cache on failure."""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


PROFILE_URL = "https://scholar.google.co.jp/citations?user=uDFb6OcAAAAJ&hl=en&sortby=pubdate"
CACHE_PATH = Path(__file__).resolve().parents[1] / "_data/scholar_publications.json"


class Element:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def find_all(self, class_name):
        for child in self.children:
            if isinstance(child, Element):
                if class_name in child.attrs.get("class", "").split():
                    yield child
                yield from child.find_all(class_name)

    def text(self):
        return "".join(child.text() if isinstance(child, Element) else child
                       for child in self.children)


class ScholarParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in self.VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def clean(element):
    return " ".join(element.text().split()) if element else ""


def parse_publications(html):
    parser = ScholarParser()
    parser.feed(html)
    publications = []
    seen = set()
    for row in parser.root.find_all("gsc_a_tr"):
        title = next(row.find_all("gsc_a_at"), None)
        if title is None or not clean(title):
            continue
        url = urljoin(PROFILE_URL, title.attrs.get("href", ""))
        if urlparse(url).hostname != "scholar.google.co.jp" or "citation_for_view=" not in url:
            raise ValueError("Unexpected publication URL in Scholar response")
        if url in seen:
            continue
        seen.add(url)
        details = list(row.find_all("gs_gray"))
        year = next(row.find_all("gsc_a_h"), None)
        publications.append({
            "title": clean(title),
            "url": url,
            "authors": clean(details[0]) if details else "",
            "venue": clean(details[1]) if len(details) > 1 else "",
            "year": clean(year),
        })
        if len(publications) == 10:
            break
    if not publications:
        raise ValueError("Scholar returned no publications (possibly a CAPTCHA or changed markup)")
    return publications


def refresh(cache_path=CACHE_PATH, html=None):
    if html is None:
        request = Request(PROFILE_URL + "&pagesize=20", headers={
            "User-Agent": "Mozilla/5.0 (compatible; PersonalSitePublications/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
    # Parse successfully before touching the last known good data.
    publications = parse_publications(html)
    data = {
        "profile_url": PROFILE_URL,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "publications": publications,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(cache_path)
    return len(publications)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, help="Import a saved Scholar profile page sorted by date")
    args = parser.parse_args()
    try:
        html = args.html.read_text(encoding="utf-8") if args.html else None
        count = refresh(html=html)
    except Exception as error:
        print(f"Scholar refresh failed; existing cache retained: {error}", file=sys.stderr)
        return 1
    print(f"Updated {count} publications in {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
