# Public beta readiness — 8 November 2026

> Follow-up: [0.3.1 native capture reliability](native-capture-reliability.md) records subsequent production lifecycle fixes and the revised diagnostic protocol. The sections below retain the earlier public-repository audit and its exact source/test scope. First-run and real WindowServer acceptance remain pending.

**READY FOR CONTROLLED TESTERS.** Automated installation/export checks pass and this audit found no confirmed confidential exposure within the inspected scope. Interactive first launch, fresh Screen Recording consent and native capture reliability remain incomplete. Green CI is not proof of those workflows.

## A. Public repository audit

Audit baseline: ContextLens `68bdf99af69bc52ea75911c90336e59c9c6f3f75`; Homebrew tap `9bec1ee5ce085d1dd5411855e2fd0dd25356fa6f`. All public branch/tag/PR refs were fetched before inspection. No file was deleted or published history changed during the audit.

| Scope | Reviewed input |
|---|---|
| ContextLens current tree | 487 tracked paths, 425 distinct blobs |
| ContextLens complete reachable history | 7 commits, 464 unique file blobs, 39 history-only blobs; 526 distinct path/blob versions, including the preview tag |
| Tap current tree | 7 tracked paths/blobs |
| Tap complete reachable history | 13 commits, 26 unique file blobs, 19 history-only blobs; main and preview-candidate branch included |
| Git metadata | Commit and annotated-tag messages checked separately; no credential finding |
| Published preview | Three release assets; ZIP contains seven expected files and exactly two executables |
| Published PNGs | All 112 paths: 93 browser-evidence images, 18 geometric documentation/example images, one owned brand image; 64 distinct PNG byte hashes |

Both repositories passed **Gitleaks 8.30.1** over all reachable history. A separate byte/filename review inspected all 490 unique file blobs across both repositories. Its 19 content-review candidates were documentation/reusable-analysis references to excluded private evidence plus two deliberately synthetic quoting-test paths; none was an actual receipt, transcript, account snapshot or credential. Sensitive/generated filename checks found no accidentally committed private files. There were no historical-only PNG versions outside the images reviewed.

The verified candidate contains 501 main-repository tracked paths and 15 tap paths after adding the guards, tests and documentation. Before commit, its index scans had zero findings, and an independent Gitleaks directory scan of an exact exported index snapshot also returned zero. The candidate link audit covered 83 Markdown files / 103 local links with zero broken destinations/anchors; all 51 external targets returned HTTP 200 during this audit. Future external availability is not asserted.

All 112 PNGs were inspected through 13 contact sheets, full-resolution local Vision OCR and ImageIO properties. Their pixels depict owned Lensboard fixture pages, geometric demo shapes or ContextLens branding. No personal application windows, browser profile chrome, visible account addresses/credentials or personal recordings were found. The 71 EXIF-bearing files contain only pixel dimensions/color-space fields; there are no author, GPS, identifying timestamp, XMP or text chunks. OCR/visual inspection is evidence, not a proof against every hidden or obfuscated payload.

Asset classification: the 173 `Benchmarks/reports/browser-evidence/` paths support deterministic replay and reproduction of raw/selected/annotated/auto-only comparisons. The 34 tracked `docs/examples/` paths are generated geometry/legacy-schema/export fixtures or owned example source. Branding is owned source. Retain these useful inputs, including duplicates needed for the comparisons; no size-only cleanup is warranted. The new documentation GIF reuses already-audited fixture 04, contains three inspected labeled frames, and is explicitly an illustration rather than native app execution.

The fresh preview download still hashes to **`1cd84d6b15fc7aed7346ff1fd27382d5d2cd5a51637c7358861ddf55ebe0da45`**. Its receipt/embedded provenance agree on clean source commit `4b463d3e6dfc3ec4035f89d0e9f8787dee08ff4c`. Expected files are Info.plist, app, CLI, icon, MIT license, preview provenance and CodeResources. There is no source checkout, private benchmark data, credential, extra executable, debug artifact or developer home/cache path. Both executables have ad-hoc signatures, no Apple team/authority and no entitlement exceptions. This verifies integrity and packaging, not Apple trust.

Ignored native screenshots, historical research reports, trial workspaces, raw traces and account/authorization records remain local. Their excluded paths are absent from every audited reachable tree; private originals were not removed or added to Git. The audit cannot establish what may exist in deleted server refs, forks, old clones, external logs or previously deleted releases. Both repositories expose a non-noreply Git author email as ordinary commit metadata; its value is intentionally omitted here. The owner should confirm that identity is intended to be public, or choose GitHub noreply for future commits. No identity/history change was made automatically.

