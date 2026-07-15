#!/usr/bin/env python3
"""
Wrapper: reads build_config.json and calls build_master.main()
Run: python scripts/run_build.py
"""
import json, sys
from pathlib import Path

# Patch sys.argv so build_master.main() gets the config
cfg_path = Path(__file__).parent / "build_config.json"
cfg = cfg_path.read_text(encoding="utf-8")
sys.argv = [sys.argv[0], cfg]

# Run build
import build_master
build_master.main()
