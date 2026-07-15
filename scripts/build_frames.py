#!/usr/bin/env python3
"""
Build synthetic frame sequence for Nitro V15 scroll site.
Creates a multi-chapter scroll film from still images using:
 - Ken Burns zoom/pan effects per chapter
 - Cross-fade transitions between chapters
 - Vignette overlays
 - Outputs WebP frames + manifest

Windows: python scripts/build_frames.py
Requires: pip install Pillow
"""

import os
import json
import math
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

# Config
PROJECT = Path(__file__).parent.parent
ASSETS = PROJECT / "assets"
FRAMES_DIR = PROJECT / "frames"
FRAME_W = 1400
FRAME_H = 788  # 16:9 approx
FPS = 12
XFADE = 0.4  # seconds crossfade

# Chapter definitions: (image_name, duration_secs, zoom_start, zoom_end, pan_x, pan_y)
# zoom: 1.0 = fill, >1 = zoomed in. pan: (-1..1) relative crop offset
CHAPTERS = [
    # ch0: hero materializes — slow zoom out from center
    {"name": "hero",      "file": "hero.png",     "dur": 6, "z0": 1.25, "z1": 1.0,  "px0": 0.0,  "py0": 0.0,  "px1": 0.0,  "py1": 0.0},
    # ch1: keyboard RGB - pan right to left across keys
    {"name": "keyboard",  "file": "keyboard.png", "dur": 6, "z0": 1.1,  "z1": 1.2,  "px0": -0.1, "py0": 0.05, "px1": 0.1,  "py1": -0.05},
    # ch2: display blast - zoom in on screen
    {"name": "display",   "file": "display.png",  "dur": 6, "z0": 1.0,  "z1": 1.3,  "px0": 0.0,  "py0": 0.0,  "px1": 0.0,  "py1": -0.05},
    # ch3: cooling vents - rise up slightly
    {"name": "cooling",   "file": "cooling.png",  "dur": 5, "z0": 1.15, "z1": 1.05, "px0": 0.0,  "py0": 0.1,  "px1": 0.0,  "py1": -0.05},
    # ch4: side profile - pull back
    {"name": "side",      "file": "side.png",     "dur": 5, "z0": 1.2,  "z1": 1.0,  "px0": -0.05,"py0": 0.0,  "px1": 0.05, "py1": 0.0},
    # ch5: hero return - push in slow to finish
    {"name": "hero_fin",  "file": "hero.png",     "dur": 6, "z0": 1.0,  "z1": 1.1,  "px0": 0.0,  "py0": 0.0,  "px1": 0.0,  "py1": 0.0},
]


