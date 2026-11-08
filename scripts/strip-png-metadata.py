#!/usr/bin/env python3
"""Remove text, XMP, EXIF, timestamp and vendor chunks from a PNG without touching its pixels.

Usage: python3 scripts/strip-png-metadata.py SOURCE.png DESTINATION.png

macOS screenshots carry XMP and Apple-specific chunks, which the publication audit rejects.
Only image-defining and colour chunks are kept; compressed image data is copied byte for byte.
The destination must not exist, so an original is never overwritten.
"""
import struct
import sys
from pathlib import Path
import zlib

SIGNATURE = b'\x89PNG\r\n\x1a\n'
KEEP = {b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND', b'sRGB', b'gAMA', b'cHRM', b'iCCP', b'pHYs'}


def chunks(data):
    if not data.startswith(SIGNATURE):
        raise ValueError('not a PNG file')
    offset, result = len(SIGNATURE), []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError('truncated chunk header')
        size, kind = struct.unpack('>I', data[offset:offset + 4])[0], data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = data[offset + 8 + size:offset + 12 + size]
        if len(payload) != size or len(crc) != 4 or zlib.crc32(kind + payload) != struct.unpack('>I', crc)[0]:
            raise ValueError(f'corrupt {kind.decode(errors="replace")} chunk')
        result.append((kind, payload)); offset += size + 12
    if not result or result[0][0] != b'IHDR' or result[-1][0] != b'IEND':
        raise ValueError('incomplete PNG')
    return result


def strip(data):
    """Return (clean PNG bytes, names of removed chunks)."""
    kept, removed = [], []
    for kind, payload in chunks(data):
        if kind in KEEP:
            kept.append(struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload)))
        else:
            removed.append(kind.decode('latin-1'))
    return SIGNATURE + b''.join(kept), removed


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__.strip()); return 2
    source, destination = Path(args[0]), Path(args[1])
    if destination.exists():
        print(f'Refusing to overwrite {destination.name}; choose a new file name.'); return 2
    try:
        cleaned, removed = strip(source.read_bytes())
    except (OSError, ValueError) as error:
        print(f'Could not read {source.name}: {error}'); return 1
    destination.write_bytes(cleaned)
    width, height = struct.unpack('>II', cleaned[16:24])
    print(f'{destination.name}: {width} × {height} px; removed {", ".join(removed) or "nothing"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
