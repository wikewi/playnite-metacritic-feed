import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Public key embedded in every metacritic.com page.
METACRITIC_API_KEY = "1MOZgmNFxvmljaQR1X9KAij9Mo4xAY3u"
FINDER_URL = "https://backend.metacritic.com/finder/metacritic/web"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
PAGE_SIZE = 24
FEED_PATH = "metacritic_current_year.json"
CACHE_PATH = "steam_cache.json"
USER_AGENT = "Mozilla/5.0 (compatible; playnite-metacritic-feed)"


def get_json(url, retries=4):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 2)


def normalize(title):
    title = re.sub(r"[™®©]", "", title or "").casefold().replace("&", " and ")
    return re.sub(r"[^0-9a-z]+", " ", title).strip()


def fetch_metacritic_games(year, fetch=get_json):
    games = []
    offset = 0
    total = None
    while total is None or offset < total:
        query = urllib.parse.urlencode({
            "sortBy": "-metaScore", "mcoTypeId": 13, "releaseYearMin": year, "releaseYearMax": year,
            "offset": offset, "limit": PAGE_SIZE, "componentName": "finder",
            "componentType": "Finder", "apiKey": METACRITIC_API_KEY,
        })
        data = fetch(FINDER_URL + "?" + query)["data"]
        total = int(data["totalResults"])
        items = data["items"]
        if not items:
            break
        for item in items:
            title = (item.get("title") or "").strip()
            if title:
                score = (item.get("criticScoreSummary") or {}).get("score")
                games.append({"title": title, "slug": item.get("slug") or "", "metascore": score})
        offset += PAGE_SIZE
    if total is None or len(games) < total * 0.9:
        raise RuntimeError("Metacritic returned %d of %s expected games." % (len(games), total))
    return games


def resolve_steam_app_id(title, fetch=get_json):
    query = urllib.parse.urlencode({"term": title, "cc": "us", "l": "en"})
    wanted = normalize(title)
    for item in fetch(STEAM_SEARCH_URL + "?" + query).get("items", []):
        if item.get("type") == "app" and normalize(item.get("name")) == wanted:
            return int(item["id"])
    return None


def build_feed(games, cache, resolve=resolve_steam_app_id, delay=0.0):
    feed = []
    for game in games:
        key = normalize(game["title"])
        if key not in cache:
            cache[key] = resolve(game["title"])
            time.sleep(delay)
        if cache[key]:
            feed.append({"appid": cache[key], "title": game["title"], "metascore": game["metascore"]})
    unique = {}
    for entry in feed:
        unique.setdefault(entry["appid"], entry)
    return sorted(unique.values(), key=lambda entry: entry["appid"])


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default


def write_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)
        file.write("\n")


def main():
    year = int(os.environ.get("FEED_YEAR") or datetime.now(timezone.utc).year)
    games = fetch_metacritic_games(year)
    cache = read_json(CACHE_PATH, {})
    # Misses are retried on every run so newly listed Steam pages are picked up.
    cache = {key: value for key, value in cache.items() if value}
    feed = build_feed(games, cache, delay=0.3)
    if not feed:
        raise RuntimeError("No Metacritic games could be matched to Steam App IDs; feed not updated.")
    write_json(CACHE_PATH, cache)
    write_json(FEED_PATH, feed)
    print("Metacritic games: %d. Matched to Steam: %d." % (len(games), len(feed)))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Feed build failed: %s" % error, file=sys.stderr)
        sys.exit(1)
