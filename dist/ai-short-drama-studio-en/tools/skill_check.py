#!/usr/bin/env python3
"""skill_check.py — self-check local ShortDrama SkillBot files (no cloud calls).
Exits 0 if required files exist; prints a report otherwise."""
import os,sys
SK=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
req=["SKILL.md","pricing.json","AGENT-UX.md"]+["scripts/run_one.py","scripts/finish_video.py","scripts/editor_to_images.py"]
missing=[f for f in req if not os.path.exists(os.path.join(SK,f))]
if missing:
    print("CHECK: MISSING " + ", ".join(missing)); sys.exit(1)
print("CHECK: OK (SKILL/config/scripts present in %s)"%SK)
