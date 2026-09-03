---
name: shortdrama-skillbot
description: Turn a story + character photo(s) into a 20-30s 9:16 720p micro-drama MP4, planned, generated, QC'd and assembled. Photo-anchored; cheap segments; local assembly. Use when a user wants an AI-generated short cinematic video from a story and a reference photo.
version: 1.0.0
---

# ShortDrama SkillBot V1

Inputs: story (100-500 zh chars), photos (1-4, first = character anchor), optional targetNotes.
Flow: plan 4 scenes -> photo-anchored 720p segments (Wan first/last-frame) -> QC + segment-level retry (<=2) -> ffmpeg concat -> final mp4 + subtitle + narration + cover.

Operational notes:
- Cloud plan + segment generation runs on your LoomLoom(胜算云) profile; fill handles in config.json (proprietary, not in repo).
- `scripts/finish_video.py --runid <segment-run-id> --wd <dir>` finishes segments into final-shortdrama.mp4.
- Photo upload implies portrait-rights consent; declare it in listing description.
- Keep old versions; never delete. Local code MIT; cloud spec proprietary.