def ease_inout(t):
    """Cubic ease in-out."""
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def add_vignette(img):
    """Apply dark edge vignette to a PIL Image."""
    w, h = img.size
    vig = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vig)
    # radial gradient approximation using concentric ellipses
    steps = 30
    for i in range(steps, 0, -1):
        t = i / steps
        alpha = int((1 - t) ** 1.8 * 200)
        x0 = int(w * (1 - t) * 0.5)
        y0 = int(h * (1 - t) * 0.5)
        x1 = w - x0
        y1 = h - y0
        draw.ellipse([x0, y0, x1, y1], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")


def add_top_bottom_gradient(img):
    """Darken top and bottom edges."""
    w, h = img.size
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(grad)
    band = h // 5
    for y in range(band):
        alpha = int((1 - y / band) ** 2 * 160)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        draw.line([(0, h - 1 - y), (w, h - 1 - y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), grad).convert("RGB")


def crop_frame(img, zoom, px, py):
    """Crop with zoom + pan. zoom>=1 means zoomed in."""
    ow, oh = img.size
    cw = int(ow / zoom)
    ch = int(oh / zoom)
    # pan offsets in pixels, centered
    max_dx = (ow - cw) // 2
    max_dy = (oh - ch) // 2
    cx = ow // 2 + int(px * max_dx) - cw // 2
    cy = oh // 2 + int(py * max_dy) - ch // 2
    # clamp
    cx = max(0, min(ow - cw, cx))
    cy = max(0, min(oh - ch, cy))
    cropped = img.crop((cx, cy, cx + cw, cy + ch))
    return cropped.resize((FRAME_W, FRAME_H), Image.LANCZOS)


def generate_chapter_frames(ch_cfg, loaded_imgs):
    """Generate all frames for a single chapter."""
    img = loaded_imgs[ch_cfg["file"]]
    dur = ch_cfg["dur"]
    n_frames = int(dur * FPS)
    frames = []
    for i in range(n_frames):
        t = ease_inout(i / max(n_frames - 1, 1))
        zoom = lerp(ch_cfg["z0"], ch_cfg["z1"], t)
        px = lerp(ch_cfg["px0"], ch_cfg["px1"], t)
        py = lerp(ch_cfg["py0"], ch_cfg["py1"], t)
        frame = crop_frame(img, zoom, px, py)
        frame = add_vignette(frame)
        frame = add_top_bottom_gradient(frame)
        frames.append(frame)
    return frames


def crossfade(frames_a, frames_b, xfade_frames):
    """Blend the tail of frames_a with the head of frames_b."""
    n = min(xfade_frames, len(frames_a), len(frames_b))
    merged = frames_a[:-n].copy()
    for i in range(n):
        t = (i + 1) / (n + 1)
        blended = Image.blend(frames_a[-n + i], frames_b[i], alpha=t)
        merged.append(blended)
    merged.extend(frames_b[n:])
    return merged


def main():
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    # Clear old frames
    for f in FRAMES_DIR.iterdir():
        if f.suffix in (".webp", ".png", ".json"):
            f.unlink()

    print("Loading source images...")
    loaded_imgs = {}
    for ch in CHAPTERS:
        fname = ch["file"]
        if fname not in loaded_imgs:
            path = ASSETS / fname
            if not path.exists():
                raise FileNotFoundError(f"Missing asset: {path}")
            img = Image.open(path).convert("RGB")
            # Upscale to ensure enough resolution for all zoom ops
            scale = max(FRAME_W / img.width, FRAME_H / img.height) * 1.35
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            loaded_imgs[fname] = img
            print(f"  Loaded {fname}: {img.size}")

    print("\nGenerating chapter frames...")
    xfade_frames = int(XFADE * FPS)

    chapter_frames = []
    chapter_meta = []
    total_before = 0

    for i, ch in enumerate(CHAPTERS):
        frames = generate_chapter_frames(ch, loaded_imgs)
        chapter_meta.append({"name": ch["name"], "start_frame": total_before})
        total_before += len(frames) - xfade_frames if i > 0 else len(frames)
        chapter_frames.append(frames)
        print(f"  Chapter '{ch['name']}': {len(frames)} frames")

    # Merge with crossfades
    print("\nMerging with crossfades...")
    all_frames = chapter_frames[0]
    for i in range(1, len(chapter_frames)):
        all_frames = crossfade(all_frames, chapter_frames[i], xfade_frames)

    total = len(all_frames)
    print(f"\nTotal frames: {total}")

    # Save as WebP
    print("\nSaving WebP frames...")
    for idx, frame in enumerate(all_frames):
        out = FRAMES_DIR / f"frame_{idx + 1:04d}.webp"
        frame.save(str(out), "WEBP", quality=84)
        if idx % 20 == 0:
            print(f"  {idx + 1}/{total}")

    # Manifest
    manifest = {"count": total, "pattern": "frames/frame_%04d.webp"}
    (FRAMES_DIR / "frames.json").write_text(json.dumps(manifest))

    size_mb = sum(f.stat().st_size for f in FRAMES_DIR.iterdir() if f.suffix == ".webp") / 1e6
    print(f"\nDone! {total} frames, {size_mb:.1f} MB total")

    print("\nChapter scroll fractions (for caption calibration):")
    for m in chapter_meta:
        frac = m["start_frame"] / total
        print(f"  {m['name']:<12}  frame {m['start_frame']:4d}  →  scroll {frac:.3f}")


if __name__ == "__main__":
    main()
