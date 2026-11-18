#!/usr/bin/env python3
"""Rebuild the research report and descriptive tables from recorded observations.

No network access, no experiment execution, and no statistical population claims.
"""
import collections
import csv
import html
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'deliverables'

def read(p):return json.loads(p.read_text())
def esc(v):return html.escape(str(v))
def table(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'
def latex(s):
    return str(s).replace('\\',r'\textbackslash{}').replace('&',r'\&').replace('%',r'\%').replace('_',r'\_').replace('#',r'\#')
def tex_table(label,caption,headers,rows):
    return '\n'.join([r'\begin{table*}[t]',r'\centering',r'\small',r'\caption{'+caption+'}',r'\label{tab:'+label+'}',
      r'\begin{tabular}{'+'l'*len(headers)+'}',r'\toprule',' & '.join(map(latex,headers))+r' \\',r'\midrule']+
      [' & '.join(map(latex,row))+r' \\' for row in rows]+[r'\bottomrule',r'\end{tabular}',r'\end{table*}',''])

def main():
    OUT.mkdir(exist_ok=True)
    loc=read(ROOT/'ekstazi_study/latest_result.json')
    # Archived dependency paths are evidence only. Resolve the data locally after extraction.
    native_dir=ROOT/'ekstazi_study/results'/Path(loc['path']).name
    ek=read(native_dir/'results.json'); controls=read(native_dir/'controls.json')
    mon=read(ROOT/'testmon_pilot/derived_results.json')
    mc=[r for r in mon if r['repetition']>0]
    wrappers=read(ROOT/'project_sample/wrapper_pilot/results.json')
    wc=[r for r in wrappers if r['scenario'] in ['ordinary_change','target_metadata_missing','target_metadata_truncated_50pct']]
    maven=read(ROOT/'ekstazi_study/maven_validation/results.json')
    audit=read(ROOT/'project_sample/audit_totals.json')
    repos=read(ROOT/'project_sample/repository_audit_summary.json')
    artifacts=read(ROOT/'project_sample/pilot_artifact_manifest.json')
    normalized=[]
    for r in ek:
        normalized.append({'experiment':'ekstazi_native','subject':'synthetic_arithmetic','condition':r['case_id'],
          'strategy':r['strategy'],'repetition':r['repetition'],'exit_code':r['returncode'],
          'methods_executed':r['methods_executed'],'intended_failures_detected':len(set(r['tests_failed'])&set(r['oracle_failing_tests'])),
          'runner_error':r['execution_status']!='completed','false_green':r['false_green'],
          'omission_assessable':r['execution_status']=='completed',
          'relevant_selection_omissions':len(r['relevant_tests_omitted']) if r['execution_status']=='completed' else None,
          'fallback':r['fallback'],'elapsed_seconds':r['total_seconds']})
    for r in mc:
        normalized.append({'experiment':'testmon_native','subject':'synthetic_arithmetic','condition':r['fault'],
          'strategy':r['strategy'],'repetition':r['repetition'],'exit_code':r['exit_code'],
          'methods_executed':r['tests'],'intended_failures_detected':r['oracle_tests_detected'],
          'runner_error':r['status']=='runner_error','false_green':r['false_accept'],
          'omission_assessable':r['omission_assessable'],'relevant_selection_omissions':r['selection_omission_count'],
          'fallback':r['full_suite_fallback'],'elapsed_seconds':r['elapsed_s']})
    for r in wc:
        normalized.append({'experiment':'java_library_wrapper','subject':r['project'],'condition':r['scenario'],
          'strategy':r['arm'],'repetition':1,'exit_code':r['returncode'],'methods_executed':r['run_count'],
          'intended_failures_detected':int(r['expected_relevant_failure_observed']),
          'runner_error':r['parse_status']!='parsed','false_green':r['returncode']==0,
          'omission_assessable':r['parse_status']=='parsed',
          'relevant_selection_omissions':int(not r['relevant_test_executed']) if r['parse_status']=='parsed' else None,
          'fallback':r['fallback'],'elapsed_seconds':r['elapsed_seconds']})
    summary={'date':'2026-11-10','analyzed_process_invocations':len(ek)+len(controls)+len(mon)+len(wrappers)+len(maven),
      'changed_source_comparisons':len(normalized),'expected_assertion_failure_completions':sum(r['intended_failures_detected']>0 for r in normalized),
      'runner_errors':sum(r['runner_error'] for r in normalized),'false_green_comparisons':sum(r['false_green'] for r in normalized),
      'selection_omissions_among_assessable_runs':sum(r['relevant_selection_omissions'] or 0 for r in normalized if r['omission_assessable']),
      'scope':'Finite designed corpus; not a probability sample. Repeated invocations are not independent security trials.',
      'native_ekstazi_conditions':8,'native_ekstazi_repetitions':3,'testmon_conditions':5,'testmon_repetitions':3,
      'library_wrappers':5,'wrapper_conditions_per_project':3,'wrapper_repetitions':1,'static_audit':audit}
    assert summary['analyzed_process_invocations']==189
    assert summary['changed_source_comparisons']==162
    assert summary['expected_assertion_failure_completions']==156 and summary['runner_errors']==6
    assert summary['false_green_comparisons']==0
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (OUT/'controlled_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(normalized[0]));w.writeheader()
        for r in normalized:w.writerow({k:('N/A' if v is None else v) for k,v in r.items()})
    (OUT/'controlled_results.json').write_text(json.dumps(normalized,indent=2)+'\n')
    groups=collections.defaultdict(list)
    for r in normalized:groups[(r['experiment'],r['subject'],r['condition'],r['strategy'])].append(r)
    stats=[]
    for key,rr in groups.items():
        outcomes={(r['exit_code'],r['methods_executed'],r['intended_failures_detected'],r['runner_error'],r['false_green'],r['relevant_selection_omissions'],r['fallback']) for r in rr}
        stats.append(dict(zip(['experiment','subject','condition','strategy'],key),n=len(rr),
          identical_discrete_outcomes=len(outcomes)==1,
          elapsed_median_seconds=statistics.median(r['elapsed_seconds'] for r in rr),
          elapsed_min_seconds=min(r['elapsed_seconds'] for r in rr),elapsed_max_seconds=max(r['elapsed_seconds'] for r in rr),
          runner_errors=sum(r['runner_error'] for r in rr),false_greens=sum(r['false_green'] for r in rr)))
    (OUT/'descriptive_statistics.json').write_text(json.dumps({'groups':stats,
       'inference':'No significance tests, confidence intervals, or rule-of-three bound: fixed faults and technical repeats do not provide independent random trials.',
       'timing':'Wall times are descriptive, include startup, and were collected during concurrent local research; no production speed claim.'},indent=2)+'\n')
    labels={'none':'Intact','missing_target':'Target record missing','empty_target':'Target record empty',
      'half_truncated_target':'Target record half truncated','invalid_header':'Invalid target header','missing_cache':'Entire cache missing',
      'unexpected_file':'Unexpected cache file','wrong_baseline_id':'Wrong declared baseline ID'}
    ek_rows=[]
    for fault in labels:
        row=[labels[fault]]
        for strat in ['standard_rts','verified_rts','full_suite']:
            rr=[r for r in ek if r['case_id']==fault and r['strategy']==strat]
            assert len(rr)==3
            assert len({(r['methods_executed'],r['failures'],r['fallback']) for r in rr})==1
            row.append(f"{rr[0]['methods_executed']} / {rr[0]['failures']}"+(' (fallback)' if rr[0]['fallback'] else ''))
        ek_rows.append(row)
    mon_rows=[]
    for fault,label in [('none','Intact'),('missing','Missing cache'),('empty','Empty cache'),('half_truncated','Half-truncated cache'),('garbage','Garbage cache')]:
        row=[label]
        for strat in ['standard_rts','fail_closed','full_suite']:
            rr=[r for r in mc if r['fault']==fault and r['strategy']==strat];r=rr[0]
            row.append('Runner error 3; 0 tests' if r['status']=='runner_error' else f"{r['tests']} / {r['failures']}"+(' (fallback)' if r['full_suite_fallback'] else ''))
        mon_rows.append(row)
    wrapper_rows=[]
    for name,version in [('cli','1.6.0'),('csv','1.10.0'),('codec','1.16.0'),('io','2.15.0'),('lang','3.14.0')]:
        rr=[r for r in wc if r['project']==name and r['arm']=='standard_rts']
        wrapper_rows.append(['Commons '+name.upper() if name in ['cli','csv','io'] else 'Commons '+name.title(),version,'3 / 0','0 / 0']+
          [f"{r['run_count']} / {r['failure_count']}" for r in rr])
    audit_rows=[['Optional root Ekstazi profile',audit['optional_ekstazi_profile_declared'],'20 repositories'],
      ['Explicit Ekstazi workflow reference',audit['ekstazi_any_workflow_reference'],'20 repositories'],
      ['Primary workflow pull_request trigger',audit['primary_pull_request_trigger'],'20 primary workflows'],
      ['Primary contents permission read',audit['primary_contents_permission_read'],'20 primary workflows'],
      ['Primary actions pinned to 40-hex commits',audit['primary_all_actions_pinned_40hex'],'20 primary workflows'],
      ['Primary checkout persist-credentials false',audit['primary_checkouts_persist_credentials_false'],'20 primary workflows'],
      ['Explicit primary Maven dependency cache',audit['primary_maven_dependency_cache'],'20 primary workflows']]
    control_rows=[['Ekstazi native cold',4,0,'Pass'],['Ekstazi native warm',0,0,'Pass'],['Ekstazi ordinary change',3,2,'Expected failure'],['Ekstazi changed full suite',4,2,'Expected failure'],
                  ['Maven cold',len(maven[0]['tests_executed']),0,'Pass'],['Maven warm',len(maven[1]['tests_executed']),0,'Pass'],['Maven ordinary change',len(maven[2]['tests_executed']),2,'Expected failure'],['Maven changed full suite',len(maven[3]['tests_executed']),2,'Expected failure']]
    latex_text='% Generated from recorded observations. Requires \\usepackage{booktabs}.\n% Counts are test methods; fixed fault repetitions are not independent trials.\n\n'
    latex_text+=tex_table('ekstazi-controls','Native Ekstazi and supplemental Maven controls. Failures are intentionally seeded arithmetic assertion failures.',['Control','Executed','Failures','Outcome'],control_rows)
    latex_text+=tex_table('ekstazi-faults','Ekstazi 5.3.0 controlled integrity-fault outcomes. Each cell is executed methods / intended failures; identical across three repetitions. The baseline-ID condition changes the harness provenance label only.',['Metadata condition','Standard RTS','Verified RTS','Full suite'],ek_rows)
    latex_text+=tex_table('testmon-faults','pytest-testmon 2.3.0 controlled cache-fault outcomes. Each normal cell is executed tests / intended failures, identical across three repetitions. Exit 3 is a runner error; selection omission is not assessable.',['Metadata condition','Standard RTS','Verified RTS','Full suite'],mon_rows)
    latex_text+=tex_table('wrapper-pilot','Five synthetic wrappers calling unmodified published Java libraries. Entries are executed methods / intended failures; one observation per cell. Upstream regression suites were not run.',['Library','Version','Cold','Warm','Normal change','Missing record','Half truncated'],wrapper_rows)
    latex_text+=tex_table('static-audit','Static indicators in a purposive sample of 20 commit-pinned Apache Commons repositories. This does not estimate deployed RTS prevalence.',['Indicator','Observed','Denominator'],audit_rows)
    (OUT/'publication_tables.tex').write_text(latex_text)
    timing_rows=[]
    for exp in ['ekstazi_native','testmon_native']:
        for strat in ['standard_rts','verified_rts' if exp=='ekstazi_native' else 'fail_closed','full_suite']:
            rr=[r for r in normalized if r['experiment']==exp and r['condition']=='none' and r['strategy']==strat]
            timing_rows.append([exp,strat,len(rr),f"{statistics.median(r['elapsed_seconds'] for r in rr):.3f}",f"{min(r['elapsed_seconds'] for r in rr):.3f}–{max(r['elapsed_seconds'] for r in rr):.3f}"])
    source_links=''.join('<li><a href="'+esc(r['upstream_source_url'])+'">'+esc(r['repository'])+'</a> — <code>'+r['commit']+'</code></li>' for r in repos)
    evidence_rows=[['Ekstazi native matrix',str(native_dir.relative_to(ROOT))+'/results.json','72 comparisons + 4 controls'],
      ['Maven integration','ekstazi_study/maven_validation/results.json','4 offline controls'],
      ['Testmon public classifications','testmon_pilot/derived_results.json','45 comparisons + 4 controls'],
      ['Library wrappers','project_sample/wrapper_pilot/results.json','45 comparisons + 15 controls'],
      ['Static repository audit','project_sample/repository_audit_summary.json','20 snapshots'],
      ['Independent audit','methods_review/audit.json','Raw logs / XML / hashes cross-checked'],
      ['Normalized comparison data','deliverables/controlled_results.csv','162 changed-source comparison rows']]
    body=f'''<header><p class="eyebrow">SP2027 · DEFENSIVE RTS RESEARCH · 10 NOVEMBER 2026</p>
<h1>Regression test selection under controlled metadata-integrity faults</h1>
<p class="subtitle">Measured native behavior, synthetic library feasibility, and a reproducible configuration audit</p></header>
<section class="finding"><h2>Main finding</h2><p><strong>No relevant-test omission was observed in completed runs, and no changed-source comparison returned a passing result.</strong> The study contains {summary['analyzed_process_invocations']} analyzed local runner invocations: {summary['changed_source_comparisons']} changed-source comparisons and 27 controls or supplemental integration checks. Of the comparisons, 156 completed with the intended assertion failures; six testmon invocations stopped with explicit database errors. Those errors are not selection omissions or passing builds.</p>
<p>The positive defense result is narrower: a trusted-manifest check detected the deliberately injected metadata faults and invoked an agent-free full suite. For testmon's two corrupted-database conditions, this recovered executable regression evidence from otherwise aborted runs. Standard Ekstazi already detected every seeded regression in this corpus, so these data show no incremental defect-detection benefit from the guard for Ekstazi.</p></section>
<section><h2>1. Questions and scope</h2><p>The experiment asks whether cold/warm selection works, whether ordinary harmless regressions are detected, how the native selectors respond to fixed integrity faults, and what a fail-closed check changes. It does not test an adversary's ability to reach, replace, or exploit a real CI cache.</p>
<p>All dynamic subjects were locally generated synthetic applications and test fixtures. Five fixtures call unmodified published Java libraries. No upstream source, remote repository, production system, or CI workflow was modified. Dependencies and public repository snapshots were downloaded during preparation; actual fixture executions perform no network I/O. Isolation means separate local workspaces and processes, not a claimed container or enforced network namespace.</p>
<p>The same unchanged tests act as the oracle across arms. A +1 arithmetic change intentionally violates two assertions in the Java/Python toy programs. Java library wrappers append a harmless exclamation mark to a returned value, violating one synthetic assertion. An independently changed module retains its correct output, ensuring a passing changed control is available, while another module stays untouched.</p></section>
<section><h2>2. Versions and controls</h2><p>Ekstazi uses the unmodified Maven Central core 5.3.0 binary with native JUnit instrumentation, JUnit 4.13.2, and Temurin JDK 8u432-b06. The core SHA-256 is <code>baf7affe8fc42e12b382ec933f3572fce417e5e0d9a7ebab2902bc5c614cb749</code>. Supplemental Maven controls use Maven 3.8.8 and Surefire 2.22.2. Testmon uses pytest-testmon 2.3.0, pytest 8.4.2, coverage 7.10.6, and Python 3.12.14. Full artifact hashes and environment records accompany the data.</p>
{table(['Control','Executed methods','Failures','Observed outcome'],control_rows)}
<p>The direct native fault matrix uses three test classes containing four methods. Counts above refer to executed methods, not selector decision units. Cold execution creates three native dependency records; warm execution skips all methods. The Maven controls run offline with explicit <code>select</code> and <code>restore</code> goals and a local excludes file. They establish basic integration behavior, not a full Maven fault matrix or hosted CI result.</p></section>
<section><h2>3. Paired experiment design</h2><p>Each condition starts from the same warmed baseline restored at the same absolute path. This avoids accidental invalidation from relocated dependency paths. Full-suite arms run without the selector and receive their own restored state, preventing them from repairing metadata used by an RTS arm. Before and after hashes, test identities, actual process exits, native logs, JUnit observations, and test source hashes are retained.</p>
<p>The Ekstazi matrix has eight fixed conditions × three strategies × three technical repetitions: 72 comparisons. Faults include a missing or empty target dependency record, retaining the first floor(n/2) bytes, an invalid header, deleting the cache, adding an unexpected file, and supplying a wrong synthetic baseline label. The fraction is fixed; no adaptive byte search or fingerprint manipulation occurred. The baseline-label condition changes only the guard's declared provenance value; it is not evidence about restoring an actual older cache.</p>
<p>For native Ekstazi, a frozen seed shuffles condition/strategy order within each repetition. Testmon and wrapper ordering is fixed and disclosed. Testmon has five cache conditions × three strategies × three repetitions. Each library wrapper has three conditions × three strategies, with one observation per cell. These are designed case studies, not random samples of faults or deployments.</p></section>
<section><h2>4. Ekstazi integrity-fault results</h2><p>Each cell reports <strong>executed methods / intended failures</strong>. All three repetitions agree on discrete outcomes.</p>
{table(['Metadata condition','Standard RTS','Verified RTS','Full suite'],ek_rows)}
<p>All 72 changed-source comparisons completed and exposed both intended failures. No relevant failing method was omitted in the 24 standard-RTS invocations. Removing the entire cache executed all four methods; the other standard-RTS conditions executed three. This is measured native behavior under controlled fault simulation. It does not establish soundness for every possible metadata inconsistency.</p>
<p>The ordinary-change condition executes 3/4 methods, a 25% reduction in test-method count for this fixture. It provides no evidence of a runtime speedup. The guard triggered fallback for all seven fault definitions in all three repetitions (21 invocations) and preserved RTS in the intact condition.</p></section>
<section><h2>5. pytest-testmon comparison</h2><p>Each normal cell reports <strong>executed tests / intended failures</strong>. All three repetitions agree.</p>
{table(['Cache condition','Standard testmon','Verified testmon','Full suite'],mon_rows)}
<p>The four controls were cold 4/0, unchanged warm 0/0, full baseline 4/0, and changed full oracle 4/2. Missing and empty databases caused conservative execution. Half-truncated and garbage databases produced SQLite-related runner errors with exit code 3 and zero test executions. The omission metric is <strong>N/A</strong> for these six error invocations because no completed selection was observed.</p>
<p>Of 45 changed-source comparisons, 39 completed and exposed both intended failures; six explicitly aborted. None passed. The fail-closed guard rejected all four injected fault modes in all three repeats, leading to 12 full-suite fallbacks. The artifact preserves the original raw result fields and supplies corrected derived records that distinguish unexecuted oracle tests during an error from tests omitted by completed selection.</p></section>
<section><h2>6. Five-library feasibility pilot</h2><p>These cases use real released dependencies inside synthetic applications. They do not execute, validate, or modify the upstream regression suites. The library release commits and published artifact hashes are distinct from the current default-branch snapshots used for the configuration audit.</p>
{table(['Library','Version','Cold','Warm','Ordinary change','Missing record','Half truncated'],wrapper_rows)}
<p>Entries are methods executed / failures under standard RTS. Each fixture has three test methods. The full unchanged baseline also passed all three. Across the 15 project-by-condition cases, standard RTS executed the relevant method and observed its failure in every case. The guard ran all three methods in the 10 fault cases and retained two-method RTS execution in five intact cases. Full-suite execution always ran three methods and observed the one expected failure.</p>
<p>All 45 changed-source arm runs preserved both test source and compiled test bytecode. This establishes that the toolchain can exercise these five library APIs through controlled fixtures. It does not establish compatibility, selection soundness, or performance for each project's complete build and test suite.</p></section>
<section><h2>7. Static configuration sample</h2><p>The audit inspected 20 commit-pinned Apache Commons repositories, 156 repository configuration files, and seven transitive Maven parent POMs. Repository names were fixed in a manifest before the scanner read their configuration. The sample is purposive: all subjects share an organization, many share parent configuration, and prior search had already suggested RTS references in Math and Numbers.</p>
{table(['Static indicator','Observed count','Denominator'],audit_rows)}
<p>Commons Math declares Ekstazi 4.4.0 and Commons Numbers declares 5.3.0 in optional profiles activated by the <code>ekstazi</code> property. Neither profile is active by default. No inspected GitHub workflow explicitly mentions Ekstazi. The sample proportion is 2/20 (10%) for optional profile declarations, and 0/20 for explicit workflow mentions. These are configuration statistics; actual profile activation and deployed RTS usage remain unknown.</p>
<p>The listed safeguards describe each repository's primary <code>.github/workflows/maven.yml</code> file. They do not certify every workflow or external reusable action. Caching <code>~/.m2</code> is dependency caching, not proof that RTS dependency metadata is shared. Branch protection, mandatory checks, actual execution history, cache permissions, and external enforcement were not measured. The absence of a testmon string in this Java-only sample is not evidence about testmon adoption.</p>
<details><summary>All 20 immutable source snapshots</summary><ul>{source_links}</ul></details></section>
<section><h2>8. Defense interpretation</h2><p>The research guard compares a separately trusted SHA-256 manifest with the complete observed cache inventory. Native Ekstazi additionally binds the test source inventory, exact agent binary, and a synthetic expected baseline ID. Testmon checks cache bytes and test inventory. Library wrappers check cache inventory while separately verifying unchanged test source/bytecode. These are related guard prototypes, not identical fully authenticated CI systems.</p>
<p>On rejection, the driver executes the full suite with the selector disabled. A successful manifest comparison only shows agreement with a trusted snapshot. It does not prove that the original graph was complete, that cache generation was correct, that a baseline matches real repository history, or that the manifest itself cannot be replaced. No signing service, immutable remote cache policy, complete JDK/build provenance chain, or race-free verification/use boundary was implemented.</p>
<p>In this finite corpus, the guard provides integrity rejection and deterministic fallback. It does not improve Ekstazi's detected-regression count because the unguarded tool already detects every seeded regression. For testmon's corrupt-database cases, the benefit is recovering an executable diagnostic path; the unguarded process already failed and did not accept the regression.</p></section>
<section><h2>9. Descriptive statistical analysis</h2><p>The descriptive analysis unit is the designed fixture/condition, not each repeated invocation. Native Ekstazi and testmon repetitions verify repeatability. All 24 Ekstazi condition/strategy cells and all 15 testmon cells have identical discrete outcomes across their three repetitions. Five wrappers share one harness pattern and have only one observation per cell. Counting these as independent security trials would exaggerate evidence.</p>
<p>The report therefore provides counts, denominators, selected-test fractions, matched outcomes, and per-cell median/minimum/maximum wall times. It provides no p-values, attack-success confidence intervals, rule-of-three bounds, or population prevalence interval. The 162 comparison rows are an audit count, not a sample-size claim supporting general security rates.</p>
<h3>Ordinary-change timing observations only</h3>
{table(['Experiment','Strategy','Observations','Median seconds','Range seconds'],timing_rows)}
<p>These times include JVM/Python startup and local filesystem effects; root native timing includes verification when used and excludes compilation/reset. Testmon timing has a different measurement boundary. Parallel research activity and small test suites make cross-tool comparisons and production speed claims inappropriate. Exact timing boundaries are retained in each protocol.</p></section>
<section><h2>10. Validity threats and untested hypotheses</h2><ul>
<li><strong>Construct validity:</strong> harmless output regressions demonstrate detection behavior; they are not actual exploitable security defects. Generic damage does not cover every valid-but-incomplete dependency graph.</li>
<li><strong>External validity:</strong> one small arithmetic fixture per language, five closely related wrapper fixtures, one Java/JUnit configuration, one Python configuration, and a single-organization static sample.</li>
<li><strong>Mechanism coverage:</strong> native cache deletion, emptiness, truncation and malformed input were tested. Actual stale-cache restoration, graph completeness, selector concurrency, dynamically generated code, broad reflection patterns, and hosted cache permissions were not established.</li>
<li><strong>Internal validity:</strong> path-stable state restoration, independent full-suite arms, unchanged test hashes, fresh logs, and exact test identities reduce contamination. Setup attempts and the first harness directory-creation error are retained separately and excluded from the formal matrix.</li>
<li><strong>Defense assumptions:</strong> the manifest is protected from the injected faults. No proof is made for a setting where both cache and manifest are replaceable, or where metadata changes between verification and use.</li>
<li><strong>Statistical validity:</strong> deterministic repeats and purposive samples do not justify inference to all faults or deployments. Timing reflects concurrent local activity.</li>
<li><strong>Unconfirmed hypotheses:</strong> other integrity faults might omit relevant tests; deployed CI might restore untrusted metadata; stronger provenance controls might reduce failures in a broader corpus. None is established by these measurements.</li></ul>
<p>For an S&amp;P submission, these results support a reproducible defensive robustness pilot and negative findings for the tested faults. They do not support a claim that Ekstazi was bypassed or that an exploitable RTS vulnerability is prevalent. A defensible next extension would independently define broader non-adaptive fault classes, retain all negative outcomes, validate genuine larger suites under an explicitly expanded scope, and sample deployment configurations from a justified frame.</p></section>
<section><h2>11. Reproduction and evidence</h2><p>The archive includes fixed experiment scripts, dependency manifests, fixture sources, result JSON/CSV, raw stdout and JUnit XML, native metadata snapshots, frozen sampling rules, exact repository commits, SHA-256 inventories, descriptive analysis, and LaTeX publication tables. <code>analyze_study.py</code> rebuilds this report from the observations without network access. <code>reproduce.py</code> copies the scripts to a fresh experiment directory and regenerates native caches at that new path.</p>
{table(['Evidence','Archive path','Content'],evidence_rows)}
<p>Archived caches contain original absolute paths and are forensic evidence; they must not be reused at a new path as warmed caches. Reproduction starts cold and recollects dependencies. Java 8 runtime and Maven downloads are pinned; large runtime binaries and source-download intermediates are omitted from the archive. Bundled library artifacts are unchanged.</p>
<p>The initial Maven dynamic-attach path was unavailable in this environment. The explicit select/restore integration succeeded, and all four formally measured Maven controls ran in offline mode. Early DNS/proxy/dependency-setup failures remain separate from test results. No setup failure is counted as an RTS defect, regression omission, or successful defense.</p></section>
<section><h2>12. Primary sources</h2><ul>
<li><a href="https://mir.cs.illinois.edu/marinov/publications/GligoricETAL15EkstaziDemo.pdf">Gligoric, Eloussi, and Marinov, Ekstazi: Lightweight Test Selection</a>. Historical background: dependency information selects affected classes; missing information selects a class. Current findings above are measured against the exact 5.3.0 artifact.</li>
<li><a href="https://repo.maven.apache.org/maven2/org/ekstazi/org.ekstazi.core/5.3.0/org.ekstazi.core-5.3.0.jar">Published Ekstazi 5.3.0 core artifact</a>; exact hash recorded above. The published sources JAR contained directory entries and no Java source files; binary inspection was retained separately.</li>
<li><a href="https://github.com/apache/commons-math/blob/36cefd500d2b6a193bd81654665944db1bb1aaed/pom.xml">Pinned Commons Math POM</a> and <a href="https://github.com/apache/commons-numbers/blob/e6845beaca307b09bb02ae5ae625c63345bce130/pom.xml">pinned Commons Numbers POM</a>. Raw configuration bytes and hashes are included in the audit snapshots.</li>
<li>All other library release coordinates, artifact URLs, source commits, environment versions, and original measurement paths are in the accompanying manifests.</li></ul></section>'''
    css='''*{box-sizing:border-box}body{margin:0;background:#eef2f5;color:#182735;font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1120px;margin:36px auto;background:white;padding:52px 62px;box-shadow:0 4px 32px #17324d12}header{border-bottom:4px solid #21696c;padding-bottom:24px;margin-bottom:30px}.eyebrow{font-size:12px;font-weight:750;letter-spacing:.12em;color:#21696c}h1{font-size:38px;line-height:1.18;margin:14px 0;max-width:900px}h2{font-size:24px;line-height:1.3;margin:30px 0 14px}h3{font-size:18px}.subtitle{font-size:19px;color:#506373}.finding{background:#edf7f5;padding:12px 24px 20px;border-left:4px solid #21696c}.finding h2{margin-top:10px}section{margin-bottom:30px}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.45;margin:20px 0}th{background:#203e51;color:white;text-align:left;padding:11px 10px}td{border-bottom:1px solid #d7e0e6;padding:10px}tr:nth-child(even){background:#f4f7f9}code{font:12px/1.4 ui-monospace,monospace;overflow-wrap:anywhere}a{color:#12666b}li{margin:8px 0}details{background:#f4f7f9;padding:15px}summary{font-weight:600;cursor:pointer}@media print{body{background:white;font-size:10pt}main{margin:0;padding:0;box-shadow:none;max-width:none}h1{font-size:25pt}h2{font-size:16pt;break-after:avoid}table{font-size:8pt}tr{break-inside:avoid}header{margin-bottom:20px}.finding{break-inside:avoid}details{display:block}a{color:#193b49;text-decoration:none}}'''
    (OUT/'research_report.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>RTS defensive integrity study · 10 November 2026</title><style>'+css+'</style></head><body><main>'+body+'</main></body></html>')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
