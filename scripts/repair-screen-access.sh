#!/bin/zsh
# Explicitly invoked repair: only ContextLens's Screen Recording grant is reset.
set -eu
cd "${0:A:h:h}"
app_path="$PWD/dist/ContextLens.app"
[[ -d "$app_path" ]] || { print -u2 'Build ContextLens first.'; exit 1; }
/usr/bin/codesign --verify --deep --strict "$app_path"
if /usr/bin/pgrep -x ContextLens >/dev/null; then
    /usr/bin/osascript -e 'tell application id "dev.contextlens.app" to quit'
    for attempt in {1..30}; do
        /usr/bin/pgrep -x ContextLens >/dev/null || break
        /bin/sleep 0.1
    done
    if /usr/bin/pgrep -x ContextLens >/dev/null; then
        print -u2 'ContextLens has not finished quitting. Finish any save dialog, then rerun this repair.'
        exit 1
    fi
fi
# Preserve the signed bytes but replace the bundle/executable inodes. Keep a backup.
stage_path=$(/usr/bin/mktemp -d "$PWD/dist/.permission-repair.XXXXXX")
/usr/bin/ditto "$app_path" "$stage_path/ContextLens.app"
/usr/bin/codesign --verify --deep --strict "$stage_path/ContextLens.app"
/bin/mv "$app_path" "$stage_path/previous.app"
/bin/mv "$stage_path/ContextLens.app" "$app_path"
/usr/bin/tccutil reset ScreenCapture dev.contextlens.app
/usr/bin/open "$app_path"
print 'Reset only ContextLens Screen Recording and reopened the verified build. Approve it in macOS when requested.'
