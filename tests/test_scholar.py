import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.update_scholar import parse_publications, refresh


def row(index, year="2026"):
    return f'''<tr class="gsc_a_tr"><td class="gsc_a_t">
      <a class="gsc_a_at" href="/citations?view_op=view_citation&amp;user=uDFb6OcAAAAJ&amp;citation_for_view=uDFb6OcAAAAJ:{index}">Paper <em>{index}</em> &amp; AI</a>
      <div class="gs_gray">G Ros, A Author</div>
      <div class="gs_gray">Conference <span>2026</span></div></td>
      <td class="gsc_a_c"><a>42</a></td>
      <td class="gsc_a_y"><span class="gsc_a_h">{year}</span></td></tr>'''


class ScholarTests(unittest.TestCase):
    def test_latest_ten_preserve_scholar_order_and_fields(self):
        publications = parse_publications("<table>" + "".join(row(i) for i in range(20)) + "</table>")
        self.assertEqual(len(publications), 10)
        self.assertEqual(publications[0]["title"], "Paper 0 & AI")
        self.assertEqual(publications[-1]["title"], "Paper 9 & AI")
        self.assertEqual(publications[0]["authors"], "G Ros, A Author")
        self.assertEqual(publications[0]["venue"], "Conference 2026")
        self.assertEqual(publications[0]["year"], "2026")
        self.assertIn("citation_for_view=uDFb6OcAAAAJ:0", publications[0]["url"])

    def test_duplicates_and_missing_year(self):
        publications = parse_publications(row(0, "") + row(0) + row(1))
        self.assertEqual(len(publications), 2)
        self.assertEqual(publications[0]["year"], "")

    def test_untrusted_link_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_publications(row(0).replace("/citations?", "https://example.com/citations?"))

    def test_successful_refresh_writes_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "publications.json"
            self.assertEqual(refresh(cache, html=row(0)), 1)
            data = json.loads(cache.read_text())
            self.assertEqual(data["publications"][0]["title"], "Paper 0 & AI")
            self.assertTrue(data["updated_at"])

    def test_captcha_preserves_existing_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "publications.json"
            cache.write_text('{"publications": [{"title": "Cached paper"}]}')
            original = cache.read_bytes()
            with self.assertRaises(ValueError):
                refresh(cache, html="<html><p>Verify you are human</p></html>")
            self.assertEqual(cache.read_bytes(), original)

    def test_http_failure_preserves_existing_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "publications.json"
            cache.write_text('{"publications": [{"title": "Cached paper"}]}')
            original = cache.read_bytes()
            with patch("scripts.update_scholar.urlopen", side_effect=HTTPError("url", 429, "Too Many Requests", {}, None)):
                with self.assertRaises(HTTPError):
                    refresh(cache)
            self.assertEqual(cache.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
