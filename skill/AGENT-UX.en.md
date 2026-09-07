# AGENT UX Contract (any agent)

Applies whatever the host: WorkBuddy, Codex, Claude, Cursor, etc. Behavior must be the same in every agent.

## 1. User-facing flow (always)
1. State what will be produced: a vertical (9:16) short drama from photos + story.
2. Quote before run: before any cloud video (Wan, CNY), show `length X ~= CNY Y (CNY 5 per 30s piece)` and the cloud reminder; wait for explicit confirmation.
3. Run only after the user confirms. If unsure, do nothing.
4. Length has no cap, per user's request.
5. On completion, give the final mp4 path + a short summary (duration, cost), never hide the essentials.

## 2. Do not expose internals
- Never show tokens / internal account IDs / internal commands to the user.
- No buyer-vs-developer terms (decided by the official API).

## 3. Retry & degrade
- Per-segment failure retries up to 2x, then ask; offer a simpler camera move instead of failing.

## 4. Cross-agent consistency
- Plain-text parseable; any agent can run `run_one.py` (local) + cloud template to reproduce this: price-quote -> confirm -> run -> deliver.
- Private handles live in local config and are never in this repo.