# 🎮 Aethericx Phantom X1 — 3D Scroll Product Showcase

An ultra-premium, interactive 3D scroll-driven product landing page for the fictional **Aethericx Phantom X1** gaming laptop. Built with vanilla HTML, CSS, and JavaScript, featuring a highly-optimized, mobile-responsive canvas image-sequence scrubber inspired by Apple's product showcase pages.

---

## ✨ Features

- **🎬 Apple-Style Scrubber:** Smooth, physics-based frame interpolation mapping your scroll position directly to a 480-frame silent video sequence.
- **🎨 Premium Dark Aesthetic:** Built on a deep near-black (`#080608`) canvas accented with bright crimson (`#dc1e32`) glowing indicators and futuristic Rajdhani headlines.
- **📱 Fully Mobile Responsive:** Custom-designed full-screen blurred menu overlay (`backdrop-filter: blur(28px)`) with adaptive centered captions and optimized layout for portrait mobile screens.
- **📽️ AI-Generated Cinematic Assets:** All video frames generated using **Gemini Veo** (via Google AI Studio) and processed with custom Python scripts to ensure frame-to-frame consistency.
- **🗺️ Complete Brand Homepage:** Outro scroll section includes a full landing page featuring a manifesto, origin story, 3 detailed craft chapters, interactive specs sheet, quote section, and a responsive media gallery.

---

## 🛠️ Tech Stack

- **Frontend:** Vanilla HTML5, CSS3, ES6 JavaScript, Canvas API.
- **Animation Engine:** Time-based lerp (`1 - exp(-dt * 14)`) for scroll smoothing and IntersectionObserver for section reveal animations.
- **Asset Pipeline:** 
  - **Google AI Studio (Veo):** Image-to-video frames generation.
  - **FFmpeg:** Video crossfade concatenation, audio stripping, and frame extraction.
  - **Pillow (Python PIL):** WebP conversion, Ken Burns panning/zooming, vignette overlays, and resolution optimization.

---

## 📁 File Structure

```
aethericx-phantom-x1/
├── index.html          # Main website (film sequence + brand sections)
├── main.js             # Physics-based canvas frame scrubber engine
├── frames/             # 480 WebP frames + frames.json manifest
├── assets/             # Still assets (original AI renders)
│   ├── hero.png
│   ├── keyboard.png
│   ├── display.png
│   ├── cooling.png
│   └── side.png
└── scripts/            # Build tools
    ├── build_frames.py # Fallback frame builder with Ken Burns pan/zoom
    ├── run_build.py    # Wrapper to launch build_master
    └── build_master.py # Main FFmpeg slicing & conversion script
```

---

## 🚀 Local Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/Surajpawar99/aethericx-phantom-x1.git
   cd aethericx-phantom-x1
   ```

2. Start a local HTTP server:
   ```bash
   # Using Python
   python -m http.server 8090
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:8090
   ```

---

## 🎨 Asset Generation Prompts (Gemini Veo)

The cinematic sequence consists of 6 core chapters. If you want to regenerate individual video clips inside `assets/clips/`, use these prompt templates in Google AI Studio:

- **Ch 1 (Hero Reveal):** `The Aethericx gaming laptop slowly materializes from complete darkness, emerging into dramatic crimson rim lighting...`
- **Ch 2 (Keyboard):** `Close-up aerial top-down view of the gaming laptop keyboard. A wave of vivid crimson and red RGB light sweeps slowly...`
- **Ch 3 (Display):** `The gaming laptop screen displays an explosive burst of neon light rays in deep blue, purple, and crimson...`
- **Ch 4 (Cooling):** `Close-up rear view of a gaming laptop's dual exhaust cooling vents. Subtle heat shimmer rises...`

*(Full prompts and negative tokens can be found in `PROJECT_MEMORY.md`)*

---

## 📜 License

Created as a concept design showcase. All assets and imagery are AI-generated.
Designed by **Aethericx** & built with Gemini.
