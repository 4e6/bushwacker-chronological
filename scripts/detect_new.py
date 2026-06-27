#!/usr/bin/env python3
"""
Detect channel uploads not yet classified in the repo. Reads the channel RSS
feed (no API key, no yt-dlp → not bot-blocked) and diffs against the known IDs
in bushwacker_playlist.txt + bushwacker_excluded.txt (the repo IS the state).

For each NEW id it enriches duration + description via the YouTube Data API
(reusing the YT_* OAuth secrets) — duration is decisive for SHORT vs episode
(a 65 s clip can have a full "(1378-1417)" episode title). If no creds are
present it still works, just without durations.

Outputs:
  • human summary to stdout
  • JSON list of new videos to $OUT_JSON (default /tmp/new_videos.json)
  • if $GITHUB_OUTPUT is set: has_new=true|false and count=N (for the workflow)

Env: CHANNEL_ID (default Bushwacker), OUT_JSON, YT_CLIENT_ID/SECRET/REFRESH_TOKEN
"""
import os
import re
import sys
import json
import html
import urllib.request
import urllib.parse
import urllib.error

CHANNEL_ID = os.environ.get("CHANNEL_ID", "UCGzfpg1YiBIlgcODQI4lDvQ")
OUT_JSON = os.environ.get("OUT_JSON", "/tmp/new_videos.json")
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_FILE = os.path.join(PROJ, "bushwacker_playlist.txt")
EXCLUDED_FILE = os.path.join(PROJ, "bushwacker_excluded.txt")
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"


def known_ids():
    ids = set()
    with open(PLAYLIST_FILE, encoding="utf-8") as f:
        for line in f:
            m = re.search(r"watch\?v=([A-Za-z0-9_-]{11})", line)
            if m:
                ids.add(m.group(1))
    if os.path.exists(EXCLUDED_FILE):
        with open(EXCLUDED_FILE, encoding="utf-8") as f:
            for line in f:
                if re.match(r"^\[(SHORT|META)\]", line):
                    parts = line.split()
                    if len(parts) >= 2:
                        ids.add(parts[1])
    return ids


def feed_entries():
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0 (playlist-sync)"})
    xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", e)
        tit = re.search(r"<title>([^<]*)</title>", e)
        pub = re.search(r"<published>([^<]+)</published>", e)
        if vid:
            out.append({
                "id": vid.group(1),
                "title": html.unescape(tit.group(1)).strip() if tit else "",
                "published": pub.group(1)[:10] if pub else "",
            })
    return out


def get_access_token():
    """Reuse the playlist-apply OAuth secrets for a read-only metadata call."""
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        return None
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=body, timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        print(f"  (token refresh failed: {e.code}; durations unavailable)")
        return None


def iso_to_seconds(s):
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s or "")
    if not m:
        return None
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def enrich(new):
    """Attach duration_s + description to each new video via the Data API."""
    if not new:
        return
    token = get_access_token()
    if not token:
        print("  (no YT_* creds — durations unavailable; classification relies on title only)")
        return
    ids = ",".join(e["id"] for e in new)
    url = ("https://www.googleapis.com/youtube/v3/videos"
           f"?part=contentDetails,snippet&id={ids}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        print(f"  (duration fetch failed: {e.code} {e.read().decode()[:200]})")
        return
    meta = {}
    for it in data.get("items", []):
        meta[it["id"]] = (
            iso_to_seconds(it.get("contentDetails", {}).get("duration")),
            (it.get("snippet", {}).get("description", "") or "")[:400],
        )
    for e in new:
        dur, desc = meta.get(e["id"], (None, ""))
        e["duration_s"] = dur
        e["description"] = desc


def main():
    known = known_ids()
    entries = feed_entries()
    new = [e for e in entries if e["id"] not in known]
    enrich(new)

    print(f"feed: {len(entries)} latest uploads | known: {len(known)} classified | NEW: {len(new)}")
    for e in new:
        d = e.get("duration_s")
        dtxt = f"{d}s" if d is not None else "?"
        print(f"  NEW  {e['id']} | {e['published']} | {dtxt:>6} | {e['title']}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)

    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"has_new={'true' if new else 'false'}\n")
            f.write(f"count={len(new)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
