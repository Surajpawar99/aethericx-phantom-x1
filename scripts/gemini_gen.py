#!/usr/bin/env python3
"""
Gemini Omni Flash pipeline client — image & video generation for scroll-site-generator.

Usage (Windows PowerShell):
  python scripts/gemini_gen.py image '<json>'
    e.g.: python scripts/gemini_gen.py image '{"name":"hero","prompt":"...","out":"C:\\project\\assets\\hero.png"}'

  python scripts/gemini_gen.py video '<json>'
    e.g.: python scripts/gemini_gen.py video '{"name":"ch1","prompt":"...","image_path":"C:\\project\\assets\\hero.png","out":"C:\\project\\assets\\clips\\ch1.mp4"}'

Environment:
  GEMINI_API_KEY in env or in .env file next to this script's project root.

Models:
  Image: gemini-2.0-flash-preview-image-generation  (default, free tier)
         imagen-3.0-generate-002                    (higher quality)
  Video: veo-2.0-generate-001                       (stable, default)
         veo-3.0-generate-preview                   (latest, may need billing)

Install dependencies:
  pip install google-genai pillow requests
"""

import sys
import os
import json
import time
import base64
from pathlib import Path

# ---------------------------------------------------------------------------
# Env / key loading
# ---------------------------------------------------------------------------

PROJECT = Path(__file__).parent.parent

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env_path = PROJECT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        print("ERROR: GEMINI_API_KEY not found in env or .env file.")
        print("Get a key at: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    return key


def get_client():
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai not installed. Run: pip install google-genai")
        sys.exit(1)
    return genai.Client(api_key=get_api_key())


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------

def gen_image(spec: dict):
    """
    spec keys:
      name        str   — filename stem
      prompt      str   — image prompt
      model       str?  — default: gemini-2.0-flash-preview-image-generation
      aspect_ratio str? — "16:9" (default), "1:1", "9:16"
      out         str?  — absolute output path (.png); default: assets/<name>.png
    """
    from google import genai
    from google.genai import types
    from PIL import Image
    import io

    client = get_client()
    model = spec.get("model", "gemini-2.0-flash-preview-image-generation")
    prompt = spec["prompt"]
    aspect_ratio = spec.get("aspect_ratio", "16:9")
    out_path = Path(spec["out"]) if spec.get("out") else PROJECT / "assets" / f"{spec['name']}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[image] {spec['name']} → {model}")

    try:
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_only_high",
                person_generation="allow_adult",
            ),
        )
        if not response.generated_images:
            print("ERROR: No images returned.")
            return None

        image_bytes = response.generated_images[0].image.image_bytes
        img = Image.open(io.BytesIO(image_bytes))
        img.save(str(out_path), "PNG")
        print(f"[image] saved: {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"[image] ERROR: {e}")
        return None


# ---------------------------------------------------------------------------
# Video generation (Gemini Veo — Omni Flash)
# ---------------------------------------------------------------------------

def gen_video(spec: dict):
    """
    spec keys:
      name          str   — filename stem
      prompt        str   — video prompt
      image_path    str?  — absolute path to anchor still (image-to-video)
      model         str?  — default: veo-2.0-generate-001
      duration_seconds int? — 5 or 8 (default 5)
      aspect_ratio  str?  — "16:9" (default), "9:16"
      negative_prompt str? — optional negative prompt
      out           str?  — absolute output path (.mp4); default: assets/clips/<name>.mp4
    """
    from google import genai
    from google.genai import types

    client = get_client()
    model = spec.get("model", "veo-2.0-generate-001")
    prompt = spec["prompt"]
    duration = spec.get("duration_seconds", 5)
    aspect_ratio = spec.get("aspect_ratio", "16:9")
    out_path = Path(spec["out"]) if spec.get("out") else PROJECT / "assets" / "clips" / f"{spec['name']}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[video] {spec['name']} → {model}  ({duration}s, {aspect_ratio})")

    # Build image input if provided
    image_input = None
    if spec.get("image_path"):
        img_path = Path(spec["image_path"])
        if not img_path.exists():
            print(f"ERROR: image_path not found: {img_path}")
            return None
        image_data = img_path.read_bytes()
        # Detect mime type
        suffix = img_path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/webp"
        image_input = types.Image(image_bytes=image_data, mime_type=mime)

    try:
        config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            duration_seconds=duration,
        )
        if spec.get("negative_prompt"):
            config.negative_prompt = spec["negative_prompt"]

        if image_input:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                image=image_input,
                config=config,
            )
        else:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=config,
            )

        print(f"[video] queued: {operation.name} — polling (2-5 min)...")

        # Poll until done
        timeout = 600
        start = time.time()
        while not operation.done:
            if time.time() - start > timeout:
                print(f"[video] TIMEOUT after {timeout}s")
                return None
            elapsed = int(time.time() - start)
            print(f"[video] waiting... ({elapsed}s)")
            time.sleep(15)
            operation = client.operations.get(operation)

        # Download result
        videos = operation.response.generated_videos
        if not videos:
            print("[video] ERROR: No videos in response.")
            return None

        video_uri = videos[0].video.uri
        print(f"[video] downloading: {video_uri}")
        client.files.download(file=video_uri, download_path=str(out_path))
        print(f"[video] saved: {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"[video] ERROR: {e}")
        return None


# ---------------------------------------------------------------------------
# Extract last frame from a clip (for chaining chapters)
# ---------------------------------------------------------------------------

def extract_last_frame(clip_path: str, out_path: str):
    """Extract the last frame of a clip for use as next chapter anchor."""
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-sseof", "-0.1",
        "-i", clip_path,
        "-frames:v", "1",
        out_path
    ]
    print(f"[extract] {clip_path} → {out_path}")
    subprocess.run(cmd, check=True)
    print(f"[extract] saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        spec = json.loads(sys.argv[2])
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}")
        sys.exit(1)

    if cmd == "image":
        result = gen_image(spec)
    elif cmd == "video":
        result = gen_video(spec)
    elif cmd == "last-frame":
        # python gemini_gen.py last-frame '{"clip":"path.mp4","out":"frame.png"}'
        result = extract_last_frame(spec["clip"], spec["out"])
    else:
        print(f"Unknown command: {cmd}")
        print("Valid commands: image, video, last-frame")
        sys.exit(1)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
