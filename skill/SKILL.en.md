---
name: ai-short-drama-studio
description: Turn a story + character photo(s) into a continuous 9:16 720p short drama MP4, planned, generated, QC'd and assembled. Photo-anchored; cheap segments; local assembly.
version: 0.6.0
---

# AI Short Drama Studio

Inputs: story, photos (1+; the first photo is the character anchor), optional target duration.
Flow: plan -> photo-anchored segments -> QC + per-segment retry (<=2) -> ffmpeg concat -> final mp4 (+ subtitle / narration / cover).

## Video Engine (important)
- Default/cheap: **Micro Wan (First+last)** (wan-2.2-i2v fast-lora), ~CNY 0.28 per segment. Prefer this.
- Do NOT default to wan2.6-i2v (~CNY 6/seg): expensive unless the user explicitly asks for longer/higher-res.
- Private cloud handles live in `config.runtime.json` (local only; not in this repo).

## Pricing / Execution (final)
- **Price: CNY 5 per piece (within 30s)**; above 30s, billing rounds up to a whole 30s "piece" (see pricing.json).
- Mandatory pre-run notice: before cloud video (Wan, CNY), always show the price (CNY X) and the cloud-cost reminder; **run only after explicit user confirmation**.
- Buyer/developer identity is decided by the official API chain, not by this skill.
- **No hard cap**: run to the user's requested length (30s=CNY 5; each extra 30s = another piece); per-segment failures retry up to 2x, continuing after user confirmation.

Operational notes:
- `scripts/finish_video.py --runid <segment-run-id> --wd <dir>` assembles segments into final mp4.
- Uploading a photo grants portrait-rights permission; the listing must declare this.
- Keep old versions; never delete. Local code is MIT; cloud templates/instructions are proprietary (not public in this repo).
- Publish/identity: read `ACCOUNT-IDENTITY.md` before releasing to avoid wrong account.

## Model-Source Hard Rule (any agent)
- For text/image/video, allow only two paths:
  1) **LoomLoom (shengsuanyun)**: CNY billing (text/image/video). Default and official.
  2) **User's local image/editing model** (explicitly declared usable by the user).
- NEVER use other platforms' ImageGen / credits for any step. If keyframes are needed and the user has no photo nor local model, must use Loom's image edit (e.g. google/gemini-2.5-flash-image, CNYu).
- Rule: user motion runs only in CNY-Loom or their local; never third-party credits.

## Precise metering + default engine
- One "piece" = one finished video (<=30s) = CNY 5; >30s each 30s counts one.
- Default/cheap engine only = way-2.2-i2v-fast-lora; other engines (e.g. wan2.6) require explicit request and do a qc_report preflight.
- Self-check: `python3 tools/skill_check.py` (verifies local files only, not cloud).