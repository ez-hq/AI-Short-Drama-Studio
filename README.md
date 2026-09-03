# ShortDrama SkillBot (V1)

Turn a short story + character photo(s) into a **20–30s vertical (9:16, 720p) micro-drama MP4**, automatically planned, generated, QC'd and assembled.

> Photo-anchors carry "who"; the story decides "what happens"; the planner decides "how to shoot"; the video model decides "how it moves."

## Highlights (V1)
- **Photo-anchored** — uses the user's real photo as the visual identity; no unstable text-invented character frames.
- **Cheap** — micro segments via a first→last-frame Wan engine (~¥0.28/segment measured); a 20–30 s drama ≈ ¥1–3, far below Kling Pro.
- **One-click local Skill** — story → plan → segments → QC → assemble → `shortdrama.mp4`.
- **Segment-level QC & retry (≤2, budget-capped)** — only re-run a failed segment, never the whole set.

## Pipeline
```
story + photos
  → plan (4 scenes: hook / discovery / reveal / cliffhanger)
  → per-scene: photo anchor → short 720p segment (Wan first/last-frame)
  → QC (face/identity/scene/continuity) → retry only failed segment
  → ffmpeg concat → final-shortdrama.mp4 (+ subtitle.srt, narration.txt, cover.jpg)
```

## Install / run (local Agent)
1. Install this repo as a WorkBuddy/tool schema (check each platform).
2. Set platform token via your LoomLoom(`shengsuanyun`) profile env.
3. `python scripts/finish_video.py --runid <segment-run-id> --wd out/` — finalize segments into `final-shortdrama.mp4`.

> Cloud orchestration config (template handles, model selections & proprietary prompts) is **not** part of this public repo — it stays proprietary and is provided to licensed users via `config.example.json`.

## Cost model (V1 target)
- 720p, 4 × 5–7 s ≈ 20–30 s, target ≈ ¥13–20 / task; measured micro sample ≈ ¥2–3.
- retry reserve ⇔ budget cap = taken; never exceed.

## License
MIT (local code only). Cloud templates & prompts are proprietary and not distributed here.

Author: ez-hq (ShortDrama SkillBot V1, 2026)
## 定价 (v0.2.0, 最终)
- 售价 ¥5 / 一次（30s 内）；>30s 按每30s=1次向上取整。
- 跑前必提醒用户价格 + 云端(Wan, 人民币)执行确认；开发者/用户身份由平台官方判定，无本地区分逻辑。
- 本地运行时 handle 存私有 config 文件（不入开源库）。
