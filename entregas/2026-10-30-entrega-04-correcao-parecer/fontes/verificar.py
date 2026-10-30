"""Verify the corrected public package without launching or reclassifying experiments."""
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
PUBLIC=REPO/'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def source_sha(path):
    data=path.read_bytes()
    if path.suffix.lower()!='.png':data=data.replace(b'\r\n',b'\n')
    return hashlib.sha256(data).hexdigest()

def require(condition,message):
    if not condition:raise ValueError(message)

def verify(current_sources=False):
    pdf=ROOT/'TCC-Entrega04-correcoes.pdf'
    reader=PdfReader(pdf)
    text='\n'.join(p.extract_text() for p in reader.pages)
    require(len(reader.pages)==86,'unexpected pagination')
    for phrase in ['ABSTRACT','Palavras-chave','LISTA DE QUADROS','Pontos fortes','Avaliação do sistema','Contribuições','Leitura exploratória da recuperação operacional']:
        require(phrase.lower() in text.lower(),'missing section: '+phrase)
    require('PRZYBYŁEK' in text and 'KAZANAVIČIUS' in text and 'MAŽEIKA' in text,'uppercase names not preserved')
    require('Profa. Dra. Alessandra Bussador' in text,'advisor title differs')
    require('??' not in text,'unresolved text marker')
    revision=json.loads((ROOT/'VALIDACAO-REVISAO.json').read_text(encoding='utf-8'))
    require(sha(pdf)==revision['pdf']['sha256'],'PDF differs from recorded revision')
    if current_sources:
        require(sha(pdf)==sha(REPO/'output/pdf/TCC-2026-final.pdf'),'current PDF copies differ')
        for source in revision['source_files']:
            require(source_sha(REPO/source['path'])==source['sha256'],'current source differs: '+source['path'])
    for line in (PUBLIC/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1);path=(PUBLIC/name).resolve()
        require(PUBLIC.resolve() in path.parents and sha(path)==digest,'original campaign changed: '+name)
    catalog=json.loads((PUBLIC/'catalog.json').read_text())
    require((catalog['planned_runs'],catalog['complete_original_evidence'],catalog['partial_commit_timing'])==(65,64,1),'campaign reclassified')
    exploration=json.loads((ROOT/'recuperacao-exploratoria.json').read_text(encoding='utf-8'))
    require((exploration['original_observed'],exploration['exploratory_observed'])==(1,5),'recovery sensitivity differs')
    require(sum(r['verified_files'] for r in exploration['runs'])==115,'raw verification scope differs')
    original=REPO/'entregas/2026-10-27-entrega-04-java-final'
    require(sha(original/'TCC-Entrega04-final.pdf')=='56431f7482c5f90eec7a4501dabc70da1a965fceed49e660913b8495e4aed1e5','historical PDF changed')
    for line in (original/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1); require(sha(original/name)==digest,'historical package changed: '+name)
    for path,digest in {
        'implementacao-java/experimento/FROZEN-PROTOCOL.json':'e2330aaa67d0df9369c1263ab3a9dca057027f72df1814496260b281be6f2d5b',
        'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/plan.csv':'4091d5891657c6d0d80614d4133fd776e80d93d1b342148978c6fad7022a8148',
        'implementacao-java/.runtime/reduzida65-2026-10-27-r2/state.json':'53d73836e736758b0ce11a48ff2b1a04197b611b6e612252fd193df6d06b4209'
    }.items():
        if (REPO/path).exists():require(sha(REPO/path)==digest,'frozen operational evidence changed: '+path)
    items={}
    for line in (ROOT/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1);path=(ROOT/name).resolve()
        require(ROOT in path.parents and name not in items and sha(path)==digest,'new package mismatch: '+name)
        items[name]=digest
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts}
    require(actual==set(items),'new package inventory incomplete')
    return dict(pdf_pages=len(reader.pages),package_files=len(items),campaign=dict(complete=64,partial=1),
                recovery=dict(original=1,exploratory=5,total=5),historical_package_unchanged=True,
                author_personal_review_pending=True,institutional_approval_not_claimed=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--write-checksums',action='store_true');parser.add_argument('--current-sources',action='store_true');args=parser.parse_args()
    if args.write_checksums:
        files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts)
        (ROOT/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in files),encoding='utf-8')
    print(json.dumps(verify(args.current_sources),ensure_ascii=False))
