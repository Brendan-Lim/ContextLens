#!/usr/bin/env python3
import argparse
import json
from dmg import build

parser = argparse.ArgumentParser(description='Build and mount-verify a Finder installer from one signed app.')
parser.add_argument('app')
parser.add_argument('output')
args = parser.parse_args()
print(json.dumps(build(args.app, args.output), indent=2))
