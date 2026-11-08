# Local diagnostics and stress checks

The app uses macOS unified logging with subsystem `dev.contextlens.app` and categories `App`, `Images`, `Capture` and `Export`. Debug messages record editor duration, decode/render counts, committed frame sequence numbers and export attempt duration/count. Errors log a fixed failure message; details remain in the app's existing error UI. No window titles, paths, image data, annotations, tasks, Accessibility labels or raw error descriptions are written to these logs. No telemetry service or network upload is added. macOS controls log storage/retention.

```sh
log stream --level debug --predicate 'subsystem == "dev.contextlens.app"'
```

Keep this running only while diagnosing; debug timing messages can be numerous during capture. `Images` timings include work on the actor and are not keyboard/display latency. Export timing is explicitly an attempt and may describe a failed/cancelled operation. Frame logs identify a numeric sequence only.

Runtime guards throw recoverable errors for invalid geometry, non-finite stroke points, dimension mismatches, escaping paths, invalid sample scale/time and overflowing luminance dimensions/counters. Cache byte accounting and thumbnail-size bounds also have debug assertions. Public/file inputs use validation errors instead of debug-only assertions so release builds retain their checks. Disk failures propagate to the UI; capture selector state advances only after a successful write.

```sh
scripts/verify.sh
python3 scripts/check-coverage-map.py
# Generated 2x screenshot fixture; always choose a new destination:
dist/contextlens-cli stress-fixture /tmp/contextlens-stress 500
dist/contextlens-cli profile-images /tmp/contextlens-stress
```

The fixture contains generated UI bars and per-state marks, not real screenshots. The profiler compares the former load/render-per-note image path with the new render-request gate, then measures geometry rendering and thumbnail loading. It excludes JSON persistence, SwiftUI layout, event delivery and the display. Use `scripts/measure-performance.py` for three repetitions and process peak memory, including a 100-state export and comparator profile.

The explicitly invoked `--capture-soak OUTPUT.json --soak-seconds 600 [--low-sensitivity]` test creates and records only a window owned by this process. It skips activation and needs existing Screen Recording approval; it never requests consent automatically. `scripts/measure-capture-soak.py` runs both sensitivities sequentially and records CPU/RSS samples. Its changing bars and scripted hold periods exercise the production screenshot/selector/encoding path, but not physical scroll events, another application's UI, real video or the ordinary capture controller's full lifecycle.

See [coverage](testing-coverage.md) for tested and untested behavior, and results (local-only evidence `testing-report.md`) for measurements and remaining failures.
