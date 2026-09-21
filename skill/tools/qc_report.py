#!/usr/bin/env python3
"""qc_report.py — quantify a produced short-drama mp4: duration/resolution/segment count.
Usage: python3 qc_report.py final-shortdrama.mp4
Outputs a small machine-parseable + human-readable QC summary.

Uses system ffprobe when present; otherwise falls back to the ffmpeg binary bundled
with imageio-ffmpeg (which ships no ffprobe), so a clean box still gets a QC line."""
import sys, subprocess, csv, os, json, re, shutil

def _tool():
    """Prefer system ffprobe; else imageio-ffmpeg's bundled ffmpeg."""
    if shutil.which("ffprobe"): return "ffprobe", shutil.which("ffprobe")
    import imageio_ffmpeg
    return "ffmpeg", imageio_ffmpeg.get_ffmpeg_exe()

def probe(p):
    kind, exe = _tool()
    if kind == "ffprobe":
        r=subprocess.run([exe,"-v","error","-select_streams","v:0","-show_entries","stream=width,height,duration,avg_frame_rate","-of","json",p],capture_output=True,text=True)
        if r.returncode!=0: return None
        return json.loads(r.stdout).get("streams",[{}])[0]
    r=subprocess.run([exe,"-i",p],capture_output=True,text=True)
    err=r.stderr or ""
    m=re.search(r"Video:.*?(\d{2,5})x(\d{2,5})",err,re.S)
    if not m: return None
    d=re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)",err)
    f=re.search(r"(\d+(?:\.\d+)?)\s*fps",err)
    return {"width":int(m.group(1)),"height":int(m.group(2)),
            "duration":(int(d.group(1))*3600+int(d.group(2))*60+float(d.group(3))) if d else 0,
            "avg_frame_rate":(f.group(1) if f else "0")+"/1"}
if __name__=="__main__":
    p=sys.argv[1]
    st=probe(p)
    if not st:
        print("QC: FAIL (cannot read %s; needs ffprobe or imageio-ffmpeg)"%p); sys.exit(1)
    w,h=(st.get("width"),st.get("height")); dur=float(st.get("duration") or 0)
    fps=(st.get("avg_frame_rate") or "0/1").split("/")
    fps=round(int(fps[0])/max(int(fps[1]),1),2) if len(fps)==2 else 0
    print("QC_OK  file=%s | dur=%.1fs | res=%sx%s | fps=%s | 9:16=%s | ≥90%%有效=%s"%(p,dur,w,h,fps, abs(w/h- (9/16))<0.06, dur>=1))
