#!/usr/bin/env python3
"""Render two original installer compositions and a README hero without UI automation."""
import argparse
from pathlib import Path
import subprocess
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
args = parser.parse_args()
subprocess.run(['swift', '-module-cache-path', '.build/ModuleCache',
                str(Path(__file__).with_name('render.swift')), str(args.output.resolve())], check=True)
pairs = []
for image in args.output.glob('*.png'):
    if image.name.endswith('.optimized.png'):
        continue
    optimized = image.with_suffix('.optimized.png')
    # Xcode's old pngcrush can corrupt RGBA->RGB reduction. Preserve color type,
    # then compare every decoded pixel before accepting an optimized asset.
    subprocess.run(['xcrun', 'pngcrush', '-q', '-c', '6', str(image), str(optimized)], check=True)
    pairs.extend([str(image), str(optimized)])
subprocess.run(['swift', '-module-cache-path', '.build/ModuleCache',
                str(Path(__file__).with_name('verify-pixels.swift')), *pairs], check=True)
for original, compressed in zip(pairs[::2], pairs[1::2]):
    image, optimized = Path(original), Path(compressed)
    os.replace(optimized, image)
