#!/usr/bin/env python3
"""Fail-closed macOS bundle verification, notarization and final-byte packaging."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def metadata(version=None):
    data = json.loads((ROOT / 'config/version.json').read_text())
    require(isinstance(data['version'], str) and VERSION.fullmatch(data['version']), 'Version must be X.Y.Z, without leading zeros or suffixes')
    require(type(data['build']) is int and data['build'] > 0, 'Build must be a positive integer')
    require(data['bundleID'] == 'dev.contextlens.app', 'Do not change the established bundle identity')
    require(data['minimumMacOS'] == '14.0', 'Deployment target must agree with Package.swift and the cask')
    if version is not None:
        require(version == data['version'], 'Requested version differs from config/version.json')
    return data


def run(*args):
    result = subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def write_plist(path):
    data = metadata()
    info = dict(CFBundleName='ContextLens', CFBundleDisplayName='ContextLens',
                CFBundleIdentifier=data['bundleID'], CFBundleVersion=str(data['build']),
                CFBundleShortVersionString=data['version'], CFBundleIconFile='AppIcon',
                CFBundleExecutable='ContextLens', CFBundlePackageType='APPL',
                LSMinimumSystemVersion=data['minimumMacOS'], NSHighResolutionCapable=True,
                NSScreenCaptureUsageDescription='Capture only the window you select to prepare local visual context for your coding agent.')
    Path(path).write_bytes(plistlib.dumps(info, sort_keys=True))


def verify(app, mode='development', notarized=False):
    app = Path(app).resolve()
    data = metadata()
    require(app.name == 'ContextLens.app', 'Expected ContextLens.app')
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    for key, expected in [('CFBundleIdentifier', data['bundleID']), ('CFBundleShortVersionString', data['version']),
                          ('CFBundleVersion', str(data['build'])), ('LSMinimumSystemVersion', data['minimumMacOS']),
                          ('CFBundleExecutable', 'ContextLens'), ('CFBundlePackageType', 'APPL'), ('CFBundleIconFile', 'AppIcon')]:
        require(info.get(key) == expected, 'Bundle metadata mismatch: ' + key)
    require((app / 'Contents/Resources/AppIcon.icns').stat().st_size > 0, 'Missing icon')
    require((app / 'Contents/Resources/LICENSE').is_file(), 'Missing MIT license')
    require('NSScreenCaptureUsageDescription' in info, 'Missing screen capture usage description')
    run('codesign', '--verify', '--deep', '--strict', '--verbose=2', app)
    for name in ['ContextLens', 'contextlens-cli']:
        binary = app / 'Contents/MacOS' / name
        require(os.access(binary, os.X_OK), 'Missing executable: ' + name)
        require(run('lipo', '-archs', binary).strip() == 'arm64', 'Only arm64 distribution has been verified')
        load = run('otool', '-l', binary)
        require(re.search(r'\bminos 14\.0(?:\.0)?\b', load), 'Executable deployment target is not macOS 14.0')
        for library in run('otool', '-L', binary).splitlines()[1:]:
            path = library.strip().split(' (', 1)[0]
            require(path.startswith(('/System/Library/', '/usr/lib/', '@rpath/', '@executable_path/', '@loader_path/')), 'Nonportable linked library')
        # Read internally so a finding never prints an embedded private path.
        require(b'/Users/' not in binary.read_bytes() and b'/private/var/folders/' not in binary.read_bytes(), 'Developer-specific path embedded in executable')
        run('codesign', '--verify', '--strict', binary)
        if mode == 'distribution':
            signature = run('codesign', '-d', '--verbose=4', binary)
            team = os.environ.get('CONTEXTLENS_TEAM_ID', '')
            require(re.fullmatch(r'[A-Z0-9]{10}', team), 'CONTEXTLENS_TEAM_ID is required for distribution verification')
            require('Authority=Developer ID Application:' in signature, 'Developer ID Application signature required')
            require('TeamIdentifier=' + team + '\n' in signature, 'Unexpected signing team')
            require('runtime' in signature and 'Timestamp=' in signature, 'Hardened Runtime and secure timestamp required')
            entitlements = run('codesign', '-d', '--entitlements', '-', '--xml', binary)
            require('<key>' not in entitlements, 'This native app needs no entitlement exceptions; inspect before changing this gate')
    if notarized:
        require(mode == 'distribution', 'Notarization validation requires distribution signing')
        run('xcrun', 'stapler', 'validate', app)
        run('spctl', '--assess', '--type', 'execute', '-vv', app)
    # Assess a downloaded distribution before executing even its help command.
    help_text = run(app / 'Contents/MacOS/contextlens-cli', '--help')
    require(all(command in help_text for command in ['demo', 'validate', 'export', 'replay', 'profile', 'permissions', 'windows']), 'CLI help is incomplete')
    return data


def archive_members(path):
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            p = PurePosixPath(item.filename)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in item.filename, 'Unsafe archive path')
            require(p.parts and p.parts[0] in ['ContextLens.app', '__MACOSX'], 'Unexpected archive root')
            require((item.external_attr >> 16) & 0o170000 != 0o120000, 'Unexpected archive symlink')
        require(archive.testzip() is None, 'Archive CRC failed')
        require('ContextLens.app/Contents/MacOS/contextlens-cli' in archive.namelist(), 'CLI absent from archive')


def package(app, output, development=False):
    data = verify(app, 'development' if development else 'distribution', notarized=not development)
    dirty = bool(run('git', '-C', ROOT, 'status', '--porcelain').strip())
    require(development or not dirty, 'Distribution packaging requires a clean source checkout')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    suffix = '-development' if development else ''
    name = f"ContextLens-{data['version']}-arm64{suffix}.zip"
    target = output / name
    require(not target.exists() and not target.with_suffix('.zip.sha256').exists(), 'Archive/checksum already exists; never replace a published version')
    # ZIPs are not claimed byte-reproducible across rebuilds/signing timestamps.
    # The checksum always describes the final immutable downloadable bytes.
    with tempfile.TemporaryDirectory(prefix='.package-', dir=output) as temporary:
        staged = Path(temporary) / name
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', '--noqtn', Path(app).resolve(), staged)
        archive_members(staged)
        unpacked = Path(temporary) / 'unpacked'
        run('ditto', '-x', '-k', staged, unpacked)
        verify(unpacked / 'ContextLens.app', 'development' if development else 'distribution', notarized=not development)
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        # Hard-link creation refuses a concurrent overwrite, too.
        os.link(staged, target)
    target.with_suffix('.zip.sha256').write_text(f'{digest}  {name}\n')
    receipt = dict(version=data['version'], architecture='arm64', archive=name, sha256=digest,
                   trust='development-only' if development else 'developer-id-notarized',
                   sourceCommit=run('git', '-C', ROOT, 'rev-parse', 'HEAD').strip(), sourceDirty=dirty)
    target.with_suffix('.zip.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return target


def verify_archive(path):
    path = Path(path).resolve()
    data = metadata()
    require(path.name == f"ContextLens-{data['version']}-arm64.zip", 'Unexpected release asset name')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(path.with_suffix('.zip.sha256').read_text().strip() == f'{digest}  {path.name}', 'Downloaded checksum does not match final archive')
    receipt = json.loads(path.with_suffix('.zip.json').read_text())
    require(receipt.get('sha256') == digest and receipt.get('trust') == 'developer-id-notarized', 'Release receipt mismatch')
    require(receipt.get('sourceDirty') is False, 'Distribution receipt must record a clean source checkout')
    require(receipt.get('version') == data['version'] and receipt.get('architecture') == 'arm64', 'Release receipt metadata mismatch')
    archive_members(path)
    with tempfile.TemporaryDirectory(prefix='contextlens-verify-') as temporary:
        run('ditto', '-x', '-k', path, temporary)
        verify(Path(temporary) / 'ContextLens.app', 'distribution', notarized=True)
    return receipt


def preflight(version):
    metadata(version)
    require(not run('git', '-C', ROOT, 'status', '--porcelain').strip(), 'Release requires a clean source checkout')
    require(run('git', '-C', ROOT, 'branch', '--show-current').strip() == 'main', 'Release must run from main')
    run('git', '-C', ROOT, 'fetch', 'origin', 'main', '--tags')
    require(run('git', '-C', ROOT, 'rev-parse', 'HEAD') == run('git', '-C', ROOT, 'rev-parse', 'origin/main'), 'Release must use current origin/main')
    tag = 'v' + version
    refs = run('git', '-C', ROOT, 'tag', '--list', tag).strip()
    require(not refs, 'Version tag already exists; choose a new version')
    releases = json.loads(run('gh', 'api', 'repos/Brendan-Lim/ContextLens/releases', '--paginate', '--slurp'))
    require(not any(r['tag_name'] == tag for page in releases for r in page), 'Release already exists')
    print('Release source preflight passed: ' + tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('metadata').add_argument('--version')
    commands.add_parser('plist').add_argument('path')
    check = commands.add_parser('verify'); check.add_argument('app'); check.add_argument('--mode', choices=['development', 'distribution'], default='development'); check.add_argument('--notarized', action='store_true')
    pack = commands.add_parser('package'); pack.add_argument('app'); pack.add_argument('output'); pack.add_argument('--development', action='store_true')
    source = commands.add_parser('preflight'); source.add_argument('version')
    commands.add_parser('verify-archive').add_argument('path')
    notary = commands.add_parser('notarize'); notary.add_argument('app'); notary.add_argument('output'); notary.add_argument('--profile', required=True); notary.add_argument('--keychain')
    args = parser.parse_args()
    if args.command == 'metadata': print(json.dumps(metadata(args.version)))
    elif args.command == 'plist': write_plist(args.path)
    elif args.command == 'verify': verify(args.app, args.mode, args.notarized); print('Bundle verification passed (' + args.mode + ')')
    elif args.command == 'package': package(args.app, args.output, args.development)
    elif args.command == 'preflight': preflight(args.version)
    elif args.command == 'verify-archive': print(json.dumps(verify_archive(args.path)))
    elif args.command == 'notarize':
        verify(args.app, 'distribution')
        with tempfile.TemporaryDirectory(prefix='contextlens-notary-') as temporary:
            submission = Path(temporary) / 'submission.zip'
            run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', args.app, submission)
            auth = ['--keychain-profile', args.profile]
            if args.keychain: auth += ['--keychain', args.keychain]
            submitted = subprocess.run(['xcrun', 'notarytool', 'submit', str(submission), *auth, '--wait', '--timeout', '30m', '--output-format', 'json'], capture_output=True, text=True)
            try:
                result = json.loads(submitted.stdout)
            except ValueError:
                raise ValueError('Notarytool did not return a submission result; inspect notarytool history with the configured profile')
            print(json.dumps({'notarizationID': result.get('id'), 'status': result.get('status')}))
            require(submitted.returncode == 0 and result.get('status') == 'Accepted', 'Notarization not accepted; inspect this submission ID with notarytool log')
        run('xcrun', 'stapler', 'staple', args.app)
        verify(args.app, 'distribution', notarized=True)
        package(args.app, args.output)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as error:
        # Do not dump subprocess output that might contain authentication material.
        raise SystemExit(f'Release gate failed: {error}')
