#!/usr/bin/env python3
"""editor_to_images.py — generate scene keyframes via LoomKeyframe Editor (image-to-image, RMB).

Bridge between "no usable photos" and the video micro engine: take one character anchor photo
and N edit prompts, call the Loom `ShortDrama Keyframe Editor` template on 旧账号, download the
edited PNGs to out-dir so run_one / a user can pass them as --photos-dir.

Uses only LoomLoom (CNY). Never WorkBuddy credits or other agents' local image models.

Usage:
  python editor_to_images.py --ref <anchor.png> --prompts "p1" "p2" --out <dir> [--confirm]
"""
import argparse, json, os, subprocess, sys, time, urllib.request

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOM  = "loomloom"

def cfg():
    try:
        return json.load(open(os.path.join(SKILL, "config.runtime.json"), encoding="utf-8"))
    except FileNotFoundError:
        sys.exit("缺少 config.runtime.json（私有 handle，本地）")

def loom(*a):
    subprocess.run([LOOM, "server", "use", "shengsuanyun"], capture_output=True)
    p = subprocess.run([LOOM]+[str(x) for x in a]+["--output", "json"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("loom %s: %s" % (str(list(a)[:2]), (p.stderr or p.stdout)[:220]))
    return json.loads(p.stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="anchor character photo")
    ap.add_argument("--prompts", nargs="+", required=True)
    ap.add_argument("--out", default="keyframes")
    ap.add_argument("--auto", action="store_true")
    a = ap.parse_args()
    ed = cfg()["imageEditor"]                        # Loom editor: photo+editPrompt
    os.makedirs(a.out, exist_ok=True)

    asset = loom("input-asset", "upload", a.ref)["inputAssetId"]
    rows  = [{"photo": asset, "editPrompt": p} for p in a.prompts]
    jsonl = os.path.join(a.out, "edit_rows.jsonl")
    with open(jsonl, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    fid = loom("orchestration-input", "upload", jsonl)["inputFileId"]

    pre = loom("template-spec", "precheck", ed["templateId"], "--version-id", ed["versionId"],
               "--input-file-id", fid)["precheck"]
    print("图片关键帧: %d 张 | 云预估 %s %s（人民币）" % (
        len(rows), pre["estimatedTotalCost"]["amount"], pre["estimatedTotalCost"]["currency"]))
    if not a.auto:
        sys.exit("确认成本后加 --auto 执行（本工具只走 Loom/人民币）")

    run  = loom("template-spec", "run", ed["templateId"], "--version-id", ed["versionId"],
                "--input-file-id", fid, "--client-request-id", "kg-%d" % int(time.time()))
    rid  = run["runId"]
    print("已提交 runId", rid)
    loom("run", "watch", rid)
    for i, rr in enumerate(loom("run", "result-rows", rid).get("rows", []), start=1):
        for art in rr.get("artifacts", []):
            if art.get("mimeType", "").startswith("image"):
                p = os.path.join(a.out, "keyframe_%02d.png" % i)
                urllib.request.urlretrieve(art["accessUrl"], p)
                print("  关键帧 ->", p)
    print("DONE：把 %s 作为 --frames-dir 喂给 run_one 即可继续出片。" % a.out)

if __name__ == "__main__":
    main()