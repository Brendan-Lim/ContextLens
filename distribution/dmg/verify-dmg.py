#!/usr/bin/env python3
import argparse
import json
from dmg import verify_dmg

parser = argparse.ArgumentParser(description='Mount, verify, copy and detach a disk image without opening Finder.')
parser.add_argument('image')
parser.add_argument('--app', help='Compare every normalized bundle file to the ZIP source bundle')
args = parser.parse_args()
print(json.dumps(verify_dmg(args.image, args.app, install_copy=True), indent=2))
