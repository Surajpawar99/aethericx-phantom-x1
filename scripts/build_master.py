#!/usr/bin/env python3
"""
Crossfade-concat chapter clips into a master film, slice into WebP scrub
frames, and emit a manifest + chapter scroll fractions for captions.

  python scripts/build_master.py '<config-json>'

Config:
{
  "clips_dir":  "C:\\abs\\path\\assets\\clips",
  "frames_dir": "C:\\abs\\path\\frames",
  "master":     "C:\\abs\\path\\assets\\master.mp4",
  "fps": 12, "width": 1400, "xfade": 0.4,
  "chapters": [
    {"name": "beans",    "file": "ch1-beans.mp4"},
    {"name": "assembly", "file": "ch2-explode.mp4", "reverse": true},
    ...
  ]
}

Windows notes:
  - Use `python` (not python3)
  - Use double backslashes or raw strings in JSON paths
  - ffmpeg must be on PATH (install via: winget install ffmpeg)
  - Pillow handles PNG→WebP conversion (pip install Pillow)

Reversed chapters are cached as <file>-rev.mp4. ffmpeg builds without a
WebP encoder are handled by extracting PNG and converting via Pillow.
Prints per-chapter scroll fractions — use them to calibrate caption
data-in/hold/out values in the site.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image


def run(cmd):
    print("+", " ".join(str(c) for c in cmd[:8]), "..." if len(cmd) > 8 else "")
    subprocess.run([str(c) for c in cmd], check=True)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def main():
    cfg = json.loads(sys.argv[1])
    clips_dir = Path(cfg["clips_dir"])
    frames_dir = Path(cfg["frames_dir"])
    master = Path(cfg["master"])
    fps = cfg.get("fps", 12)
    width = cfg.get("width", 1400)
    xfade = cfg.get("xfade", 0.4)

    inputs = []
    for ch in cfg["chapters"]:
        src = clips_dir / ch["file"]
        if not src.exists():
            sys.exit(f"missing clip: {src}")
        if ch.get("reverse"):
            revd = src.with_name(src.stem + "-rev.mp4")
            if not revd.exists():
                run(["ffmpeg", "-y", "-v", "error", "-i", src,
                     "-vf", "reverse", "-an", "-crf", "16", revd])
            src = revd
        inputs.append((ch["name"], src, duration(src)))

    args = ["ffmpeg", "-y", "-v", "error"]
    for _, src, _ in inputs:
        args += ["-i", str(src)]

    # Normalize every input to the first clip's geometry
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "stream=width,height", "-of", "csv=p=0",
         str(inputs[0][1])], capture_output=True, text=True, check=True)
    W, H = probe.stdout.strip().split(",")
    filters = []
    for i in range(len(inputs)):
        filters.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps=24,setsar=1[n{i}]")

    meta = [{"name": inputs[0][0], "start": 0.0}]
    prev, prev_end = "[n0]", inputs[0][2]
    for i in range(1, len(inputs)):
        name, _, dur = inputs[i]
        offset = prev_end - xfade
        out = f"[v{i}]"
        filters.append(
            f"{prev}[n{i}]xfade=transition=fade:duration={xfade}:offset={offset:.4f}{out}")
        meta.append({"name": name, "start": offset})
        prev, prev_end = out, offset + dur
    total = prev_end

    master.parent.mkdir(parents=True, exist_ok=True)
    args += ["-filter_complex", ";".join(filters), "-map", prev]
    args += ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(master)]
    run(args)

    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.iterdir():
        if f.suffix in (".webp", ".png"):
            f.unlink()

    run(["ffmpeg", "-y", "-v", "error", "-i", str(master),
         "-vf", f"fps={fps},scale={width}:-2",
         str(frames_dir / "frame_%04d.png")])

    pngs = sorted(f for f in frames_dir.iterdir() if f.suffix == ".png")
    for p in pngs:
        Image.open(p).save(p.with_suffix(".webp"), "WEBP", quality=82)
        p.unlink()

    manifest = {"count": len(pngs), "pattern": "frames/frame_%04d.webp"}
    (frames_dir / "frames.json").write_text(json.dumps(manifest))

    size = sum(f.stat().st_size for f in frames_dir.iterdir()) / 1e6
    print(f"\nmaster: {total:.1f}s → {len(pngs)} frames, {size:.1f} MB")
    print("\nchapter scroll fractions (calibrate captions with these):")
    for m in meta:
        print(f"  {m['name']:<12} starts at {m['start'] / total:.3f}")


if __name__ == "__main__":
    main()
