#!/usr/bin/env python3
"""Offline, evidence-linked activity profiling; never attribute turn tokens to shell calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import statistics as stats
import telemetry

ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'Experiments/visual-to-code/reports/trace-profile'
SOURCE_SUFFIXES={'.js','.mjs','.css','.html','.tsx','.jsx','.ts','.vue','.svelte'}


def shell_body(command):
    try:
        words=shlex.split(command)
        if len(words)>=3 and words[1] in {'-lc','-c'}:return words[2]
    except ValueError:pass
    return command


def project_path(value):
    value=value.strip('"\'(),;')
    if value.startswith('HEAD:'):value=value[5:]
    if value.startswith('./'):value=value[2:]
    p=PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or any(c in value for c in '*?$\\\n') or not p.suffix:
        return None
    return str(p)


def classify(command):
    body=shell_body(command);reads=[]
    # A conservative recognizer, not a complete shell interpreter. Heredoc code is
    # retained as evidence but not interpreted as additional shell statements.
    prefix=body.split('<<',1)[0]
    for fragment in re.split(r'[;\n]|&&|\|\|',prefix):
        try:words=shlex.split(re.split(r'[<>]',fragment,1)[0])
        except ValueError:continue
        if not words:continue
        if words[0] in {'cat','head','tail','sed','less'}:
            for value in words[1:]:
                path=project_path(value)
                if path:reads.append(path)
    reads += [p for p in (project_path(x) for x in re.findall(r"Path\(['\"]([^'\"]+)['\"]\)\.read_(?:text|bytes)\(",body)) if p]
    reads += [p for p in (project_path(x) for x in re.findall(r'git\s+show\s+(HEAD:[\w./-]+)',body)) if p]
    tags=[]
    source=[p for p in reads if PurePosixPath(p).suffix in SOURCE_SUFFIXES and not p.startswith('evidence/')]
    if any(p.startswith('evidence/') for p in reads):tags.append('initial_context_inspection')
    if any(p.lower().endswith(('.png','.jpg','.webp')) for p in reads):tags.append('image_inspection')
    searches=bool(re.search(r'(?:^|[;\n&| ])(?:rg|grep|find|ls)\s',prefix))
    if searches:tags.append('source_code_discovery')
    if source:tags.append('source_code_reading')
    testing=bool(re.search(r'node\s+(?:--check|[^;\n]*test)|npm\s+test|pytest|unittest|git diff --check|\bassert\b',body))
    if testing:tags.append('testing_and_verification')
    return {'body':body,'recognized_reads':reads,'recognized_source_reads':source,
            'source_search_or_listing':searches,'test_or_assertion_command':testing,
            'categories':tags or ['unclassified_activity']}


def profile(file,study):
    result=json.loads(file.read_text());trace=file.parent/'trace.jsonl'
    raw=trace.read_text();events=[json.loads(line) for line in raw.splitlines() if line.strip()]
    usage=telemetry.codex(raw);commands=[];modified=set();other_tools=[];seen=Counter()
    for index,e in enumerate(events):
        if e.get('type')!='item.completed':continue
        item=e.get('item',{});kind=item.get('type')
        if kind=='command_execution':
            c=classify(item['command']);c.update(event_index=index,item_id=item.get('id'),
                exit_code=item.get('exit_code'),output_characters=len(item.get('aggregated_output','')),
                output_utf8_bytes=len(item.get('aggregated_output','').encode()),
                command_duration_seconds=item.get('duration_seconds'),token_attribution=None)
            repeated=[p for p in c['recognized_source_reads'] if seen[p]]
            if repeated:c['categories'].append('repeated_exploration')
            c['repeated_source_reads']=repeated;seen.update(c['recognized_source_reads']);commands.append(c)
        elif kind=='file_change':
            for change in item.get('changes',[]):modified.add(Path(change['path']).name)
            other_tools.append({'event_index':index,'item_type':kind,'category':'code_modification'})
        elif kind not in {'agent_message','reasoning','error',None}:
            other_tools.append({'event_index':index,'item_type':kind,
                'category':'image_inspection' if 'image' in kind else 'unclassified_activity'})
    attachments=([result['attached_image']] if result.get('attached_image') else
                 list((result.get('attached_images') or {}).keys()))
    categories=Counter(tag for c in commands for tag in c['categories'])
    categories.update(t['category'] for t in other_tools)
    read_counts=Counter(p for c in commands for p in c['recognized_reads'])
    return {'study':study,'task':result['task'],'condition':result['condition'],'repeat':result['trial'],
        'phase':result.get('phase'),'success':result.get('success'),'timed_out':result.get('timed_out',False),
        'trace':str(trace.relative_to(ROOT)),'trace_sha256':hashlib.sha256(raw.encode()).hexdigest(),
        'result':str(file.relative_to(ROOT)),'usage':usage,
        'per_completed_turn_usage':[{'event_index':i,'usage':e.get('usage',{})} for i,e in enumerate(events) if e.get('type')=='turn.completed'],
        'completed_shell_calls':len(commands),'failed_shell_calls':sum(c['exit_code'] not in (None,0) for c in commands),
        'completed_tool_items':len(commands)+len(other_tools),'files_read_recognized':dict(read_counts),
        'source_files_read_recognized':dict(seen),'repeated_source_read_occurrences':sum(max(0,n-1) for n in seen.values()),
        'source_files_read_but_not_modified':sorted(set(seen)-modified),
        'source_search_or_listing_calls':sum(c['source_search_or_listing'] for c in commands),
        'context_report_read_occurrences':sum(n for p,n in read_counts.items() if p in {'evidence/context.md','evidence/task.md'}),
        'manifest_read_occurrences':sum(n for p,n in read_counts.items() if p=='evidence/manifest.json'),
        'image_tool_events':sum(t['category']=='image_inspection' for t in other_tools),
        'initial_attached_images':attachments,'initial_image_count':len(attachments),
        'test_or_assertion_shell_calls':sum(c['test_or_assertion_command'] for c in commands),
        'source_files_modified':sorted(modified),'source_files_modified_count':len(modified),
        'output_characters':sum(c['output_characters'] for c in commands),
        'measured_command_time_seconds':None,'categories_overlapping':dict(categories),
        'commands':commands,'other_tool_items':other_tools}


def dist(values):
    values=[v for v in values if v is not None]
    return {'n':len(values),'mean':stats.mean(values) if values else None,'median':stats.median(values) if values else None,
            'sd':stats.stdev(values) if len(values)>1 else None}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=DEFAULT);a=p.parse_args()
    if a.output.exists():raise SystemExit('Choose a new output directory; existing profile is preserved.')
    a.output.mkdir(parents=True)
    sources={'manual-equivalent-study':ROOT/'Benchmarks/reports/manual-vs-contextlens/study-v2/trials',
             'archived-vs-lean-study':ROOT/'Benchmarks/reports/lean-handoff/comparison'}
    rows=[profile(f,study) for study,folder in sources.items() for f in sorted(folder.glob('*/result.json'))]
    metrics=['completed_shell_calls','failed_shell_calls','repeated_source_read_occurrences','source_search_or_listing_calls',
             'context_report_read_occurrences','manifest_read_occurrences','test_or_assertion_shell_calls','output_characters','source_files_modified_count']
    groups=[]
    for study,condition in sorted({(r['study'],r['condition']) for r in rows}):
        selected=[r for r in rows if (r['study'],r['condition'])==(study,condition)]
        groups.append({'study':study,'condition':condition,'attempts':len(selected),
            'observed_usage_trials':sum(r['usage']['total_tokens'] is not None for r in selected),
            'usage':{k:dist(r['usage'][k] for r in selected) for k in ['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','total_tokens','turns']},
            'activity':{k:dist(r[k] for r in selected) for k in metrics}})
    report={'kind':'offline-existing-real-trace-activity-profile','model_calls':0,'individual_trials':rows,'groups':groups,
        'limits':['Category counts overlap; shell fragments may batch several actions.',
          'File reads are conservative recognized arguments, not a complete syscall/file-access trace.',
          'Reading a file not modified does not establish irrelevance or redundant reasoning.',
          'Repeated reads may legitimately compare edits; they are not necessarily waste.',
          'Images attached in argv count as supplied evidence, not image tool events; viewing cannot be inferred from zero events.',
          'No command durations/timestamps are exposed in these traces. Invocation timing cannot be apportioned to commands.',
          'Turn usage cannot be attributed to individual commands, images, source files or categories.',
          'The manual timeout lacks completed-turn usage; missing is not zero. Separate experiments are never pooled causally.']}
    (a.output/'profile.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Existing-trace exploration profile','',f'{len(rows)} real historical attempt records; zero new model calls.','',
           '| Study | Condition | Attempts | Shell calls mean | Discovery calls | Repeated source reads | Report reads | Manifest reads | Output chars |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for g in groups:
        act=g['activity'];lines.append('| '+' | '.join([g['study'],g['condition'],str(g['attempts']),*[f"{act[k]['mean']:.2f}" for k in ['completed_shell_calls','source_search_or_listing_calls','repeated_source_read_occurrences','context_report_read_occurrences','manifest_read_occurrences','output_characters']]])+' |')
    lines+=['','## Per task','', '| Study | Task | Arm | Rep | Discovery | Reads (recognized) | Repeats | Tests | Trace |','|---|---|---|---:|---:|---|---:|---:|---|']
    for r in rows:lines.append('| '+' | '.join([r['study'],r['task'],r['condition'],str(r['repeat']),str(r['source_search_or_listing_calls']),', '.join(r['source_files_read_recognized']),str(r['repeated_source_read_occurrences']),str(r['test_or_assertion_shell_calls']),f"[{Path(r['trace']).parent.name}](../{r['trace']})"])+ ' |')
    current={g['condition']:g for g in groups if g['study']=='manual-equivalent-study'}
    old={g['condition']:g for g in groups if g['study']=='archived-vs-lean-study'}
    lines+=['','## Measured comparisons','',
      f"In the manual-equivalent study, current ContextLens averaged {current['contextlens']['activity']['completed_shell_calls']['mean']:.2f} completed shell calls versus {current['manual-equivalent']['activity']['completed_shell_calls']['mean']:.2f}, including the zero-command timeout. Discovery/listing calls were {current['contextlens']['activity']['source_search_or_listing_calls']['mean']:.2f} versus {current['manual-equivalent']['activity']['source_search_or_listing_calls']['mean']:.2f}: these traces do not show extra source searching in the ContextLens arm. Repeated recognized source-read occurrences were {current['contextlens']['activity']['repeated_source_read_occurrences']['mean']:.2f} versus {current['manual-equivalent']['activity']['repeated_source_read_occurrences']['mean']:.2f}.",
      f"In the separate archived-versus-lean study, mandatory manifest reads fell from {old['baseline']['activity']['manifest_read_occurrences']['mean']:.2f} to {old['lean']['activity']['manifest_read_occurrences']['mean']:.2f} per attempt while completed shell calls fell from {old['baseline']['activity']['completed_shell_calls']['mean']:.2f} to {old['lean']['activity']['completed_shell_calls']['mean']:.2f}. Discovery calls remained similar ({old['baseline']['activity']['source_search_or_listing_calls']['mean']:.2f} versus {old['lean']['activity']['source_search_or_listing_calls']['mean']:.2f}). This is descriptive evidence about activity, not a causal token allocation.",
      'All completed usage-bearing attempts expose one completed CLI turn. Extra cached input therefore does not correspond to extra observed user/CLI conversation turns; within-turn model requests and cache attribution are unavailable. The previous complete-pair token comparison remains the authority for token differences, including its missing-usage caveat.',
      '','## Interpretation','',
      'Source discovery and repeated source reads are observable optimisation targets. This does not establish that supplying pointers would remove those calls or their token cost. Tiny fixtures have only three source files; reading all three can be reasonable.',
      'A mapper could name a verified stylesheet/rule or instrumented component before repository searches. It would not eliminate the initial agent/system context, output reasoning, implementation work, semantic validation, or provider/cache variability.',
      'Current versus manual and archived versus lean remain separate studies. See the JSON for every command, event index, output length, source trace hash and turn-level usage. No per-command token attribution is made.','',
      '## Unobservable activity','',*['- '+x for x in report['limits']]]
    (ROOT/'docs/token-exploration-analysis.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'traces_profiled':len(rows),'output':str(a.output),'new_model_calls':0}))


if __name__=='__main__':main()