The current layout is appropriate for a beta: source, CLI, tests, schemas, workflows, docs, Homebrew support and reproducible experiment code remain in place. No cosmetic reorganization or blind research-file deletion was performed. Existing local Markdown destinations were already valid (79 Markdown files / 79 local links at baseline); local-only report mentions and stale schedule/screenshot wording were clarified, with a public research summary rather than publishing excluded evidence. All 47 baseline external link targets returned HTTP 200 when parsed as full URLs; a truncated Apple URL revealed and pinned a balanced-parentheses bug in the new link checker.

## B. Security status

GitHub's authorized repository API reported, for **both** repositories: secret scanning **enabled**, push protection **enabled**, zero returned alerts. Non-provider patterns and validity checks are disabled. These are point-in-time settings/results, not a complete generic-secret or absence guarantee. No provider credential validation, paid scanning service or automatic remote security-setting change was performed.

Publication safeguards now inspect full index blobs, sensitive/generated filenames, common credentials/headers/URLs, personal filesystem paths, unsafe links, disguised build/archive files, public example metadata and every historical path. Approved fixture/media hashes and narrowly scoped synthetic path examples are explicit in `config/publication-policy.json`; they never exempt credential checks. Independent Gitleaks runs with pinned official download checksums, stock rules and forced redaction. Reports expose only safe locations/rules. A read-only **Publication Security** workflow checks current/history content and links without uploading source or raw scanner reports; normal CI also runs the current-tree guard. The included staged-file hook was enabled in the working ContextLens repository only after confirming there was no existing hook/configuration to replace; no global Git setting changed. Other clones can opt into it.

The first regression run failed before implementing the index/history guard. Coverage now includes staged content hidden by a different/deleted worktree, secrets removed from HEAD but retained by a tag, the same blob under risky historical filenames, metadata, symlinks, exact fixture approvals, compiled artifacts and safe reporting. Gitleaks download tampering and missing reports fail closed. [Commands, approval maintenance and incident handling](publication-security.md).

No confirmed credential exposure was found, so no revocation or history-remediation operation was performed. A future genuine exposure stops publication, requires rotation/revocation, and needs a separately approved plan before any force-push, history rewrite or release deletion. Manual pixel review remains mandatory for new media; the public Git author identity needs the owner's privacy decision. Repository scanners do not establish safety of unexamined future captures or unreachable copies.

## C. Installation readiness

