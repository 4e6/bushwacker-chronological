# Bushwacker History — chronological playlist (sync guide)

This project maintains a **curated YouTube playlist** that mirrors the channel
**@Bushwackerhistory**, with videos ordered by the **historical period each video
is about** (ancient → modern), not by upload date.

- YouTube playlist: **PLVw98VIsFGF8** — https://www.youtube.com/playlist?list=PLVw98VIsFGF8
  (owned by this Google account; currently **Public**).
- Channel: https://www.youtube.com/@Bushwackerhistory (Russian-language history channel).
- Baseline (2026-06-27): channel had **136** videos → **126** period videos in the
  playlist + **10** excluded (7 shorts + 3 meta).

Your job in a sync session: when the channel posts new videos, add the period
ones to the playlist **in the correct chronological slot** and keep the two local
files below in sync.

## Files = source of truth

- **`bushwacker_playlist.txt`** — human-readable mirror of the playlist: only the
  included (period) videos, sorted chronologically. Each entry is 3 lines:
  ```
  [ 1096]  Крестовые походы (с 1096)
          ▶ Крестовые походы
          https://www.youtube.com/watch?v=hq9QEJjYWuY
  ```
  The `watch?v=<ID>` lines are the authoritative record of playlist membership.
- **`bushwacker_excluded.txt`** — channel videos deliberately **NOT** in the
  playlist (shorts + meta), one per line: `[SHORT|META]  <video_id>  <title>  — reason`.
  This exists so they aren't re-detected as "new" every sync.

The video IDs in these two files together = every channel video already classified.

## Period sort key

`[YEAR]` = the **start year of the historical period** the video covers.
Negative = BCE, positive = CE, smaller = older; the file is sorted ascending.
For broad-span topics, use the start of the polity/era (e.g. Republic of Venice → 697;
"Хетты" → -1650; modern "Ликбез по Сирии" → 2011). Keep period labels in Russian,
matching the existing style.

## Sync workflow

### 1. Find new videos (read-only, no login needed)

```bash
cd <this project dir>
yt-dlp --flat-playlist --no-warnings --print "%(id)s" \
  "https://www.youtube.com/@Bushwackerhistory/videos" | sort > /tmp/chan_ids.txt
{ grep -oE 'watch\?v=[A-Za-z0-9_-]{11}' bushwacker_playlist.txt | sed 's#watch?v=##'
  awk '/^\[(SHORT|META)\]/{print $2}' bushwacker_excluded.txt ; } | sort -u > /tmp/known_ids.txt
comm -23 /tmp/chan_ids.txt /tmp/known_ids.txt    # => NEW, unclassified video IDs
```

Use the **ID set-difference** as the signal (stable). Don't rely on "last video id"
or upload dates — titles/dates can change and videos can be (un)listed out of order.
For each new ID get its title/duration with:
`yt-dlp --skip-download --print "%(duration)s s | %(upload_date)s | %(title)s" "https://youtu.be/<ID>"`

### 2. Classify & date each new video

- **Short trivia** — "Истфакт №N" / "Fact #N", duration ~100–330 s → **excluded (SHORT)**.
- **Meta / Q&A / broad non-period intro** — e.g. "Вне формата", "...ответы на вопросы",
  a series intro that isn't about one period → **excluded (META)**.
- **Otherwise = a period episode** (full episodes run ~1.5–2.5 h, 5000–8000 s):
  infer its **start year** + a short Russian period label.
  - Most titles state the era or give explicit dates: `(1455 - 1486)`, `XII - XIV вв.`,
    `до н.э.` — use them directly. Otherwise use historical knowledge of the topic.
  - If the period is genuinely ambiguous, read the transcript intro + date mentions:
    ```bash
    yt-dlp --write-auto-subs --sub-langs "ru.*,ru" --sub-format vtt --skip-download \
      -o "sub_%(id)s.%(ext)s" "https://youtu.be/<ID>"
    ```
    Strip VTT to text and look at the first ~300 words + century/"до н.э."/year tokens.
    Some videos have **no captions** — then infer from title + series context and note it.

### 3. Apply the change

**Period episode:**
1. Insert a 3-line block into `bushwacker_playlist.txt` at the correct `[YEAR]` slot
   (between the two neighbours by year).
2. Add it to the YouTube playlist and move it into that slot (see API below).
3. Bump the header's `videos:` count and `last synced:` date.

**Short / meta:** append a `[SHORT|META] <id> <title> — reason` line to
`bushwacker_excluded.txt` and bump its `last synced:` date. (No playlist change.)

### 4. Verify

Re-enumerate the playlist via the **authenticated** API (below) and confirm count,
order, and no duplicates. **Do not trust anonymous yt-dlp or the web UI for the full
list** — both cap at the **first 100** items and this playlist has >100. The
authenticated `enumerate()` returns all of them.

## YouTube playlist API (mutations need the logged-in browser)

Playlist reads/writes use YouTube's internal InnerTube API from the user's
**logged-in** session via the `claude-in-chrome` tools: open
`https://www.youtube.com` (signed in), then run JS with `javascript_tool`.
Auth is a `SAPISIDHASH` computed in-page from the `SAPISID` cookie — never print
or exfiltrate it. **Verified working 2026-06-27.**

> Preference: the user **declined** `yt-dlp --cookies-from-browser`. Keep reads
> cookieless (plain yt-dlp on public data) and do writes through the in-browser
> session. Ask before any browser-cookie extraction. Browser is **Chromium**.

