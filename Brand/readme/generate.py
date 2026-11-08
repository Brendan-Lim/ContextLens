#!/usr/bin/env python3
"""Render the README's decorative brand artwork and optimize it without changing a pixel.

Usage: python3 Brand/readme/generate.py docs/media/readme
The output is brand artwork, not a screenshot. Add each file's reviewed SHA-256 to
config/publication-policy.json before committing it.
"""
import argparse
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
args = parser.parse_args()
cache = str(ROOT / '.build' / 'ModuleCache')
subprocess.run(['swift', '-module-cache-path', cache, str(HERE / 'render.swift'), str(args.output.resolve())], check=True)
pairs = []
for image in sorted(args.output.glob('*.png')):
    if image.name.endswith('.optimized.png'):
        continue
    optimized = image.with_suffix('.optimized.png')
    # Same guard as the DMG backgrounds: keep the colour type, then compare every decoded pixel.
    subprocess.run(['xcrun', 'pngcrush', '-q', '-c', '6', str(image), str(optimized)], check=True)
    pairs.extend([str(image), str(optimized)])
subprocess.run(['swift', '-module-cache-path', cache,
                str(ROOT / 'distribution' / 'dmg' / 'verify-pixels.swift'), *pairs], check=True)
for original, optimized in zip(pairs[::2], pairs[1::2]):
    os.replace(optimized, original)
