#!/usr/bin/env python3
"""Descriptive finite-corpus analysis; no population inference or p-values."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def main():
    results=json.loads((ROOT/'wrapper_pilot/results.json').read_text())
    relevant=[r for r in results if 'expected_relevant_test' in r]
    stats={'execution_count':len(results),'changed_execution_count':len(relevant),
           'projects':5,'scenarios_per_project':3,'repetitions_per_arm':1,
           'unit':'Project-by-fixed-scenario pair; not an independent probability sample.',
           'scope':'Synthetic wrapper fixtures invoking released libraries; no upstream suite validation.',
           'arms':{}}
    for arm in ['standard_rts','fail_closed','full_suite']:
        rr=[r for r in relevant if r['arm']==arm]
        stats['arms'][arm]={
          'eligible_cases':len(rr),
          'relevant_test_executed':sum(r['relevant_test_executed'] for r in rr),
          'relevant_failure_detected':sum(r['expected_relevant_failure_observed'] for r in rr),
          'omissions':sum(not r['relevant_test_executed'] for r in rr),
          'passes_despite_expected_failure':sum(r['returncode']==0 for r in rr),
          'integrity_fallbacks':sum(r['fallback'] for r in rr),
          'test_methods_executed':sum(r['run_count'] for r in rr),
          'test_method_opportunities':len(rr)*3,
          'selection_fraction':sum(r['run_count'] for r in rr)/(len(rr)*3),
        }
    stats['all_changed_runs_preserved_test_sources']=all(r['unchanged_test_sources'] for r in relevant)
    stats['all_changed_runs_preserved_test_bytecode']=all(r['unchanged_test_bytecode'] for r in relevant)
    stats['interpretation']='No omission was observed in these fixed fault cases. This neither proves general soundness nor establishes a security bypass.'
    stats['inferential_statistics']='Not reported: purposive projects, a shared wrapper pattern, deterministic chosen faults, and a single execution per arm do not support a defensible population probability model.'
    (ROOT/'wrapper_pilot/statistics.json').write_text(json.dumps(stats,indent=2)+'\n')
    versions={x['project'].split('commons-')[-1]:x['version'] for x in json.loads((ROOT/'pilot_artifact_manifest.json').read_text())}
    tex=[r'\begin{table}[t]',r'\centering',r'\caption{Native Ekstazi 5.3.0 observations in synthetic wrappers. Entries show executed/failed test methods. Each fixture has three test methods. Missing and truncated caches are simulated faults. Upstream regression suites were not run.}',r'\label{tab:wrapper-pilot}',r'\begin{tabular}{lccccc}',r'\hline',r'Library (version) & Ordinary & Missing & Half-file & Guard$^*$ & Full \\',r'\hline']
    for name in ['cli','csv','codec','io','lang']:
        cells=[]
        for scenario,arm in [('ordinary_change','standard_rts'),('target_metadata_missing','standard_rts'),('target_metadata_truncated_50pct','standard_rts'),('target_metadata_truncated_50pct','fail_closed'),('target_metadata_truncated_50pct','full_suite')]:
            r=next(r for r in relevant if r['project']==name and r['scenario']==scenario and r['arm']==arm)
            cells.append(f"{r['run_count']}/{r['failure_count']}")
        tex.append('Commons '+name.upper()+f' ({versions[name]}) & '+' & '.join(cells)+r' \\')
    tex += [r'\hline',r'\end{tabular}',r'\par\smallskip',r'\footnotesize $^*$SHA-256 guard falls back to full suite for both injected faults. The unchanged warm run executed zero tests in all five wrappers.',r'\end{table}']
    (ROOT/'wrapper_pilot/table_wrappers.tex').write_text('\n'.join(tex)+'\n')
    audit=json.loads((ROOT/'audit_totals.json').read_text())
    tex=[r'\begin{table}[t]',r'\centering',r'\caption{Static observations in 20 purposively selected Apache Commons repositories, pinned to immutable commits. These are configuration indicators, not deployment prevalence.}',r'\label{tab:configuration-audit}',r'\begin{tabular}{lr}',r'\hline',r'Indicator & Repositories \\',r'\hline']
    for label,key in [('Optional Ekstazi profile declared','optional_ekstazi_profile_declared'),('Ekstazi mentioned in inspected workflows','ekstazi_any_workflow_reference'),('Primary workflow has pull-request trigger','primary_pull_request_trigger'),('Primary contents permission is read','primary_contents_permission_read'),('Primary external actions pinned to 40-hex SHAs','primary_all_actions_pinned_40hex'),('Primary checkout disables credential persistence','primary_checkouts_persist_credentials_false'),('Explicit primary Maven dependency cache','primary_maven_dependency_cache')]:
        tex.append(label+f" & {audit[key]}/20"+r' \\')
    tex += [r'Live RTS deployment or required-check enforcement & Unmeasured \\',r'\hline',r'\end{tabular}',r'\end{table}']
    (ROOT/'table_configuration_audit.tex').write_text('\n'.join(tex)+'\n')
    print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
