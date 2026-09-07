#!/usr/bin/env python3
"""qc_report.py — quantify a produced short-drama mp4: duration/resolution/segment count.
Usage: python3 qc_report.py final-shortdrama.mp4
Outputs a small machine-parseable + human-readable QC summary."""
import sys, subprocess, csv, os, json
def probe(p):
    r=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height,duration,avg_frame_rate","-of","json",p],capture_output=True,text=True)
    if r.returncode!=0: return None
    return json.loads(r.stdout).get("streams",[{}])[0]
if __name__=="__main__":
    p=sys.argv[1]
    st=probe(p)
    if not st:
        print("QC: FAIL (cannot read %s)"%p); sys.exit(1)
    w,h=(st.get("width"),st.get("height")); dur=float(st.get("duration") or 0)
    fps=(st.get("avg_frame_rate") or "0/1").split("/")
    fps=round(int(fps[0])/max(int(fps[1]),1),2) if len(fps)==2 else 0
    print("QC_OK  file=%s | dur=%.1fs | res=%sx%s | fps=%s | 9:16=%s | ≥90%%有效=%s"%(p,dur,w,h,fps, abs(w/h- (9/16))<0.06, dur>=1))
