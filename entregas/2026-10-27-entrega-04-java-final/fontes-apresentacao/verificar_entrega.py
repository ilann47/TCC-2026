"""Verify this delivery without launching experiments or editing historical files."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
REPORT = REPO / 'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2'
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(value, message):
    if not value: raise ValueError(message)


def verify():
    scientific = json.loads((REPORT / 'VALIDACAO-FINAL.json').read_text(encoding='utf-8'))
    require(sha(ROOT / 'TCC-Entrega04-final.pdf') == scientific['pdf_sha256'] == sha(REPO / 'output/pdf/TCC-2026-final.pdf'), 'PDF differs from scientific closure')
    require(sha(ROOT / 'evidencias/catalogo-campanha.json') == scientific['catalog_sha256'] == sha(REPORT / 'resultados-a1/catalog.json'), 'catalog copy differs')
    require(sha(ROOT / 'evidencias/validacao-cientifica.json') == sha(REPORT / 'VALIDACAO-FINAL.json'), 'scientific validation copy differs')
    require(sha(ROOT / 'Apresentacao-Entrega04-final.pptx') == '43e8b0ea342d3f550c16465d0020f4a68380e5c296e68abb5e95fc0a1d64e247', 'PPTX differs from visually reviewed version')
    with ZipFile(ROOT / 'Apresentacao-Entrega04-final.pptx') as archive:
        require(archive.testzip() is None, 'invalid PPTX archive')
        owners = []
        texts = []
        for number in range(1, 11):
            xml = ET.fromstring(archive.read(f'ppt/slides/slide{number}.xml'))
            if xml.findall('.//a:tbl', NS): owners.append(number)
            texts.append(' '.join(node.text or '' for node in xml.findall('.//a:t', NS)))
            note = ET.fromstring(archive.read(f'ppt/notesSlides/notesSlide{number}.xml'))
            require(len(' '.join(node.text or '' for node in note.findall('.//a:t', NS))) > 100, 'speaker notes absent')
        require(owners == [4, 5, 6, 7, 8, 9], 'editable table owners changed')
        size = ET.fromstring(archive.read('ppt/presentation.xml')).find('p:sldSz', NS)
        require(size.attrib['cx'] == '12192000' and size.attrib['cy'] == '6858000', 'slide size changed')
        require('4,34' in texts[3] and '2,60' in texts[3] and '3,92' in texts[3] and '5,83' in texts[3], 'latency table differs')
        require('8.352' in texts[5] and '10.790' in texts[5] and '14' in texts[5] and '2.452' in texts[5], 'destination table differs')
        require('4 pares' in texts[7] and '1 de 1.667' in texts[7], 'A1 caveat absent')
        require('1 de 5' in texts[8] and '38,71' in texts[8] and 'DLQ' in texts[8], 'recovery caveat absent')
    catalog = json.loads((ROOT / 'evidencias/catalogo-campanha.json').read_text(encoding='utf-8'))
    require((catalog['planned_runs'], catalog['complete_original_evidence'], catalog['partial_commit_timing']) == (65, 64, 1), 'campaign classification changed')
    inventory = {}
    for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ', 1)
        path = (ROOT / name).resolve()
        require(ROOT in path.parents and name not in inventory and sha(path) == digest, 'checksum/path mismatch: ' + name)
        inventory[name] = digest
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS'}
    require(set(inventory) == actual, 'delivery checksum inventory incomplete')
    return {'delivery_files_hashed': len(inventory), 'slides': 10, 'notes': 10, 'native_table_slides': owners,
            'pdf_identical_to_scientific_closure': True, 'campaign': {'complete': 64, 'partial': 1},
            'native_powerpoint_application_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-checksums', action='store_true', help='Generate derived index for the packaged files, then verify.')
    args = parser.parse_args()
    if args.write_checksums:
        files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
        with (ROOT / 'SHA256SUMS').open('w', encoding='utf-8', newline='\n') as stream:
            stream.writelines(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in files)
    print(json.dumps(verify(), ensure_ascii=False))
