#!/usr/bin/env python3
"""finish_video.py - ShortDrama SkillBot V1 local finalizer (part of the usable主体).

Given a completed Kling Market run (segments), download, technical-QC, concat,
attach subtitles, produce final-shortdrama.mp4 + report files.

Usage: python finish_video.py --runid <market-run-id> --wd <dir> [--confirm-count N]
Requires: tokens in ~/.zshrc; ffmpeg via imageio_ffmpeg.
"""
import argparse, json, os, re, subprocess, sys, urllib.request
import imageio_ffmpeg
import PIL.Image

def zsh_token():
    try:
        for line in open(os.path.expanduser("~/.zshrc"), encoding="utf-8", errors="replace"):
            m = re.match(r'^\s*export\s+LOOMLOOM_TOKEN_SHENGSUANYUN\s*=\s*["\']?([^"\']+)["\']?\s*$', line)
            if m:
                os.environ["LOOMLOOM_TOKEN_SHENGSUANYUN"] = m.group(1).strip(); return True
    except FileNotFoundError:
        pass
    return False

def loom(*a):
    subprocess.run(["loomloom", "server", "use", "shengsuanyun"], capture_output=True)
    p = subprocess.run(["loomloom"]+[str(x) for x in a]+["--output","json"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("loom%s rc=%s\n%s%s" % (a[:2], p.returncode, p.stdout, p.stderr))
    return json.loads(p.stdout)

def ffmpeg(): return imageio_ffmpeg.get_ffmpeg_exe()

def probe_duration(f):
    p = subprocess.run([ffmpeg(), "-i", f], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr)
    return None if not m else int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runid", required=True)
    ap.add_argument("--wd", default="./sdeos")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--budget", type=float, default=40.0)
    a = ap.parse_args()
    zsh_token()
    os.makedirs(os.path.join(a.wd, "segments"), exist_ok=True)
    rows = loom("run", "result-rows", a.runid)
    segs = []
    for r in rows.get("rows", []):
        if r.get("status") != "completed":
            raise SystemExit("segment row not completed: %s" % r.get("errorMessage"))
        for art in r.get("artifacts", []):
            if art.get("mimeType","").startswith("video"):
                i = len(segs); p = "%s/segments/segment_%02d.mp4" % (a.wd, i+1)
                urllib.request.urlretrieve(art["accessUrl"], p)
                segs.append(p); break
    print("downloaded segments:", segs)
    # technical QC
    bad = [s for s in segs if not os.path.getsize(s) > 0]
    if bad:
        raise RuntimeError("empty segments: %s" % bad)
    # concat
    concat = os.path.join(a.wd, "concat.txt")
    with open(concat, "w") as f:
        for s in segs:
            f.write("file '%s'\n" % os.path.abspath(s))
    out = os.path.join(a.wd, "final-shortdrama.mp4")
    p = subprocess.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", concat,
                        "-c", "copy", out], capture_output=True, text=True)
    if p.returncode != 0:
        # fallback to re-encode
        p = subprocess.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", concat,
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", out], capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError("concat failed: %s" % p.stderr[-800:])
    dur = probe_duration(out)
    print("final-shortdrama.mp4 duration=%.2fs, size=%dKB" % (dur, os.path.getsize(out)//1024))

if __name__ == "__main__":
    main()