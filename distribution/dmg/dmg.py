"""Headless Finder layout and read-only DMG creation. Never drives the working desktop."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from release import require, run, verify

ASSETS = Path(__file__).with_name('assets')
POSITIONS = {'ContextLens.app': (214, 254), 'Applications': (506, 254)}
BOUNDS = '{{160, 120}, {720, 440}}'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inventory(app):
    """Normalized bundle files, content, executable bits and signed resource forks."""
    app = Path(app)
    result = {}
    for path in sorted(app.rglob('*')):
        require(not path.is_symlink(), 'Unexpected symlink in native application bundle')
        if path.is_file():
            attrs = {}
            names = os.listxattr(path) if hasattr(os, 'listxattr') else run('xattr', path).splitlines()
            for name in ['com.apple.ResourceFork', 'com.apple.FinderInfo']:
                if name in names:
                    value = os.getxattr(path, name) if hasattr(os, 'getxattr') else bytes.fromhex(run('xattr', '-px', name, path))
                    attrs[name] = hashlib.sha256(value).hexdigest()
            result[path.relative_to(app).as_posix()] = dict(sha256=sha256(path), executable=bool(path.stat().st_mode & 0o111), attributes=attrs)
    require(result, 'Empty app inventory')
    return result


@contextmanager
def mounted(image, readonly=True):
    # Unique private mount point; never discover/detach another ContextLens volume by name.
    with tempfile.TemporaryDirectory(prefix='contextlens-mount-', dir='/private/tmp' if sys.platform == 'darwin' else '/tmp') as temporary:
        mount = Path(temporary).resolve() / 'volume'
        mount.mkdir()
        try:
            run('hdiutil', 'attach', '-plist', '-nobrowse', '-noautoopen', '-owners', 'off',
                '-readonly' if readonly else '-readwrite', '-mountpoint', mount, image)
            require(os.path.ismount(mount), 'Disk image did not mount at its private mountpoint')
            yield mount
        finally:
            if os.path.ismount(mount):
                try:
                    run('hdiutil', 'detach', mount)
                except subprocess.CalledProcessError:
                    # This path belongs only to the image attached in this context.
                    run('hdiutil', 'detach', '-force', mount)
                    raise  # Cleanup succeeded, but clean unmount verification failed.


def configure(mount):
    from ds_store import DSStore
    from mac_alias import Alias
    alias = Alias.for_file(str((mount / '.background/background.tiff').resolve())).to_bytes()
    with DSStore.open(str(mount / '.DS_Store'), 'w+') as store:
        store['.']['vSrn'] = ('long', 1)
        store['.']['icvl'] = ('type', b'icnv')
        store['.']['bwsp'] = dict(ShowToolbar=False, ShowStatusBar=False, ShowSidebar=False,
                                 ShowPathbar=False, ShowTabView=False, WindowBounds=BOUNDS,
                                 ContainerShowSidebar=False, PreviewPaneVisibility=False)
        # Finder requires the fallback RGB fields even when backgroundType selects a picture.
        store['.']['icvp'] = dict(viewOptionsVersion=1, backgroundType=2, backgroundImageAlias=alias,
                                 backgroundColorRed=1.0, backgroundColorGreen=1.0, backgroundColorBlue=1.0,
                                 iconSize=104.0, textSize=13.0, labelOnBottom=True,
                                 showItemInfo=False, showIconPreview=False, gridSpacing=100.0,
                                 gridOffsetX=0.0, gridOffsetY=0.0, scrollPositionX=0.0,
                                 scrollPositionY=0.0, arrangeBy='none')
        for name, position in POSITIONS.items():
            store[name]['Iloc'] = position


def verify_layout(mount):
    from ds_store import DSStore
    from mac_alias import Alias
    with DSStore.open(str(mount / '.DS_Store'), 'r') as store:
        require(store['.']['icvl'] == (b'type', b'icnv'), 'Finder must use icon view')
        window = store['.']['bwsp']
        require(window['WindowBounds'] == BOUNDS and all(window[k] is False for k in
                ['ShowToolbar', 'ShowStatusBar', 'ShowSidebar', 'ShowPathbar']), 'Finder window layout differs')
        options = store['.']['icvp']
        require(options['iconSize'] == 104 and options['backgroundType'] == 2
                and options['labelOnBottom'] and options['arrangeBy'] == 'none', 'Finder icon layout differs')
        require(all(type(options.get(channel)) is float and options[channel] == 1.0 for channel in
                    ['backgroundColorRed', 'backgroundColorGreen', 'backgroundColorBlue']),
                'Finder picture settings require fallback RGB color components')
        alias = Alias.from_bytes(options['backgroundImageAlias'])
        require(alias.target.posix_path == '/.background/background.tiff'
                and alias.volume.name == 'ContextLens', 'Background alias points outside this volume')
        for name, position in POSITIONS.items():
            require(tuple(store[name]['Iloc']) == position, 'Finder icon position differs')


def verify_dmg(image, app=None, install_copy=False):
    image = Path(image).resolve()
    run('hdiutil', 'verify', image)  # Validates the UDIF checksum, separately from SHA-256.
    with mounted(image) as mount:
        run('diskutil', 'verifyVolume', mount)
        shortcut = mount / 'Applications'
        require(shortcut.is_symlink() and os.readlink(shortcut) == '/Applications'
                and shortcut.resolve() == Path('/Applications'), 'Applications must be the real destination')
        bundle = mount / 'ContextLens.app'
        data = verify(bundle, 'development')
        require((mount / '.background/background.tiff').stat().st_size > 0, 'Missing Retina background')
        verify_layout(mount)
        contents = inventory(bundle)
        if app is not None:
            require(contents == inventory(app), 'DMG changed bundle files, executable modes or resource metadata')
        if install_copy:
            # Exercises normal copy semantics in a throwaway folder. Never /Applications.
            with tempfile.TemporaryDirectory(prefix='contextlens-copy-') as destination:
                copy = Path(destination) / 'ContextLens.app'
                run('ditto', bundle, copy)
                verify(copy, 'development')
                require(inventory(copy) == contents, 'Installation copy changed bundle')
    return dict(version=data['version'], build=data['build'], architecture='arm64', minimumMacOS=data['minimumMacOS'],
                sha256=sha256(image), bundleInventorySHA256=hashlib.sha256(
                    __import__('json').dumps(contents, sort_keys=True).encode()).hexdigest(),
                mount='pass', filesystem='pass', signature='pass', layoutMetadata='pass',
                copyRoundTrip='pass' if install_copy else 'not-run', finderAppearance='pending-isolated-GUI',
                applicationFirstLaunch='pending-isolated-GUI')


def build(app, target):
    app, target = Path(app).resolve(), Path(target).resolve()
    require(target.suffix == '.dmg' and not target.exists(), 'Choose a new .dmg; replacement is forbidden')
    verify(app, 'development')
    original = inventory(app)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.contextlens-dmg-', dir=target.parent) as temporary:
        work = Path(temporary)
        stage = work / 'root'; stage.mkdir()
        run('ditto', app, stage / 'ContextLens.app')
        os.symlink('/Applications', stage / 'Applications')
        (stage / '.background').mkdir()
        run('sips', '-s', 'format', 'tiff', '-s', 'dpiWidth', '72', '-s', 'dpiHeight', '72',
            ASSETS / 'background@1x.png', '--out', work / '1x.tiff')
        run('sips', '-s', 'format', 'tiff', '-s', 'dpiWidth', '144', '-s', 'dpiHeight', '144',
            ASSETS / 'background.png', '--out', work / '2x.tiff')
        run('tiffutil', '-cathidpicheck', work / '1x.tiff', work / '2x.tiff',
            '-out', stage / '.background/background.tiff')
        (stage / '.metadata_never_index').touch()
        rw = work / 'staging.dmg'
        run('hdiutil', 'create', '-srcfolder', stage, '-volname', 'ContextLens', '-fs', 'HFS+', '-format', 'UDRW', rw)
        with mounted(rw, readonly=False) as mount:
            configure(mount)
            verify_layout(mount)
        compressed = work / 'final.dmg'
        run('hdiutil', 'convert', rw, '-format', 'UDZO', '-imagekey', 'zlib-level=9', '-o', compressed)
        result = verify_dmg(compressed, app, install_copy=True)
        require(inventory(app) == original, 'Packaging modified the source bundle')
        os.link(compressed, target)  # Exclusive final-byte promotion; races cannot overwrite.
    return result
