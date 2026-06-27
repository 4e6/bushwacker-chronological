#!/usr/bin/env python3
"""
Deterministic YouTube playlist sync — make the LIVE playlist match
bushwacker_playlist.txt (the source of truth). Adds any videos that are in the
file but missing from the playlist, each at its correct chronological position.

NO LLM. Stdlib only (no pip install needed in CI). Safe by default: dry-run
unless APPLY=1. Never auto-removes anything — it only reports extras/dupes.

Env:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (required)
  PLAYLIST_ID    default PLVw98VIsFGF8
  APPLY=1        actually insert (default: dry-run, read-only)

Local dry-run:
  YT_CLIENT_ID=... YT_CLIENT_SECRET=... YT_REFRESH_TOKEN=... \
    python3 scripts/yt_playlist_sync.py
"""
import os
import re
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

PLAYLIST_ID = os.environ.get("PLAYLIST_ID", "PLVw98VIsFGF8")
APPLY = os.environ.get("APPLY") == "1"
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_FILE = os.path.join(PROJ, "bushwacker_playlist.txt")


def die(msg):
    sys.exit(f"error: {msg}")


def get_access_token():
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.environ.get(k):
            die(f"missing env var {k}")
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    try:
        with urllib.request.urlopen(
            "https://oauth2.googleapis.com/token", data=body, timeout=30
        ) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        die(f"token refresh failed: {e.code} {e.read().decode()[:300]}")


def api(token, path, params=None, method="GET", body=None):
    url = f"https://www.googleapis.com/youtube/v3/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        die(f"{method} {path} -> {e.code} {e.read().decode()[:400]}")


def desired_order():
    """Video IDs in file (chronological) order — the source of truth."""
    ids = []
    with open(PLAYLIST_FILE, encoding="utf-8") as f:
        for line in f:
            m = re.search(r"watch\?v=([A-Za-z0-9_-]{11})", line)
            if m:
                ids.append(m.group(1))
    if not ids:
        die("parsed 0 video ids from the playlist file")
    if len(set(ids)) != len(ids):
        die("playlist file contains duplicate video ids")
    return ids


def live_items(token):
    """(videoId, playlistItemId) in current playlist order; paginates past 100."""
    items = []
    params = {"part": "snippet", "playlistId": PLAYLIST_ID, "maxResults": 50}
    while True:
        j = api(token, "playlistItems", params)
        for it in j.get("items", []):
            rid = it["snippet"]["resourceId"]
            if rid.get("kind") == "youtube#video":
                items.append((rid["videoId"], it["id"]))
        tok = j.get("nextPageToken")
        if not tok:
            break
        params["pageToken"] = tok
    return items


def main():
    token = get_access_token()
    print("OK  access token refreshed")

    desired = desired_order()
    desired_idx = {v: i for i, v in enumerate(desired)}
    live = live_items(token)
    live_ids = [v for v, _ in live]
    live_set = set(live_ids)

    to_add = [v for v in desired if v not in live_set]
    extra = sorted({v for v in live_ids if v not in desired_idx})
    dupes = sorted({v for v in live_ids if live_ids.count(v) > 1})

    print(f"file: {len(desired)} videos | live: {len(live)} items | "
          f"to add: {len(to_add)} | not-in-file: {len(extra)} | dupes: {len(dupes)}")
    if extra:
        print("  ! on playlist but NOT in file (not auto-removed):", ", ".join(extra[:10]))
    if dupes:
        print("  ! duplicate playlist entries (not auto-removed):", ", ".join(dupes[:10]))

    if not to_add:
        common = [v for v in live_ids if v in desired_idx]
        order_ok = common == [v for v in desired if v in live_set]
        print("nothing to add — playlist matches the file")
        print("order matches file" if order_ok else "  ! live order differs from file (review)")
        return

    # Insert each missing video at its slot. Process in file order so multi-adds
    # land correctly; position = count of curated videos already present that
    # sort before it.
    present = {v for v in live_ids if v in desired_idx}
    for vid in to_add:
        pos = sum(1 for d in present if desired_idx[d] < desired_idx[vid])
        if APPLY:
            api(token, "playlistItems", params={"part": "snippet"}, method="POST", body={
                "snippet": {
                    "playlistId": PLAYLIST_ID,
                    "position": pos,
                    "resourceId": {"kind": "youtube#video", "videoId": vid},
                }
            })
            print(f"  + inserted {vid} at position {pos}")
        else:
            print(f"  [dry-run] would insert {vid} at position {pos}")
        present.add(vid)

    print("done" if APPLY else "dry-run only — set APPLY=1 to actually write")


if __name__ == "__main__":
    main()
