#!/usr/bin/env python3
"""Bounded read-only audit of Phase 21 report/evidence references."""
from __future__ import annotations
import datetime, hashlib, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = [
    ROOT/'PHASE21_STATUS_REPORT.md', ROOT/'PHASE21_CURRENT_STATE.md',
    ROOT/'REQUIREMENTS_AUDIT.md', ROOT/'EVIDENCE_LEDGER.md',
    ROOT/'TARGET_CAPTURE_CHECKLIST.md', ROOT/'RESTORATION_FEASIBILITY_MATRIX.md',
]
# Local references are deliberately conservative: explicit evidence/paths and named workspace artifacts.
pat = re.compile(r'(?<![A-Za-z0-9_./-])(?:evidence/|PHASE21_FUNCTIONAL_RESEARCH/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?\.(?:json|md|txt|rom|py)')
refs = {}
for report in REPORTS:
    text = report.read_text(errors='replace')
    found = sorted(set(pat.findall(text)))
    resolved=[]
    missing=[]
    for raw in found:
        rel = raw
        if rel.startswith('PHASE21_FUNCTIONAL_RESEARCH/'):
            rel = rel.split('/',1)[1]
        candidates = [ROOT/rel, ROOT/'tools'/rel, ROOT/'evidence'/rel, ROOT.parent/rel, pathlib.Path('/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research')/rel]
        # Historical artifacts are retained under the workspace's work_v15 tree.
        if rel.startswith('RAW_DATA/'):
            candidates.append(ROOT.parent/'work_v15'/rel)
        if '/' not in rel:
            candidates += [ROOT.parent/'work_v15'/'TOPOLOGY'/rel, ROOT.parent/'work_v15'/'RAW_DATA'/rel, pathlib.Path('/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research')/rel, pathlib.Path('/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research/PHASE15')/rel]
        p = next((q for q in candidates if q.exists()), candidates[0])
        item={'reference':raw,'path':str(p.relative_to(ROOT.parent)) if p.exists() and p.is_relative_to(ROOT.parent) else str(p),'exists':p.exists()}
        if p.exists() and p.is_file():
            item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            item['size']=p.stat().st_size
            resolved.append(item)
        else:
            missing.append(item)
    refs[str(report.relative_to(ROOT))]={'references':resolved+missing,'missing':missing}
# Check machine-readable evidence paths in matrix/blocker register.
structured=[]
for name in ('evidence/requirement_matrix.json','evidence/blocker_register.json'):
    p=ROOT/name; obj=json.loads(p.read_text())
    for row in obj.get('rows',[]):
        paths=[]
        if 'artifact' in row: paths.append(row['artifact'])
        paths += row.get('evidence',[])
        for raw in paths:
            candidates=[ROOT/raw, ROOT/'evidence'/raw, ROOT/'tools'/raw, ROOT.parent/raw]
            if raw == 'saved_runtime_provenance.json': candidates.insert(0, ROOT/'evidence'/raw)
            q=next((z for z in candidates if z.exists()), candidates[0])
            structured.append({'source':name,'reference':raw,'path':str(q.relative_to(ROOT.parent)) if q.exists() else str(q.relative_to(ROOT)),'exists':q.exists(), 'sha256':hashlib.sha256(q.read_bytes()).hexdigest() if q.exists() and q.is_file() else None})
missing=[x for r in refs.values() for x in r['missing']] + [x for x in structured if not x['exists']]
# Some references intentionally describe artifacts that must be collected on the target or
# temporary comparison inputs that are not part of this checkout. Keep them visible without
# treating their absence as a broken report link.
expected=[]; hard_missing=[]
for item in missing:
    ref=item.get('reference','')
    if ref == 'target_package.json' or ref in ('gen3_a.rom','t_clk.rom'):
        item['classification']='EXPECTED_EXTERNAL_OR_TEMPORARY'; expected.append(item)
    else:
        hard_missing.append(item)
out={
 'schema':'phase21-artifact-integrity-v1',
 'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'explicit local references in core reports plus machine-readable matrix/blocker paths',
 'report_reference_audit':refs,
 'structured_reference_audit':structured,
 'missing_count':len(hard_missing),
 'missing':hard_missing,
 'expected_unresolved_count':len(expected),
 'expected_unresolved':expected,
 'status':'PASS' if not hard_missing else 'FAIL',
 'note':'Hash capture is an integrity snapshot; it does not prove current-target runtime or hardware capability.'
}
(ROOT/'evidence/artifact_integrity_audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print('artifact integrity:',out['status'],'reports=',len(REPORTS),'hard_missing=',len(hard_missing),'expected_unresolved=',len(expected),'structured=',len(structured))
raise SystemExit(0 if not hard_missing else 1)
