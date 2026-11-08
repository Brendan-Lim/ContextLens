# Positioning ContextLens around the work it removes

The subsequent [24-attempt old/lean comparison](handoff-comparison-results.md) observed 11.9% faster mean time to its original acceptance and 5.5% fewer total tokens, alongside 10.1% more uncached input. Uncertainty includes no improvement, and broader email checks found one weak fix per format. Human reporting effort and quota savings remain unmeasured; these results do not support a general speed, quality or allowance claim.

## A claim we can support now

**Turn UI feedback into a clear coding-agent handoff.**

Capture the window you are working in, mark what should change, and export a visual brief. Keep your screenshots, notes and UI states together without assembling a screenshot report by hand. Files stay local until you choose to share them with an agent.

Lead with fewer reporting chores and clearer intent. The product already provides selected-window recording, state selection, editable boxes/highlights, explicit notes, stable issue IDs and a portable local package. Those are inspectable capabilities. “Saves hours,” “uses fewer ChatGPT credits,” “makes every agent faster,” and “improves fix quality” require measurements we do not yet have.

Suggested short copy:

> Show the problem. Mark the change. Hand it off.
>
> ContextLens gathers UI states and your visual notes into a local brief for your coding agent. Spend less attention managing screenshots and explaining which element you mean.

“Spend less attention” describes the reporting work the product is designed to remove. Treat reductions in effort or frustration as hypotheses until observed with people; do not attach a percentage or time saving to this copy yet.

## What to measure

The primary outcome is **time from noticing a UI problem to an accepted fix**, including manual capture/report preparation, app review/annotation/export, agent work, evaluation and correction rounds. Record active human preparation time separately from elapsed waiting. A modest increase in agent time can still accompany a better overall workflow if human effort decreases enough; the current data does not establish that decrease.

Use the same task scope, starting source, model/effort and acceptance criteria in each condition. Counterbalance the order for operators to limit learning effects. Include representative multi-state and hard-to-describe UI tasks, not only tiny fixtures whose desired change is already stated precisely in one sentence.

Keep these outcomes together:

| Outcome | Why it matters |
|---|---|
| Accepted-result elapsed time, including preparation/corrections | Overall workflow benefit |
| Active human preparation seconds, manual captures/crops and interruptions | Reporting effort and disruption |
| Clarification/correction rounds and abandoned handoffs | Whether the evidence communicates intent |
| Target acceptance, regression checks and independent visual review | Quality must not be traded for lower usage |
| Before/after perceived effort or frustration using a consistent rating | Direct evidence for the product's human value |
| Input, cached input, uncached input, output and tool calls | Diagnose where agent work grows |
| Displayed ChatGPT allowance observations | Secondary subscription-specific signal, with reset/concurrency/resolution caveats |

Do not replace the primary outcome with a more favorable metric after seeing results. Report unsuccessful attempts and timeouts. Predefine the quality gate and report individual task results beside averages.

## How to interpret allowance

OpenAI says model choice, reasoning, tools, retrieval and caching affect usage. Included limits are shared and are not a simple token-price conversion. The local account endpoint returns account-level used percentages and reset windows, rather than a precise per-trial allowance charge. A displayed zero change is not evidence that a trial was free. A reset or concurrent activity invalidates simple causal attribution.

Sources checked on 7 November 2026: [official pricing/usage guidance](https://learn.chatgpt.com/docs/pricing), [account rate-limit protocol](https://learn.chatgpt.com/docs/app-server).

Keep allowance as a secondary observation. Isolate other account activity where practical, record both windows and reset timestamps, and retain raw readings. Do not infer savings from rounded percentages or price total tokens as if all tokens were uncached API input. No money or paid credits are authorized for these experiments.

## What the earlier agent study actually showed

The 27 corrected scripted trials established outcomes for their eager-image protocol: full packages used more total tokens and took longer than four plain screenshots on average. They did not measure human report preparation, frustration, general workflow value, or progressive image viewing.

A trace audit found 11.2 shell calls on average for full packages versus 5.6 for plain screenshots. Mean uncached input was about 17,612 versus 15,945 tokens; output was about 1,342 versus 1,230. Much of the total-token gap was cached input accumulated across tool calls. This is a diagnostic observation, not a causal decomposition or an allowance estimate.

The benchmark also used package-relative instructions while the process started in the project root; some initial `cat context.md` / `cat manifest.json` calls failed before agents found `evidence/`. The next comparison corrects paths in **both** arms and keeps attached image bytes identical. The earlier result should not be represented as an intrinsic penalty of all ContextLens usage.

## The change being tested

The new copied prompt names the exact `context.md` path. That file contains the explicit requests and one annotated overview per marked state. The manifest is optional. Complete timeline/events move to `metadata/timeline.md`; crops, per-issue overlays, original-dimension redacted full frames and precise metadata remain available. No request is summarized away, no image is downsampled, and no required verification is removed.

This removes mandatory packaging reads and duplicate initial views. It does not prove faster reasoning or unchanged agent outcomes. The prepared comparison uses the same initial pixels in both arms and independent acceptance/regression checks. Live validation remains gated by included-usage availability and the existing zero-money policy.
