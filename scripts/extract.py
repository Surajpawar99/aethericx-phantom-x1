#!/usr/bin/env python3
"""Extract a clip into a WebP frame sequence + manifest for the Next app.

  python scripts/extract.py <clip.mp4> <out_dir> [--fps 12] [--width 1280] [--reverse]

Windows notes:
  - Use `python` (not python3)
  - ffmpeg must be on PATH (install via: winget install ffmpeg)
  - Use full absolute paths for clip and out_dir
  - Pillow handles PNG->WebP conversion (pip install Pillow)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image


def main():
    clip = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    fps = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 12
    width = int(sys.argv[sys.argv.index("--width") + 1]) if "--width" in sys.argv else 1280
    reverse = "--reverse" in sys.argv

    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.iterdir():
        if f.suffix in (".png", ".webp"):
            f.unlink()

    vf = f"fps={fps},scale={width}:-2" + (",reverse" if reverse else "")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vf", vf,
         str(out_dir / "frame_%03d.png")],
        check=True
    )

    pngs = sorted(f for f in out_dir.iterdir() if f.suffix == ".png")
    for p in pngs:
        Image.open(p).save(p.with_suffix(".webp"), "WEBP", quality=80)
        p.unlink()

    name = out_dir.name
    manifest = {"count": len(pngs), "pattern": f"frames/{name}/frame_%03d.webp"}
    (out_dir / "manifest.json").write_text(json.dumps(manifest))
    size = sum(f.stat().st_size for f in out_dir.iterdir()) / 1e6
    print(f"{name}: {len(pngs)} frames, {size:.1f} MB")


if __name__ == "__main__":
    main()