| Check | Result and scope |
|---|---|
| Existing Homebrew preview | [Published cask](https://github.com/Brendan-Lim/homebrew-tap/blob/main/Casks/contextlens-preview.rb); [fresh install/audit run 42480574763](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42480574763) passed on disposable arm64 macOS 15.8.2 / Homebrew 7.0.12 after these changes |
| App placement, CLI link/help, quarantine, existing-app refusal, uninstall/session retention | Passed in that hosted environment; no local installation or permission reset repeated for this audit |
| Gatekeeper | Hosted read-only assessment returned 3, rejected; no Developer ID, notarization or acceptance claim |
| Actual Open Anyway | **Pending** — no disposable interactive macOS environment/person available |
| Fresh Screen Recording deny/grant/relaunch/revoke/recovery | **Pending** — owner's TCC permissions were not changed |
| Capture, annotation, UI Hand Off and reopen | **Pending** as an installed-preview interactive workflow |
| Released CLI offline smoke | Fresh downloaded CLI `--help`, `demo`, `validate`, `export --all-frames --keep-duplicates` passed on arm64 macOS 26.6.2; exported three-frame/one-issue package passed the Python validator; source session still validated afterward |
| Native CLI package inspection | Not implemented: `validate` accepts sessions. Exported Hand Off packages use `scripts/validate_package.py`; documentation now states this distinction |
| macOS 14, mixed-display scaling and upgrade | Deployment metadata verified; actual runtime/display/upgrade checks remain pending |

[Exact isolated acceptance steps](beta-acceptance.md) cover installation, real security dialogs, permission recovery, synthetic TextEdit windows, closure/app exit, resize/display scaling, rapid start/stop, empty capture, Review/Mark Up/Hand Off, relaunch, saved-session and export validation, and uninstall preservation. A new account or custom app directory alone does not isolate an existing global Homebrew app/CLI installation. Use a disposable VM or separate test Mac; every interactive case is marked pending until observed.

## D. Bugs found and fixed

- **Staged-file blind spot:** the old guard skipped a file missing from the working copy and did not inspect history. A temporary Git regression staged a credential, then hid/deleted its worktree version; the new guard checks the index blob and retains historical/tag findings after HEAD cleanup. No credential value is printed.
- **Publication coverage gaps:** risky filenames, generic headers/assignments, real home paths, unsafe links, generated binaries, unapproved media and private example metadata now fail with safe locations. Exact reviewed fixture hashes prevent a changed screenshot inheriting a broad directory exemption; legitimate reviewed historical digests can be retained explicitly.
- **Link-check parser defect:** a Markdown Apple API URL contains balanced parentheses. The initial checker truncated it and returned a misleading HTTP 404; the full URL is HTTP 200. The parser and regression now preserve it.
- **Documentation accuracy:** local-only trace/report/schedule references now lead to public summaries or explicit fresh-dataset requirements. Native engineering notes no longer present a failed closure probe or private screenshot as current public first-run proof. Source mapping stays experimental; no token/time/human-preparation benefit is advertised as proven.
- **Known native closure check remains unresolved:** retained evidence has `closure_detected_without_fallback: false`. Source confirms selected-window ID/PID checks and no display fallback, but does not explain that live failure. The helper also calls `makeKeyAndOrderFront` for its probe; the agent guide now warns it can take focus despite background flags. It was not run on the owner's active desktop. No speculative production capture fix or unverified passing result was introduced.

| Verification before final push | Result |
|---|---|
| Baseline and full deterministic `scripts/ci.sh` in an isolated staged-candidate checkout | Passed: 80 Swift tests, 49 benchmark Python tests, 36 publication/release/link regression tests, 13 packages, 10 deterministic replays, real-bundle portability rejection, development archive round-trip and browser fixtures (10 defects reproduced, 10 controls passed) |
| Independent JSON Schema cross-check | Passed for all 13 packages using the existing development dependency; the isolated clone initially lacked that optional dependency, while baseline/supplemental workspace validation included it |
| Offline experiment verification | Passed: 4 Visual-to-Code Python gate tests, 8 code-aware Python tests, 14 Visual-to-Code Node unit/export tests, 3 owned-browser tests and 2 code-aware mapper tests; no live model invocation |
| Tap | 19 guard/link/Gitleaks regression tests, Ruby/template/cask validation, staged/current/history audits and independent Gitleaks passed locally |
| Public guard outputs and media | Zero findings; 216 explicit reviewed fixture/branding/telemetry/media approvals; all three new GIF frames inspected, metadata limited to GIF/file-size properties |
| npm development dependency audit | Zero reported vulnerabilities during isolated CI; production dependencies remain zero |

Hosted verification of implementation [`f9c6b06`](https://github.com/Brendan-Lim/ContextLens/commit/f9c6b068634246507094032d9c163aca15ecde38) and tap [`195acc4`](https://github.com/Brendan-Lim/homebrew-tap/commit/195acc4686aefbf959af6bc37d06447080d584ad) passed:

- [Main full macOS CI 42480571742](https://github.com/Brendan-Lim/ContextLens/actions/runs/42480571742), including independent schema validation.
- [Main Publication Security 42480571658](https://github.com/Brendan-Lim/ContextLens/actions/runs/42480571658): full reachable history, current index, links, regression tests and independent Linux Gitleaks.
- [Tap validation/install/audit 42480574763](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42480574763): actual install/link/help/quarantine, expected Gatekeeper rejection and uninstall preservation passed again. Its expected foreign-app refusal appears as an error annotation inside a passing protection test.
- [Tap Publication Security 42480574761](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42480574761): full history, current index, links, tests and Linux Gitleaks.

The implementation commit's post-change historical audit inspected 549 main path/blob versions / 487 unique file blobs with zero findings. This report-only follow-up preserves those application, fixture and guard implementations. No paid model trial, new native capture or personal-window capture ran. The working app, CLI installation, TCC settings and private experiments were not replaced/reset.

## E. Release status

Existing [v0.3.0-preview.1](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1) remains published, a prerelease, and unchanged. Homebrew command:

```sh
brew install --cask Brendan-Lim/tap/contextlens-preview
```

No new binary is warranted: this work changes publication tooling, tests and documentation, with a synthetic illustration; native application/CLI code and release identities are unchanged. **No preview.2 was published or existing archive replaced.** Prepare `v0.3.0-preview.2` only when a reproduced runtime fix warrants rebuilding and all applicable gates pass. Signed/notarized stable distribution remains separate and still requires its original production credentials/gates.

## F. Final recommendation

**READY FOR CONTROLLED TESTERS** using non-sensitive, disposable windows and the isolated checklist. Do not broaden the recommendation to limited public beta until real authorization, fresh permissions, capture/Hand Off/session recovery and target-loss behavior have evidence. Remaining blockers are interactive test access and the unresolved native closure check, with macOS 14/display/upgrade coverage also pending. Automated installation and a clean reachable-history scan do not remove those limitations.
