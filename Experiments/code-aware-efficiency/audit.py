"""Offline trace and source-localization audit. No command-level token attribution."""
import hashlib
import argparse
import json
from pathlib import Path
import re
import statistics as stats
from collections import Counter, deque

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mean(values):return stats.mean(values) if values else None

def main():
    profile=ROOT/'Experiments/visual-to-code/reports/trace-profile-v2/profile.json'
    old=json.loads(profile.read_text());groups=[]
    for study,condition in sorted({(r['study'],r['condition']) for r in old['individual_trials']}):
        rows=[r for r in old['individual_trials'] if (r['study'],r['condition'])==(study,condition)]
        groups.append(dict(study=study,condition=condition,attempts=len(rows),usageAvailable=sum(r['usage']['total_tokens'] is not None for r in rows),
          shellCommandsMean=mean([r['completed_shell_calls'] for r in rows]),discoveryCommandsMean=mean([r['source_search_or_listing_calls'] for r in rows]),
          uniqueSourceFilesReadMean=mean([len(r['source_files_read_recognized']) for r in rows]),sourceReadOccurrencesMean=mean([sum(r['source_files_read_recognized'].values()) for r in rows]),
          repeatedReadsMean=mean([r['repeated_source_read_occurrences'] for r in rows]),testCommandsMean=mean([r['test_or_assertion_shell_calls'] for r in rows]),
          outputUTF8BytesMean=mean([sum(c['output_utf8_bytes'] for c in r['commands']) for r in rows]),
          actualTurnUsageMeans={k:mean([r['usage'][k] for r in rows if r['usage'][k] is not None]) for k in ['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','total_tokens']}))
    trace_receipts=[]
    for r in old['individual_trials']:
        p=ROOT/r['trace'];assert sha(p)==r['trace_sha256']
        trace_receipts.append({k:r[k] for k in ['study','task','condition','repeat','phase','success','timed_out','trace','trace_sha256','usage','source_files_read_recognized','repeated_source_read_occurrences','source_search_or_listing_calls','test_or_assertion_shell_calls','commands']})
    fixture=BASE/'fixture';files=sorted((fixture/'src').rglob('*'));files=[p for p in files if p.is_file()]
    graph={str(p.relative_to(fixture)):[] for p in files}
    for p in files:
        rel=str(p.relative_to(fixture))
        for imp in re.findall(r"(?:from\s*|import\s*)['\"]([^'\"]+)['\"]",p.read_text()):
            if not imp.startswith('.'):continue
            target=p.parent/imp
            for candidate in [target,*[Path(str(target)+s) for s in ['.ts','.tsx','.css']],target/'index.tsx']:
                if candidate.is_file():graph[rel].append(str(candidate.resolve().relative_to(fixture)));break
    def shortest(start,end):
        queue=deque([[start]]);seen=set()
        while queue:
            chain=queue.popleft()
            if chain[-1]==end:return chain
            if chain[-1] in seen:continue
            seen.add(chain[-1]);queue.extend(chain+[n] for n in graph.get(chain[-1],[]))
    owners={'publish-actions':'src/features/projects/PublishDialog.tsx','project-filter':'src/features/projects/ProjectWorkspace.tsx',
            'seat-allocation':'src/features/team/SeatCounter.tsx','contact-validation':'src/features/settings/ContactForm.tsx'}
    tasks=json.loads((BASE/'tasks.json').read_text())['tasks'];paths=[]
    for task in tasks:
        source=task['responsible']['file'];paths.append(dict(task=task['id'],visualFeature=owners[task['id']],responsible=source,
            importPath=shortest(owners[task['id']],source),instructionLiteralInResponsibleFile=task['instruction'] in (fixture/source).read_text(),
            responsibleFileHasUIControlLabel=any(label in (fixture/source).read_text() for label in ['Publish update','Add five seats','Owner email','Filter projects'])))
    names=Counter(p.name for p in files)
    complexity=dict(sourceFiles=len(files),tsxFiles=sum(p.suffix=='.tsx' for p in files),componentModules=sum(p.suffix=='.tsx' and bool(re.search(r'export function [A-Z]',p.read_text())) for p in files),cssFiles=sum(p.suffix=='.css' for p in files),
        cssModules=sum(p.name.endswith('.module.css') for p in files),sourceUTF8Bytes=sum(p.stat().st_size for p in files),sourcePhysicalLines=sum(len(p.read_text().splitlines()) for p in files),
        importEdges=sum(map(len,graph.values())),duplicateBasenames={k:n for k,n in names.items() if n>1},routes=['projects','team','settings','reports'],
        localizationPaths=paths,importGraph=graph,
        assessment='Eligible for an exploratory matched pilot: visible labels resolve to shared copy, markup owners delegate through components/hooks/policies, CSS classes are module-scoped, and working decoys remain active. This is structural evidence, not observed agent difficulty or guaranteed savings. Four authored fixes remain small; source paths are meaningful. Do not claim repository scale or generality.')
    report=dict(kind='offline-existing-trace-and-structural-localization-audit',newModelCalls=0,profileSource=str(profile.relative_to(ROOT)),profileSHA256=sha(profile),groups=groups,
        traceReceipts=trace_receipts,complexity=complexity,
        limits=old['limits']+['Group usage means are descriptive and use available telemetry only. Pilot/revised historical records remain explicitly labelled; these group means are not matched causal estimates.',
          'Command output sizes are recorded UTF-8 bytes, not tokenizer input costs. No tokens assigned to commands, searches, reads, tests, images or file sizes.',
          'New-fixture localization difficulty has not been observed with agents. Reassess after the pilot; improve before larger repetitions if all A tasks are located immediately.'])
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=BASE/'reports/audit.json');out=parser.parse_args().output
    if out.exists():raise ValueError('Preserve audit; choose or archive another revision explicitly')
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'groups':groups,'complexity':{k:v for k,v in complexity.items() if k!='importGraph'}},indent=2))

if __name__=='__main__':main()
