#!/usr/bin/env python3
"""
One-time helper: mint a YouTube OAuth **refresh token** for the playlist-sync
automation. Run this LOCALLY, once. Nothing is written to disk and no secret
file goes into the repo — you paste your Desktop OAuth client id/secret at the
prompt, approve in the browser, and it prints the 3 values to copy into GitHub.

Prereqs (one time, in Google Cloud Console — see below):
  • A project with **YouTube Data API v3** enabled.
  • OAuth consent screen published to **In production**, scope
    https://www.googleapis.com/auth/youtube
  • An OAuth client of type **Desktop app**  → gives Client ID + Client secret.

Install + run:
  python3 -m venv /tmp/ytauth && source /tmp/ytauth/bin/activate
  pip install google-auth-oauthlib
  python scripts/mint_youtube_token.py

A browser opens → sign in as the **playlist-owner** account → Approve.
If you see "Google hasn't verified this app": Advanced → Go to … (unsafe).
"""
import sys
import json
import urllib.request

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    sys.exit("Missing dependency. Run:  pip install google-auth-oauthlib")

# Manage playlists on the authenticated account (enough for playlistItems.insert).
SCOPES = ["https://www.googleapis.com/auth/youtube"]

print("Paste your OAuth *Desktop app* credentials")
print("(Cloud Console → APIs & Services → Credentials → your OAuth client):\n")
client_id = input("  Client ID:     ").strip()
client_secret = input("  Client secret: ").strip()
if not client_id or not client_secret:
    sys.exit("Both Client ID and Client secret are required.")

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
print("\nOpening a browser to approve access … (sign in as the playlist owner)\n")
# access_type=offline + prompt=consent guarantee a refresh_token every run.
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

if not creds.refresh_token:
    sys.exit("No refresh token returned — re-run (the script forces consent, so "
             "this is rare). Make sure the client type is 'Desktop app'.")

# Sanity check: prove the token works AND confirm it's the right account by
# listing the playlists it can see. (Read-only; non-fatal if it fails.)
try:
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/playlists"
        "?part=snippet&mine=true&maxResults=50",
        headers={"Authorization": f"Bearer {creds.token}"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    titles = [it["snippet"]["title"] for it in data.get("items", [])]
    print("\n✓ Token works. Playlists visible on this account:")
    for t in titles:
        print("   -", t)
    if not titles:
        print("   (none returned — check you signed in with the playlist owner)")
except Exception as e:  # noqa: BLE001
    print(f"\n(could not auto-verify the token: {e})")

print("\n" + "=" * 60)
print("  Add these as GitHub repo secrets")
print("  (Settings → Secrets and variables → Actions → New repository secret)")
print("=" * 60)
print(f"  YT_CLIENT_ID       {client_id}")
print(f"  YT_CLIENT_SECRET   {client_secret}")
print(f"  YT_REFRESH_TOKEN   {creds.refresh_token}")
print("=" * 60)
print("Keep these private. Revoke anytime at:")
print("  Google Account → Security → Third-party access")
