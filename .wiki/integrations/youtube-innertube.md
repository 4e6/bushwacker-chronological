---
type: Integration
title: YouTube InnerTube (logged-in browser)
description: Reading and mutating the playlist via YouTube's internal InnerTube API from the signed-in browser session.
tags: [youtube, api, browser]
timestamp: 2026-07-27T18:15:00Z
---

# When to use

Playlist **reads and writes** go through YouTube's internal InnerTube API from the
user's **logged-in** session, via the `claude-in-chrome` tools: open
`https://www.youtube.com` (signed in) and run JS with `javascript_tool`. Auth is a
`SAPISIDHASH` computed in-page from the `SAPISID` cookie — **never print or
exfiltrate it**. Verified working 2026-06-27.

> The maintainer **declined** `yt-dlp --cookies-from-browser`: keep reads
> cookieless (plain yt-dlp on public data), do writes through the in-browser
> session, and **ask before any browser-cookie extraction**. Browser is Google
> Chrome. Related: [metered-API cost discipline](/conventions/metered-api-cost-discipline.md).

# Helper (paste in the youtube.com page context)

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

# Operations

Each returns `{status:'STATUS_SUCCEEDED', ...}` on success:

```js
// ADD (appends to end). The new entry's setVideoId is in the response's playlistEditResults.
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_ADD_VIDEO', addedVideoId:'<VIDEO_ID>'}]});
// MOVE right after an existing entry — this is how you place it chronologically.
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_MOVE_VIDEO_AFTER', setVideoId:'<MOVED_setVideoId>', movedSetVideoIdPredecessor:'<PREDECESSOR_setVideoId>'}]});
// REMOVE a specific entry (e.g. a mistaken duplicate — target the exact setVideoId).
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_REMOVE_VIDEO', setVideoId:'<setVideoId>'}]});
// CREATE a fresh playlist (only if rebuilding; accepts >100 videoIds, in order):
await api('playlist/create', {context:CTX, title:'...', privacyStatus:'PRIVATE', videoIds:[/* ids in order */]});
```

The [insert-a-new-video recipe](/playbooks/manual-sync.md) is ADD then
MOVE_VIDEO_AFTER.

# Gotchas

- **Anonymous reads cap at 100** (yt-dlp `--flat-playlist`, public web UI). This
  playlist has >100, so always verify with the authenticated `enumerate()` (which
  paginates past 100). This caused real confusion before — don't repeat it. It is
  also why the [text files are the source of truth](/decisions/0001-files-as-source-of-truth.md).
- `playlist/create` is **not** capped at 100.
- `edit_playlist` add/remove/move act per-entry by `setVideoId`; the same videoId
  can appear multiple times, each with its own `setVideoId`.
