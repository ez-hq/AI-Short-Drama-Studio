#!/usr/bin/env python3
"""ShortDrama SkillBot V1 — one-shot RMB pipeline runner.

Two modes (all cloud steps bill RMB on 胜算云; no WorkBuddy credits):

  A) photos only (original behaviour, unchanged):
       python run_one.py --photos-dir DIR [--out OUT] [--dry-run] [--auto] [--no-crop916]

  B) story-driven full chain (new):
       python run_one.py --photos-dir DIR --story FILE_OR_TEXT [--out OUT] [--auto]
     1. Story Engine  -> blueprint JSON (characters, continuity, keyframe prompts, segments)
     2. Keyframe Editor -> 9:16 keyframes (image-to-image from the anchor photo)
     3. Micro Engine  -> one video segment per blueprint segment
     plus a subtitle.srt built from the blueprint's dialogue/narration/caption.

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

# Story Engine templateInputs are enum-constrained by the server; sending an
# out-of-range value fails the whole run (and costs nothing, but wastes a trip).
DURATIONS = ("Auto", "60", "90", "120")
STYLES = ("cinematic modern drama", "都市情感", "都市悬疑", "霸总豪门", "校园青春",
          "古风", "仙侠", "犯罪悬疑", "温馨治愈")

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

def upload_rows(rows, outdir, tag):
    """Write rows.jsonl, upload it, return (inputFileId, path)."""
    rowsf = os.path.join(outdir, "%s_rows.jsonl" % tag)
    with open(rowsf, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    fid = loom("orchestration-input", "upload", rowsf)["inputFileId"]
    return fid, rowsf

def run_template(tid, vid, fid, tag, auto, max_cost=None):
    """Precheck -> cost gate -> run -> watch -> result rows. Returns (runId, rows)."""
    pre = loom("template-spec", "precheck", tid, "--version-id", vid,
               "--input-file-id", fid)["precheck"]
    amt = pre["estimatedTotalCost"]["amount"]; cur = pre["estimatedTotalCost"]["currency"]
    print("  [%s] precheck: est=%s %s (actual 后结)" % (tag, amt, cur))
    if max_cost is not None and float(amt) > float(max_cost):
        sys.exit("[熔断] [%s] 预估 %s %s 超过 --max-cost %s，已中止（未提交、未扣费）"
                 % (tag, amt, cur, max_cost))
    if not auto:
        sys.exit("请在确认成本后加 --auto 运行（本次为金额确认门）")
    runid = loom("template-spec", "run", tid, "--version-id", vid,
                 "--input-file-id", fid,
                 "--client-request-id", "%s-%d" % (tag, int(time.time())))["runId"]
    print("  [%s] runId=%s，等待..." % (tag, runid))
    loom("run", "watch", runid)
    return runid, loom("run", "result-rows", runid)["rows"]

def download_artifacts(rows, outdir, tag, mime_prefix, ext):
    got = []
    for r in rows:
        for art in r.get("artifacts", []):
            if art.get("mimeType", "").startswith(mime_prefix):
                p = os.path.join(outdir, "%s_%02d%s" % (tag, len(got) + 1, ext))
                urllib.request.urlretrieve(art["accessUrl"], p)
                got.append(p); break
    return got

def load_characters(arg, n_photos):
    """Build the Story Engine's characterDescription and the photo->character plan.

    - arg is None            -> no description (the Story Engine infers from the story)
    - arg is a path to a .txt -> one non-empty line per character, line i describes
      the character in photo i (this is what binds a description to a photo)
    - arg is plain text      -> a single description covering all characters
    Returns (description_or_None, per_character_descriptions_or_None).
    """
    if not arg:
        return None, None
    if os.path.isfile(arg):
        lines = [l.strip() for l in open(arg, encoding="utf-8").read().splitlines()]
        lines = [l for l in lines if l]
        if len(lines) >= 2 and n_photos >= 2:
            desc = "The story has %d main characters. " % len(lines)
            desc += " ".join("CHAR%02d = %s" % (i + 1, l) for i, l in enumerate(lines))
            return desc, lines
        if lines:
            return " ".join(lines), None
        return None, None
    return arg, None

def pick_anchors(kfs, char_ids, coverage=True):
    """Assign one anchor character per keyframe.

    The prompt template always lists CHAR01 first, so "earliest mention" is a
    misleading signal — every keyframe ended up anchored to the first character.
    The shot is usually about whoever the prompt NAMES MOST, so mention count is
    the primary signal and earliest position only breaks ties. A coverage pass
    then guarantees that every character the blueprint declares drives at least
    one keyframe, when the blueprint gives it one worth using.

    Returns a list of character ids (None = no character named, use photo 0).
    """
    stats = []
    for k in kfs:
        p = k.get("prompt") or ""
        stats.append({cid: (p.count(cid), p.find(cid)) for cid in char_ids if cid})

    assign = []
    for row in stats:
        cands = [(n, -pos, cid) for cid, (n, pos) in row.items() if n > 0]
        assign.append(max(cands)[2] if cands else None)

    if coverage:
        used = set(a for a in assign if a)
        for cid in [c for c in char_ids if c and c not in used]:
            best_i, best_key = None, None
            for i, row in enumerate(stats):
                n = row.get(cid, (0, -1))[0]
                if n <= 0:
                    continue
                others = max([v[0] for k2, v in row.items() if k2 != cid] or [0])
                key = (n - others, n)
                if best_key is None or key > best_key:
                    best_key, best_i = key, i
            if best_i is not None and best_key[0] >= 0:
                assign[best_i] = cid
    return assign, stats

def download_by_row(rows, outdir, tag, mime_prefix, ext):
    """Map each result row's rowIndex -> downloaded local file (successful rows only)."""
    out = {}
    for r in rows:
        ri = r.get("rowIndex")
        for art in r.get("artifacts", []):
            if art.get("mimeType", "").startswith(mime_prefix):
                p = os.path.join(outdir, "%s_r%s%s" % (tag, ri, ext))
                urllib.request.urlretrieve(art["accessUrl"], p)
                out[ri] = p; break
    return out

