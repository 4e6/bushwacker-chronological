# This directory is an OKF knowledge bundle

Durable knowledge about this project: why things are the way they are, what must
hold, what words mean here, where the boundaries fall, and what bites people.
Which type each is, is `reference/concept-types.md`'s to say. A reason goes in the
`# Why` section of the page it explains; a `Decision` page is for a fork between
alternatives that no single page owns, and the user says yes to it first. **Not**
documentation of the code — the code documents itself, and a page restating it is
wrong within a week.

**Invoke the `llm-wiki` skill before writing or editing anything here.** It
carries the frontmatter contract, the concept types, the half-life rule that
decides what may be written at all, and the index and lint steps that follow
every edit. Without it you will produce a page that looks fine and is not:
missing `type`, an unpinned `sources_digest`, absent from its index.

Reading needs no skill. Start at `index.md` and drill down; don't read the whole
bundle. If a page contradicts the code, reality wins — say so rather than reading
past it.

Three things hold either way:

- `index.md` and `log.md` are reserved names, and `CLAUDE.md`, `CLAUDE.local.md`
  and `AGENTS.md` are instructions. Every other `.md` here is a concept and needs
  a `type`.
- Every edit is followed by `okf.py index --write` and `okf.py lint`. That script
  ships with the `llm-wiki` skill. If you do not have it, say the index was not
  regenerated rather than skipping the step in silence — a stale index is exactly
  what it catches.
- A wiki change lands in the same commit as the change it describes.
