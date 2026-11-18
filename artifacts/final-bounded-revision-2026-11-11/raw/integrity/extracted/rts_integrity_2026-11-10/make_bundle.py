#!/usr/bin/env python3
"""Build the evidence archive from an explicit allowlist; no toolchain settings included."""
import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parent
TOP='rts_integrity_2026-11-10'
STAGE=ROOT/'release_bundle'/TOP

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if STAGE.exists():shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for name in ['README_RESEARCH.txt','analyze_study.py','reproduce.py','make_bundle.py']:
        shutil.copy2(ROOT/name,STAGE/name)
    excluded={'venv','work','native_work','maven_validation_work','__pycache__','archives'}
    for name in ['ekstazi_study','testmon_pilot','project_sample','methods_review','deliverables']:
        for p in sorted((ROOT/name).rglob('*')):
            rel=p.relative_to(ROOT)
            if p.is_file() and not p.is_symlink() and not (set(rel.parts)&excluded) and p.suffix!='.zip':
                dest=STAGE/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    (STAGE/'toolchain').mkdir()
    for name in ['org.ekstazi.core-5.3.0.jar','org.ekstazi.core-5.3.0-sources.jar','junit-4.13.2.jar','hamcrest-core-1.3.jar','download_manifest.json']:
        shutil.copy2(ROOT/'toolchain'/name,STAGE/'toolchain'/name)
    # Concrete portability check: regenerate report from moved evidence, without tests/network.
    result=subprocess.run([sys.executable,STAGE/'analyze_study.py'],capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    for name in ['research_report.html','controlled_results.csv','publication_tables.tex','summary.json','descriptive_statistics.json']:
        if digest(ROOT/'deliverables'/name)!=digest(STAGE/'deliverables'/name):
            raise RuntimeError('Relocated analysis differs: '+name)
    class CountHTML(HTMLParser):
        def __init__(self):super().__init__();self.counts={}
        def handle_starttag(self,tag,attrs):self.counts[tag]=self.counts.get(tag,0)+1
    parser=CountHTML();parser.feed((STAGE/'deliverables/research_report.html').read_text())
    assert parser.counts.get('table')==7 and parser.counts.get('h2')==13
    assert len(json.loads((STAGE/'deliverables/controlled_results.json').read_text()))==162
    manifest={str(p.relative_to(STAGE)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(STAGE.rglob('*')) if p.is_file()}
    (STAGE/'ARTIFACT_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    out=ROOT/'deliverables/rts_integrity_evidence_2026-11-10.zip'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(STAGE.rglob('*')):
            if p.is_file():z.write(p,TOP+'/'+str(p.relative_to(STAGE)))
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('ZIP CRC verification failed: '+bad)
        if any('settings.xml' in n or '/venv/' in n for n in z.namelist()):raise RuntimeError('Unexpected runtime configuration in archive')
        entries=len(z.namelist())
    print(json.dumps({'archive':str(out),'bytes':out.stat().st_size,'sha256':digest(out),'entries':entries,
                     'relocated_analysis_identical':True,'html_tables':parser.counts['table'],'html_sections':parser.counts['h2'],'comparison_rows':162},indent=2))

if __name__=='__main__':main()
