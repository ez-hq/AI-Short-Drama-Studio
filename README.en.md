# AI Short Drama Studio — English line (independent)

This is the English build of the AI Short Drama Studio SkillBot. It is a **separate product line**: its version numbers do not track the Chinese (zh) line.

- **English line version**: 0.6.0-en
- **Chinese (zh) line version:** 0.6.0
- Installable zips (GitHub Release assets): `ai-short-drama-studio-en.zip` (this line, all-English) and `ai-short-drama-studio-zh.zip` (Chinese).

## What it does
Turn a short story + one or more character photos into a continuous 9:16 720p micro-drama MP4:
plan -> photo-anchored segments -> QC (per-segment retry <=2) -> local assembly -> final MP4.

## How to use (3 steps)
1. Requires Python 3.9+ and an internet connection.
2. Place photos + a short story in a working directory.
3. Copy `config.example.json` -> `config.json` and fill in your own cloud (LoomLoom/shengsuanyun) handles. Private handles are never in this repo.
4. Run: `python3 scripts/run_one.py --photos-dir <dir> --out <dir>`.
5. QC the output: `python3 tools/qc_report.py out.mp4`; self-check: `python3 tools/skill_check.py`.

## Pricing
- CNY 5 per piece (within 30s). One piece = one finished video <=30s. Above 30s, each extra 30s counts one.
- Default/cheap video engine: Micro Wan (wan-2.2-i2v fast-lora, First+last), ~CNY 0.28/segment.
- Models only run via Loom (shengsuanyun) in CNY, or a user-local model. No third-party credits.

## License
MIT (local code only). Cloud template handles / instructions are proprietary and are NOT in this repo.

## Changelog
- 0.6.0-en — English independent line: English-only package, English version numbering, English README/docs.