def render_batched(cfg_key, rows_of, outdir, tag, mime, ext, name_fmt, label,
                   auto, max_cost, batch, retries, pause):
    """Submit rows in small sequential batches, retrying failures.

    Both upstream models throttle parallel work (HTTP 429: the image model with
    "Throttling.RateQuota", the video model with "rate limit for creating
    predictions"), so a single wide submission silently loses rows. Anything that
    still fails after the retries ends the run loudly instead of producing a
    video that is quietly missing pieces.

    Returns {row position: local path}; every position is guaranteed present.
    """
    n = len(rows_of)
    pending = list(range(n))
    files = {}
    for attempt in range(1, retries + 2):
        if not pending:
            break
        if attempt > 1:
            print("  [%s] 重试第 %d 次，剩 %d 项：%s" % (label, attempt - 1, len(pending), pending))
        still = []
        for i in range(0, len(pending), batch):
            chunk = pending[i:i + batch]
            rows = [rows_of[k] for k in chunk]
            fid, _ = upload_rows(rows, outdir, tag)
            print("  [%s] 批次 %d：处理 %s" % (label, i // batch + 1, chunk))
            _, res = run_template(cfg_key["templateId"], cfg_key["versionId"],
                                  fid, tag, auto, max_cost)
            got = download_by_row(res, outdir, tag, mime, ext)
            for pos, k in enumerate(chunk):
                if pos in got:
                    dst = os.path.join(outdir, name_fmt % k)
                    os.replace(got[pos], dst)
                    files[k] = dst
                else:
                    still.append(k)
            if i + batch < len(pending):
                time.sleep(pause)
        pending = still
    if pending:
        sys.exit("[断链] %s 有 %d 项在重试后仍未生成：%s（上游限流；可加大 --kf-pause / 稍后重跑）"
                 % (label, len(pending), pending))
    return files

def inline_text_of(rows):
    """Text outputs come back as inlineText rather than a file."""
    for r in rows:
        for art in r.get("artifacts", []):
            t = art.get("inlineText")
            if t:
                return t
        if r.get("inlineText"):
            return r["inlineText"]
    return ""

def parse_blueprint(raw):
    s = (raw or "").strip()
    s = re.sub(r'^```(?:json)?\s*', '', s); s = re.sub(r'\s*```$', '', s)
    try:
        return json.loads(s)
    except Exception as e:
        sys.exit("[断链] Story Engine 的产出不是合法 JSON（%s）。原始输出前 200 字：\n%s" % (e, raw[:200]))

def validate_blueprint(bp):
    """Fail loudly instead of producing a silently wrong video (broken-chain guard)."""
    need = ("keyframes", "segments")
    missing = [k for k in need if not bp.get(k)]
    if missing:
        sys.exit("[断链] 蓝图缺少 %s 字段" % ", ".join(missing))
    kfs, segs = bp["keyframes"], bp["segments"]
    idx = set()
    for k in kfs:
        p = str(k.get("prompt") or "").strip()
        if not p:
            sys.exit("[断链] 有 keyframe 缺 prompt")
        idx.add(k.get("index"))
    bad = []
    for sg in segs:
        for side in ("firstFrame", "lastFrame"):
            ref = str(sg.get(side) or "")
            m = re.match(r'^KF(\d+)$', ref)
            if not m or int(m.group(1)) not in idx:
                bad.append("seg%s.%s=%r" % (sg.get("index"), side, ref))
        if not str(sg.get("motionPrompt") or "").strip():
            bad.append("seg%s 缺 motionPrompt" % sg.get("index"))
    if bad:
        sys.exit("[断链] 蓝图的帧引用对不上 keyframes[]: %s" % ", ".join(bad[:6]))
    repeat = [sg.get("index") for sg in segs if sg.get("firstFrame") == sg.get("lastFrame")]
    print("  蓝图校验通过：%d 个关键帧 / %d 段%s" % (
        len(kfs), len(segs), ("；⚠ 首尾同帧（该段几乎不动）: seg%s" % repeat) if repeat else ""))

def write_srt(bp, path):
    """Build subtitle.srt from the blueprint's dialogue/narration/caption."""
    t = 0.0; lines = []
    for i, sg in enumerate(bp.get("segments", []), start=1):
        dur = float(sg.get("duration") or 10)
        txt = " ".join(x for x in (sg.get("dialogue"), sg.get("narration")) if x)
        if txt:
            lines.append("%d\n%s --> %s\n%s\n" % (
                len(lines) + 1, ts(t), ts(t + dur), txt))
        t += dur
    if lines:
        open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path

def ts(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return ("%02d:%02d:%06.3f" % (h, m, s)).replace(".", ",")

def story_mode(a, cfg, srcs, photos):
    """Full chain: Story Engine -> Keyframe Editor -> Micro Engine."""
    story = open(a.story, encoding="utf-8").read() if os.path.isfile(a.story) else a.story
    cdesc, per_char = load_characters(a.character, len(srcs))
    print("[步骤1] Story Engine：故事%s -> 蓝图" % ("（%d 个角色）" % len(per_char) if per_char else ""))
    row = {"storyText": story, "visualStyle": a.style, "targetDuration": a.duration}
    if cdesc:
        row["characterDescription"] = cdesc
    if per_char:
        for i, d in enumerate(per_char[:len(srcs)]):
            print("  角色%d  <- %s : %s" % (i + 1, os.path.basename(srcs[i]), d[:52]))
    fid, _ = upload_rows([row], a.out, "story")
    _, rows = run_template(cfg["storyEngine"]["templateId"], cfg["storyEngine"]["versionId"],
                           fid, "story", a.auto, a.max_cost)
    bp = parse_blueprint(inline_text_of(rows))
    bp_path = os.path.join(a.out, "blueprint.json")
    open(bp_path, "w", encoding="utf-8").write(json.dumps(bp, ensure_ascii=False, indent=2))
    print("  蓝图 -> %s（%s / %s 段）" % (bp_path, bp.get("story", {}).get("title"),
                                          len(bp.get("segments", []))))
    validate_blueprint(bp)

    kfs, segs = bp["keyframes"], bp["segments"]
    print("[步骤2] Keyframe Editor：锚点照片 + 提示词 -> 9:16 关键帧")
    # one anchor asset per photo; blueprint character i <- photo i (sorted order)
    anchor_list = [loom("input-asset", "upload", s)["inputAssetId"] for s in srcs]
    bible = bp.get("characterBible") or []
    char_ids = [c.get("characterId") for c in bible if c.get("characterId")] or ["CHAR01"]
    anchor_of = {}
    for i, cid in enumerate(char_ids):
        anchor_of[cid] = anchor_list[i % len(anchor_list)]
    print("  多角色映射：%s" % ", ".join(
        "%s <- %s" % (cid, os.path.basename(srcs[i % len(srcs)]))
        for i, cid in enumerate(char_ids)))
    if len(char_ids) > len(anchor_list):
        print("  [WARN] 蓝图有 %d 个角色但只给了 %d 张照片，已循环复用"
              % (len(char_ids), len(anchor_list)))
    if len(anchor_list) > len(char_ids):
        print("  [WARN] 给了 %d 张照片但蓝图只用了 %d 个角色，多余照片未被引用：%s"
              % (len(anchor_list), len(char_ids),
                 [os.path.basename(x) for x in srcs[len(char_ids):]]))
    assign, stats = pick_anchors(kfs, char_ids)
    kf_rows = []
    for k, cid, row in zip(kfs, assign, stats):
        detail = " ".join("%s×%d" % (c, row[c][0]) for c in char_ids if row.get(c, (0,))[0])
        print("    KF%-3s <- %-7s (%s)" % (k.get("index"), cid or "第1张", detail))
        kf_rows.append({"photo": anchor_of.get(cid, anchor_list[0]), "editPrompt": k["prompt"]})
    used = {}
    for cid in assign:
        if cid:
            used[cid] = used.get(cid, 0) + 1
    print("  锚点覆盖：%s" % ", ".join("%s×%d" % (c, used.get(c, 0)) for c in char_ids))
    for cid in char_ids:
        if not used.get(cid):
            print("  [WARN] %s 没有任何关键帧以它为主：它的脸不会被锚定"
                  "（Keyframe Editor 每次只吃 1 张参考图，这是模板固有限制）" % cid)
    got = render_batched(cfg["imageEditor"], kf_rows, a.out, "kf", "image", ".png",
                         "keyframe_KF%d.png", "kf", a.auto, a.max_cost,
                         a.kf_batch, a.retry, a.kf_pause)
    kf_by_index = {kfs[pos].get("index"): got[pos] for pos in range(len(kfs))}
    print("  关键帧 %d/%d 张（全部就位）" % (len(kf_by_index), len(kfs)))

    print("[步骤3] Micro Engine：关键帧 -> 视频段")
    kf_idx = {}
    for idx, f in kf_by_index.items():
        kf_idx[idx] = loom("input-asset", "upload", f)["inputAssetId"]
    mv_rows = []
    for sg in segs:
        i = int(re.match(r'^KF(\d+)$', sg["firstFrame"]).group(1))
        j = int(re.match(r'^KF(\d+)$', sg["lastFrame"]).group(1))
        mv_rows.append({"firstFrame": kf_idx[i], "lastFrame": kf_idx[j],
                        "motion": sg.get("motionPrompt") or "subtle natural motion"})
    got = render_batched(cfg["videoMicro"], mv_rows, a.out, "seg", "video", ".mp4",
                         "segment_sg%02d.mp4", "seg", a.auto, a.max_cost,
                         a.kf_batch, a.retry, a.kf_pause)
    if len(got) != len(segs):
        sys.exit("[断链] 视频段数量不符：蓝图 %d 段，实得 %d 段" % (len(segs), len(got)))
    segs_files = [got[pos] for pos in range(len(segs))]
    print("  视频段 %d/%d（全部就位）" % (len(segs_files), len(segs)))

    srt = write_srt(bp, os.path.join(a.out, "subtitle.srt"))
    print("  字幕 -> %s" % srt)
    return segs_files, os.path.join(a.out, "shortdrama.mp4")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos-dir", required=True)
    ap.add_argument("--out", default=".out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--no-crop916", action="store_true",
                    help="skip the 9:16 normalisation and upload photos as-is (old behaviour)")
    ap.add_argument("--story", help="story text, or a path to a .txt file -> full chain "
                                    "(Story Engine -> Keyframe Editor -> Micro Engine)")
    ap.add_argument("--character", help="optional character description for the Story Engine")
    ap.add_argument("--style", default="cinematic modern drama", help="visualStyle for the Story Engine")
    ap.add_argument("--duration", default="Auto", help="targetDuration for the Story Engine: %s" % "/".join(DURATIONS))
    ap.add_argument("--max-cost", type=float, default=None,
                    help="abort before submitting if one step's precheck estimate exceeds this (CNY)")
    ap.add_argument("--kf-batch", type=int, default=2,
                    help="keyframes per sequential batch (upstream image API rate-limits parallel edits)")
    ap.add_argument("--kf-pause", type=float, default=3.0, help="seconds between keyframe batches")
    ap.add_argument("--retry", type=int, default=2, help="retries for failed keyframe rows (SKILL: <=2)")
    a = ap.parse_args()
    if a.story:
        if a.duration not in DURATIONS:
            sys.exit("--duration 只能是 %s（服务端枚举约束），收到 %r" % ("/".join(DURATIONS), a.duration))
        if a.style not in STYLES:
            sys.exit("--style 只能是 %s，收到 %r" % ("/".join(STYLES), a.style))
    cfg = load_cfg(); token()
    os.makedirs(a.out, exist_ok=True)

    photos = sorted(p for p in os.listdir(a.photos_dir)
                    if p.lower().endswith((".png", ".jpg", ".jpeg")))
    if not photos:
        sys.exit("--photos-dir 里没有图片")
    if not a.story and len(photos) < 2:
        sys.exit("需要至少 2 张照片")
    N = min(4, len(photos) - 1)
    if a.story:
        print("[步骤1] 规划: story+photo, engine=%s" % cfg["videoMicro"]["templateId"][:12])
    else:
        print("[步骤1] 规划: photo-anchor, %d 段 720p, engine=%s" % (N, cfg["videoMicro"]["templateId"][:12]))

    if a.dry_run:
        if a.story:
            print("  链路: Story Engine -> Keyframe Editor -> Micro Engine -> 拼接")
            print("  多角色: %d 张照片按文件名顺序对应蓝图里的第 1..%d 个角色"
                  % (len(photos), len(photos)))
            print("  9:16 归一化: %s" % ("关闭 (--no-crop916)" if a.no_crop916 else "开启（上传前中心裁剪）"))
        else:
            print("  上传", N+1, "图, 组装", N, "行首尾帧 -> 报价 -> run -> 拼接  [dry-run 不花钱]")
            print("  9:16 归一化: %s" % ("关闭 (--no-crop916)" if a.no_crop916 else "开启（上传前中心裁剪）"))
            print("  目标产出: %s/shortdrama.mp4 (RMB, 约 ¥%.2f)" % (a.out, N*0.28))
        return

    # 9:16 normalisation (the engine has no aspect parameter -> it inherits firstFrame)
    srcs = [os.path.join(a.photos_dir, p) for p in photos]
    if not a.no_crop916:
        print("[步骤2] 归一化为 9:16")
        srcs = [crop_to_916(p, os.path.join(a.out, "photos_916")) for p in srcs]

    if a.story:
        seg_files, final = story_mode(a, cfg, srcs, photos)
    else:
        # upload each photo as an asset (RMB-free)
        ids = {}
        for i, src in enumerate(srcs):
            ids["P%d" % i] = loom("input-asset", "upload", src)["inputAssetId"]
            print("  up", os.path.basename(src), "...", ids["P%d" % i][:16])

        # build rows (consecutive first->last), single proven motion
        mv = "smooth natural transition between the two anchored photos; identity, costume, scene unchanged; no new objects; stable camera."
        rows = [{"firstFrame": ids["P%d" % i], "lastFrame": ids["P%d" % (i+1)], "motion": mv} for i in range(N)]
        fid, _ = upload_rows(rows, a.out, "one")
        print("  上传 %d 行 -> input_file_id=%s" % (len(rows), fid[:16]))
        _, res = run_template(cfg["videoMicro"]["templateId"], cfg["videoMicro"]["versionId"],
                              fid, "one", a.auto, a.max_cost)
        seg_files = download_artifacts(res, a.out, "segment", "video", ".mp4")
        final = os.path.join(a.out, "shortdrama.mp4")

    # post-run aspect check: prove the 9:16 promise instead of assuming it
    bad = []
    for s in seg_files:
        wh = av_size(s)
        ok = bool(wh) and abs(wh[0] / wh[1] - AR_916) < 0.06
        print("  %s %s 9:16=%s" % (os.path.basename(s), ("%dx%d" % wh) if wh else "?", ok))
        if not ok: bad.append(os.path.basename(s))
    if bad:
        print("  [WARN] 以下段不是 9:16（引擎按首帧比例出片）: %s" % ", ".join(bad))

    # concat
    concat = os.path.join(a.out, "concat.txt")
    with open(concat, "w") as f:
        for s in seg_files: f.write("file '%s'\n" % os.path.abspath(s))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
                    "-i", concat, "-c", "copy", final], capture_output=True)
    wh = av_size(final)
    if not wh:
        sys.exit("[断链] 拼接后的成片无法读取")
    print("  DONE ->", final, "%.2fs" % (av_duration(final) or -1), wh)

if __name__ == "__main__":
    main()
