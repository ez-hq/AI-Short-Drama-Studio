#!/usr/bin/env python3
"""ShortDrama SkillBot V1 — one-shot RMB pipeline runner.

story/photo(s) -> shortdrama.mp4  (all cloud steps bill RMB on 胜算云; no WorkBuddy credits)

Usage:
  python run_one.py --photos-dir DIR [--out OUT] [--dry-run] [--auto]
Reads private cloud handles from ../config.runtime.json (proprietary; not on GitHub).
"""
import argparse, json, os, re, subprocess, sys, glob, urllib.request, time
import imageio_ffmpeg

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOM   = "loomloom"

def load_cfg():
    p = os.path.join(SKILL, "config.runtime.json")
    return json.load(open(p, encoding="utf-8"))

def token():
    try:
        for line in open(os.path.expanduser("~/.zshrc"), encoding="utf-8", errors="replace"):
            m = re.match(r'^\s*export\s+LOOMLOOM_TOKEN_SHENGSUANYUN\s*=\s*["\']?([^"\']+)["\']?\s*$', line)
            if m:
                os.environ["LOOMLOOM_TOKEN_SHENGSUANYUN"] = m.group(1).strip(); return
    except FileNotFoundError:
        pass

def loom(*a):
    subprocess.run(["loomloom", "server", "use", "shengsuanyun"], capture_output=True)
    p = subprocess.run(["loomloom"]+[str(x) for x in a]+["--output","json"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("loom %s failed:\n%s%s" % (str(a[:3]), p.stdout, p.stderr))
    return json.loads(p.stdout)

def av_duration(path):
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    return None if not m else round(int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3)), 2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos-dir", required=True)
    ap.add_argument("--out", default=".out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auto", action="store_true")
    a = ap.parse_args()
    cfg = load_cfg(); token()
    os.makedirs(a.out, exist_ok=True)

    photos = sorted(p for p in os.listdir(a.photos_dir)
                    if p.lower().endswith((".png", ".jpg", ".jpeg")))
    if len(photos) < 2:
        sys.exit("需要至少 2 张照片")
    N = min(4, len(photos) - 1)
    print("[步骤1] 规划: photo-anchor, %d 段 720p, engine=%s" % (N, cfg["videoMicro"]["templateId"][:12]))

    if a.dry_run:
        print("  上传", N+1, "图, 组装", N, "行首尾帧 -> 报价 -> run -> 拼接  [dry-run 不花钱]")
        print("  目标产出: %s/shortdrama.mp4 (RMB, 约 ¥%.2f)" % (a.out, N*0.28))
        return

    # upload each photo as an asset (RMB-free)
    ids = {}
    for i, nm in enumerate(photos):
        ids["P%d" % i] = loom("input-asset", "upload", os.path.join(a.photos_dir, nm))["inputAssetId"]
        print("  up", nm, "...", ids["P%d" % i][:16])

    # build rows (consecutive first->last), single proven motion
    mv = "smooth natural transition between the two anchored photos; identity, costume, scene unchanged; no new objects; stable camera."
    rows = [{"firstFrame": ids["P%d" % i], "lastFrame": ids["P%d" % (i+1)], "motion": mv} for i in range(N)]
    rowsf = os.path.join(a.out, "rows.jsonl")
    with open(rowsf, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")

    fid = loom("orchestration-input", "upload", rowsf)["inputFileId"]
    print("  上传 %d 行 -> input_file_id=%s" % (len(rows), fid[:16]))
    pre = loom("template-spec", "precheck", cfg["videoMicro"]["templateId"], "--version-id",
               cfg["videoMicro"]["versionId"], "--input-file-id", fid)["precheck"]
    print("  precheck: est=%s %s (actual 后结)" % (pre["estimatedTotalCost"]["amount"],
                                                  pre["estimatedTotalCost"]["currency"]))
    if not a.auto:
        # cost gate: requires --auto for headless, otherwise confirm here
        sys.exit("请在确认成本后加 --auto 运行（本次为金额确认门）")
    runid = loom("template-spec", "run", cfg["videoMicro"]["templateId"],
                 "--version-id", cfg["videoMicro"]["versionId"],
                 "--input-file-id", fid, "--client-request-id", "one-%d" % int(time.time()))["runId"]
    print("  已提交，runId=%s，等待..." % runid)
    loom("run", "watch", runid)
    rows = loom("run", "result-rows", runid)["rows"]
    segs = []
    for r in rows:
        for art in r.get("artifacts", []):
            if art.get("mimeType", "").startswith("video"):
                p = os.path.join(a.out, "segment_%02d.mp4" % (len(segs)+1))
                urllib.request.urlretrieve(art["accessUrl"], p)
                segs.append(p); break
    # concat
    concat = os.path.join(a.out, "concat.txt")
    with open(concat, "w") as f:
        for s in segs: f.write("file '%s'\n" % os.path.abspath(s))
    final = os.path.join(a.out, "shortdrama.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
                    "-i", concat, "-c", "copy", final], capture_output=True)
    print("  DONE ->", final, "%.2fs" % (av_duration(final) or -1))

if __name__ == "__main__":
    main()