Paste this helper in the page context on youtube.com:

```js
const pid = 'PLVw98VIsFGF8';
const API_KEY = ytcfg.get('INNERTUBE_API_KEY'), CTX = ytcfg.get('INNERTUBE_CONTEXT'), ORIGIN = 'https://www.youtube.com';
const sh = async () => { const m = document.cookie.match(/(?:^|;\s*)SAPISID=([^;]+)/) || document.cookie.match(/(?:^|;\s*)__Secure-3PAPISID=([^;]+)/); const S = decodeURIComponent(m[1]); const ts = Math.floor(Date.now()/1000); const b = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(`${ts} ${S} ${ORIGIN}`)); return `SAPISIDHASH ${ts}_${[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')}`; };
const api = async (p, b) => { const a = await sh(); const r = await fetch(`${ORIGIN}/youtubei/v1/${p}?key=${API_KEY}&prettyPrint=false`, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json','Authorization':a,'X-Origin':ORIGIN,'X-Goog-AuthUser':'0'}, body: JSON.stringify(b) }); const t = await r.text(); try { return JSON.parse(t); } catch(e) { return { _raw: t.slice(0,300) }; } };
// full enumeration (paginates past 100; returns playlist order WITH setVideoIds)
const deepTok = (n) => { let t=null; (function w(o){ if(t)return; if(Array.isArray(o)){o.forEach(w);} else if(o&&typeof o==='object'){ if(o.continuationCommand&&o.continuationCommand.token)t=o.continuationCommand.token; for(const k in o)w(o[k]); } })(n); return t; };
const coll = (j) => { let arr=null; (function w(o){ if(arr)return; if(Array.isArray(o)){ if(o.some(e=>e&&e.playlistVideoRenderer)){arr=o;return;} o.forEach(w);} else if(o&&typeof o==='object'){ for(const k in o)w(o[k]); } })(j); const it=[]; let tk=null; if(arr)for(const e of arr){ if(e.playlistVideoRenderer)it.push({v:e.playlistVideoRenderer.videoId, s:e.playlistVideoRenderer.setVideoId}); else if(e.continuationItemRenderer)tk=deepTok(e.continuationItemRenderer); } if(!tk){ let n=null; (function w(o){ if(n)return; if(Array.isArray(o)){o.forEach(w);} else if(o&&typeof o==='object'){ if(o.continuationItemRenderer){n=o.continuationItemRenderer;return;} for(const k in o)w(o[k]); } })(j); if(n)tk=deepTok(n);} return {it,tk}; };
const enumerate = async () => { let all=[]; let r=await api('browse',{context:CTX,browseId:'VL'+pid}); let {it,tk}=coll(r); all.push(...it); let p=1; const seen=new Set(); if(tk)seen.add(tk); while(tk&&p<20){ r=await api('browse',{context:CTX,continuation:tk}); const c=coll(r); p++; if(!c.it.length)break; all.push(...c.it); if(!c.tk||seen.has(c.tk))break; tk=c.tk; seen.add(tk);} return all; };
// const all = await enumerate();  // -> [{v: videoId, s: setVideoId}, ...] in playlist order
```

Operations (each returns `{status:'STATUS_SUCCEEDED', ...}` on success):

```js
// ADD (appends to end). The new entry's setVideoId is in the response's playlistEditResults.
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_ADD_VIDEO', addedVideoId:'<VIDEO_ID>'}]});

// MOVE an entry to right AFTER another existing entry (this is how you place it chronologically).
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_MOVE_VIDEO_AFTER', setVideoId:'<MOVED_setVideoId>', movedSetVideoIdPredecessor:'<PREDECESSOR_setVideoId>'}]});
// To place at the very top (unlikely for this channel): ACTION_MOVE_VIDEO_BEFORE with movedSetVideoIdSuccessor:'<current first setVideoId>'.

// REMOVE a specific entry (e.g. a mistaken duplicate — target the exact setVideoId).
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_REMOVE_VIDEO', setVideoId:'<setVideoId>'}]});

// CREATE a fresh playlist (only if rebuilding from scratch; accepts >100 videoIds, in order):
await api('playlist/create', {context:CTX, title:'...', privacyStatus:'PRIVATE', videoIds:[/* ids in order */]});
```

### Insert-a-new-video recipe

1. `const all = await enumerate();` — current order + setVideoIds.
2. ADD the new video. Re-`enumerate()`, find the new entry by its videoId → `newS`.
3. Predecessor = the **last** entry whose period year ≤ the new video's year (walk your
   local sorted list / `bushwacker_playlist.txt`). Get that entry's setVideoId from `all`.
4. MOVE: `ACTION_MOVE_VIDEO_AFTER {setVideoId:newS, movedSetVideoIdPredecessor:<pred.s>}`.
5. Re-`enumerate()` and confirm the order matches `bushwacker_playlist.txt`.

## Gotchas

- **Anonymous reads cap at 100** (yt-dlp `--flat-playlist`, public web UI). The playlist
  has >100, so always verify with the authenticated `enumerate()`. This caused real
  confusion before — don't repeat it.
- `playlist/create` is **not** capped at 100. `edit_playlist` add/remove/move act
  per-entry by `setVideoId`; the same videoId can appear multiple times, each with its
  own `setVideoId`.
- Regenerating the two text files from scratch was done with `scratchpad/build_playlist.py`
  (a curated `id → (year, label)` map); for routine syncs just edit the text files directly.
