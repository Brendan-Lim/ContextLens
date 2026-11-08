#!/usr/bin/env python3
"""Exercise portability regression and CLI behavior on a real disposable bundle."""
from pathlib import Path
import shutil
import tempfile
from release import ROOT, require, run, verify

app = ROOT / 'dist/ContextLens.app'
verify(app)
cli = app / 'Contents/MacOS/contextlens-cli'
require(run(cli, '-h') == run(cli, '--help'), 'CLI help aliases differ')
with tempfile.TemporaryDirectory(prefix='contextlens-release-regression-') as temporary:
    # Reintroduce the observed initial packaging defect: the unstripped linker's
    # absolute object paths. Only the disposable copy is re-signed for this test.
    broken = Path(temporary) / 'ContextLens.app'
    shutil.copytree(app, broken)
    binary_dir = Path(run(str(ROOT / 'scripts/swift.sh'), 'build', '-c', 'release', '--arch', 'arm64', '--show-bin-path').strip())
    unstripped = binary_dir / 'ContextLens'
    require(str(ROOT).encode() in unstripped.read_bytes(), 'Regression fixture requires an unstripped checkout build')
    shutil.copy2(unstripped, broken / 'Contents/MacOS/ContextLens')
    run('codesign', '--force', '--sign', '-', '--timestamp=none', broken)
    try:
        verify(broken)
    except ValueError as error:
        require('Developer-specific path' in str(error), 'Regression failed for the wrong reason')
    else:
        raise SystemExit('Regression: unstripped developer paths were accepted')
print('Real bundle portability regression and CLI help aliases passed.')
