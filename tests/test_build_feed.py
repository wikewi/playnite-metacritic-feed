import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_feed


def finder_page(total, titles):
    return {"data": {"totalResults": total, "items": [
        {"title": title, "slug": title.lower(), "criticScoreSummary": {"score": 80}} for title in titles
    ]}}


class BuildFeedTests(unittest.TestCase):
    def test_normalize_ignores_case_symbols_and_punctuation(self):
        self.assertEqual(build_feed.normalize("Marvel's Spider-Man™: Remastered"), "marvel s spider man remastered")
        self.assertEqual(build_feed.normalize("Dungeons & Dragons"), build_feed.normalize("DUNGEONS AND DRAGONS"))

    def test_finder_is_paged_until_total_is_reached(self):
        pages = [finder_page(26, ["G%d" % i for i in range(24)]), finder_page(26, ["A", "B"])]
        urls = []

        def fetch(url):
            urls.append(url)
            return pages[len(urls) - 1]

        games = build_feed.fetch_metacritic_games(2026, fetch)
        self.assertEqual(len(games), 26)
        self.assertIn("offset=24", urls[1])
        self.assertIn("releaseYearMin=2026", urls[0])

    def test_truncated_finder_result_is_rejected(self):
        with self.assertRaises(RuntimeError):
            build_feed.fetch_metacritic_games(2026, lambda url: finder_page(100, ["Only one"]))

    def test_steam_match_requires_exact_normalized_app_name(self):
        results = {"items": [
            {"type": "app", "name": "Elden Ring: Shadow of the Erdtree", "id": 2778580},
            {"type": "dlc", "name": "Elden Ring", "id": 1},
            {"type": "app", "name": "ELDEN RING™", "id": 1245620},
        ]}
        self.assertEqual(build_feed.resolve_steam_app_id("Elden Ring", lambda url: results), 1245620)
        self.assertIsNone(build_feed.resolve_steam_app_id("Elden", lambda url: results))

    def test_feed_drops_unmatched_games_dedupes_and_uses_cache(self):
        games = [
            {"title": "Known", "slug": "k", "metascore": 90},
            {"title": "Unknown", "slug": "u", "metascore": 80},
            {"title": "Known Again", "slug": "k2", "metascore": 70},
        ]
        calls = []
        ids = {"Known": 5, "Unknown": None, "Known Again": 5}
        cache = {"known": 5}
        feed = build_feed.build_feed(games, cache, lambda title: calls.append(title) or ids[title])
        self.assertEqual(calls, ["Unknown", "Known Again"])
        self.assertEqual([entry["appid"] for entry in feed], [5])
        self.assertEqual(feed[0]["title"], "Known")


if __name__ == "__main__":
    unittest.main()
