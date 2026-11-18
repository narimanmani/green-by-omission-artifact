#!/usr/bin/env python3
import ast,csv,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from run_protected_ci import ROOT,OUT,CASES,cli,git
sys.path.insert(0, str(ROOT / "upstream"))  # load original source without installing a wheel
from testmon.process_code import Module

def static_controls():
    rows=[]
    for case,(target,security) in CASES.items():
        p=OUT/'workspaces'/case/'single_file_collision'
        assert (p/'.git').is_dir(),p
        got=cli(p,[sys.executable,'-m','pytest','-p','diffguard','--static-diff','-vv'],f'static_diff/{case}')
        row={'case':case,'independent_policy':'Git diff + static AST transitive imports (authored comparator)',
             'selected_exit':got['exit'],'selected_count':got['collect_count'],
             'detected_security_failure':got['exit']==1 and security in got['stdout'],
             'stdout_tail':got['stdout'][-700:],'log':got['log']}
        rows.append(row)
        print('STATIC',case, row['detected_security_failure'],flush=True)
    with (OUT/'static_comparator.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    assert all(x['detected_security_failure'] for x in rows)

def verify_crc_guard(case, root):
    target=CASES[case][0];src=(root/target).read_text()
    orig=git(root,'show','main:'+target)
    t=time.perf_counter_ns()
    original_ast=ast.dump(ast.parse(orig),include_attributes=False)
    current_ast=ast.dump(ast.parse(src),include_attributes=False)
    crc_equal=sorted(Module(source_code=orig).method_checksums)==sorted(Module(source_code=src).method_checksums)
    ast_different=original_ast!=current_ast
    suspicious=crc_equal and ast_different
    overhead_ms=(time.perf_counter_ns()-t)/1e6
    return {'case':case,'crc_equal':crc_equal,'ast_different':ast_different,
            'suspicious_collision':suspicious,'analysis_ms':round(overhead_ms,4)}

def run_guard():
    rows=[]
    for case,(_,security) in CASES.items():
        p=OUT/'workspaces'/case/'single_file_collision'
        info=verify_crc_guard(case,p)
        if info['suspicious_collision']:
            outcome=cli(p,[sys.executable,'-m','pytest','-vv'],f'ast_guard/{case}/fail_closed_full')
        else:
            outcome=cli(p,[sys.executable,'-m','pytest','-p','testmon.pytest_testmon','--testmon','-vv'],f'ast_guard/{case}/native')
        info.update({'guarded_exit':outcome['exit'],'security_failure_detected':outcome['exit']==1 and security in outcome['stdout'],
                     'fallback_tests_collected':outcome['collect_count'],'log':outcome['log']})
        rows.append(info)
        print('GUARD',case,'suspicious',info['suspicious_collision'],'caught',info['security_failure_detected'],'ms',info['analysis_ms'],flush=True)
    with (OUT/'ast_integrity_guard.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    assert all(x['security_failure_detected'] for x in rows)

def comment_controls():
    # Pure comment edits intentionally leave executable AST unchanged, so the
    # integrity guard must NOT flag them as adversarial CRC collisions.
    rows=[]
    for case,(target,security) in CASES.items():
        p=OUT/'workspaces'/case/'comment_control'
        from run_protected_ci import make_case
        src,p,_=make_case(case,'comment_control')
        original=(p/target).read_text()
        modified='# benign maintenance comment only\n'+original
        (p/target).write_text(modified)
        git(p,'checkout','-qb','pr/comment-only')
        git(p,'add',target);git(p,'commit','-qm','comment-only source edit')
        z=verify_crc_guard(case,p)
        z['guard_false_positive']=z['suspicious_collision']
        rows.append(z)
        print('COMMENT',case,'crc same',z['crc_equal'],'ast same',not z['ast_different'],'flagged',z['suspicious_collision'],flush=True)
    with (OUT/'comment_controls.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    assert all(not x['guard_false_positive'] for x in rows)

if __name__=='__main__':
    static_controls();run_guard();comment_controls()
