# Playnite Metacritic Feed

A scheduled GitHub Action that lists every game Metacritic has released in the
current year (the
[browse page](https://www.metacritic.com/browse/game/all/all/current-year/metascore/))
and resolves Steam App IDs where possible, for the Playnite Trending Source
extension. Titles without a Steam match remain in the feed with a null `appid`.

The feed is published at
`https://raw.githubusercontent.com/wikewi/playnite-metacritic-feed/refs/heads/main/metacritic_current_year.json`
and has the same `appid` field as the existing trending feed:

```json
[{"appid": 1245620, "title": "Elden Ring", "metascore": 96},
 {"appid": null, "title": "Example", "metascore": 80}]
```

The workflow runs daily at 02:30 UTC and can be started manually from the
Actions tab. It reads Metacritic's undocumented finder API (the site's own
public key), so it may break without notice. A run fails without touching the
feed when Metacritic returns incomplete or invalid results.

Titles are matched to Steam only when a Steam store app has exactly the same
name (ignoring case, punctuation, and ™/®). Games without a Steam page, or whose
Steam name differs, remain available for title matching. `steam_cache.json`
stores resolved matches to limit Steam requests; misses are retried each run.

Run the tests with `python -m unittest discover -s tests`.
