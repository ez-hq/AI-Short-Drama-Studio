#!/usr/bin/env python3
# build.py — build zh/en/generic 3 zips + language check + sha256 for AI Short Drama Studio.
import os, shutil, hashlib, zipfile

REPO = os.path.dirname(os.path.abspath(__file__))
NAME = "ai-short-drama-studio"
DIST = os.path.join(REPO, "dist")

def cjk(s): return sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")

def zip_dir(dirpath, zip_path):
    if os.path.exists(zip_path): os.remove(zip_path)
    base = os.path.basename(dirpath)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(dirpath):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, dirpath)
                z.write(full, os.path.join(base, rel))

LANG = {"zh": ("SKILL.md", "AGENT-UX.md"), "en": ("SKILL.en.md", "AGENT-UX.en.md")}
shared = ["pricing.json", "config.example.json", "LICENSE", "README.md"]

for L, (s, a) in LANG.items():
    D = os.path.join(DIST, f"{NAME}-{L}")
    if os.path.exists(D): shutil.rmtree(D)
    os.makedirs(os.path.join(D, "scripts"))
    os.makedirs(os.path.join(D, "tools"))
    shutil.copy(os.path.join(REPO, "skill", s), os.path.join(D, "SKILL.md"))
    shutil.copy(os.path.join(REPO, "skill", a), os.path.join(D, "AGENT-UX.md"))
    for f in shared:
        p = os.path.join(REPO, f)
        if os.path.exists(p): shutil.copy(p, os.path.join(D, f))
    for f in os.listdir(os.path.join(REPO, "skill", "scripts")):
        if f.endswith(".py"): shutil.copy(os.path.join(REPO, "skill", "scripts", f), os.path.join(D, "scripts", f))
    for f in os.listdir(os.path.join(REPO, "skill", "tools")):
        if f.endswith(".py"): shutil.copy(os.path.join(REPO, "skill", "tools", f), os.path.join(D, "tools", f))
    n = cjk(open(os.path.join(D, "SKILL.md"), encoding="utf-8").read())
    if L == "en" and n > 0: raise SystemExit(f"[abort] EN SKILL has {n} CJK")
    if L == "zh" and n <= 100: raise SystemExit(f"[abort] ZH SKILL CJK {n} <= 100")
    z = os.path.join(DIST, f"{NAME}-{L}.zip")
    zip_dir(D, z)
    sha = hashlib.sha256(open(z, "rb").read()).hexdigest()[:16]
    print(f"{os.path.basename(z)}   CJK={n}   sha256={sha}")
shutil.copy(os.path.join(DIST, f"{NAME}-zh.zip"), os.path.join(DIST, f"{NAME}.zip"))
print("OK 3 zips in dist/")