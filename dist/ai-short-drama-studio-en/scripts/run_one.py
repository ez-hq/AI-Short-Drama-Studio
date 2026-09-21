#!/usr/bin/env python3
"""ShortDrama SkillBot V1 — one-shot RMB pipeline runner.

story/photo(s) -> shortdrama.mp4  (all cloud steps bill RMB on 胜算云; no WorkBuddy credits)

Usage:
  python run_one.py --photos-dir DIR [--out OUT] [--dry-run] [--auto] [--no-crop916]
Reads private cloud handles from ../config.runtime.json (proprietary; not on GitHub).

Note on aspect ratio: the cloud video engine (Micro Engine / Wan FT) has NO aspect
parameter — the output inherits the first frame's aspect. Photos are therefore
normalised to 9:16 by center-crop before upload (see crop_to_916). Pass --no-crop916
to keep the old behaviour and upload the originals untouched.
"""
import argparse, json, os, re, subprocess, sys, glob, urllib.request, time
import imageio_ffmpeg

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOM   = "loomloom"
AR_916 = 9.0 / 16.0          # 0.5625

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

def crop_to_916(src, outdir):
    """Center-crop one image to 9:16 so the cloud engine cannot inherit a wrong
    aspect. Returns the path to use for upload (the original when already ~9:16)."""
    try:
        from PIL import Image
    except ImportError:
        sys.exit("缺少 Pillow：pip3 install -r requirements.txt（或加 --no-crop916 跳过裁剪）")
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if abs(w / h - AR_916) < 0.01:
        return src
    if w / h > AR_916:                       # too wide -> crop width
        nw = int(round(h * AR_916)); box = ((w - nw) // 2, 0, (w - nw) // 2 + nw, h)
    else:                                    # too tall -> crop height
        nh = int(round(w / AR_916)); box = (0, (h - nh) // 2, w, (h - nh) // 2 + nh)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + "_916.png")
    im.crop(box).save(out)
    print("  crop %s %dx%d -> %dx%d (9:16)" % (os.path.basename(src), w, h, im.crop(box).size[0], im.crop(box).size[1]))
    return out

def av_duration(path):
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    return None if not m else round(int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3)), 2)

def av_size(path):
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", path], capture_output=True, text=True)
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", r.stderr, re.S)
    return None if not m else (int(m.group(1)), int(m.group(2)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos-dir", required=True)
    ap.add_argument("--out", default=".out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--no-crop916", action="store_true",
                    help="skip the 9:16 normalisation and upload photos as-is (old behaviour)")
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
        print("  9:16 归一化: %s" % ("关闭 (--no-crop916)" if a.no_crop916 else "开启（上传前中心裁剪）"))
        print("  目标产出: %s/shortdrama.mp4 (RMB, 约 ¥%.2f)" % (a.out, N*0.28))
        return

    # 9:16 normalisation (the engine has no aspect parameter -> it inherits firstFrame)
    srcs = [os.path.join(a.photos_dir, p) for p in photos]
    if not a.no_crop916:
        print("[步骤2] 归一化为 9:16")
        srcs = [crop_to_916(p, os.path.join(a.out, "photos_916")) for p in srcs]

    # upload each photo as an asset (RMB-free)
    ids = {}
    for i, src in enumerate(srcs):
        ids["P%d" % i] = loom("input-asset", "upload", src)["inputAssetId"]
        print("  up", os.path.basename(src), "...", ids["P%d" % i][:16])

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

    # post-run aspect check: prove the 9:16 promise instead of assuming it
    bad = []
    for s in segs:
        wh = av_size(s)
        ok = bool(wh) and abs(wh[0] / wh[1] - AR_916) < 0.06
        print("  %s %s 9:16=%s" % (os.path.basename(s), ("%dx%d" % wh) if wh else "?", ok))
        if not ok: bad.append(os.path.basename(s))
    if bad:
        print("  [WARN] 以下段不是 9:16（引擎按首帧比例出片）: %s" % ", ".join(bad))

    # concat
    concat = os.path.join(a.out, "concat.txt")
    with open(concat, "w") as f:
        for s in segs: f.write("file '%s'\n" % os.path.abspath(s))
    final = os.path.join(a.out, "shortdrama.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
                    "-i", concat, "-c", "copy", final], capture_output=True)
    print("  DONE ->", final, "%.2fs" % (av_duration(final) or -1), av_size(final) or "")

if __name__ == "__main__":
    main()
