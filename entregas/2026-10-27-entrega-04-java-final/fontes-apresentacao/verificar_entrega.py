"""Verify this delivery without launching experiments or editing historical files."""
import argparse
import hashlib
import json
import re
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
    revision = json.loads((ROOT / 'evidencias/revisao-resumo.json').read_text(encoding='utf-8'))
    require(revision['base_pdf_sha256'] == scientific['pdf_sha256'], 'PDF revision lost scientific provenance')
    require(sha(ROOT / 'TCC-Entrega04-final.pdf') == revision['pdf_sha256'] == sha(REPO / 'output/pdf/TCC-2026-final.pdf'), 'PDF differs from reviewed abstract revision')
    require(revision['changed_pdf_pages'] == [4] and revision['pdf_pages'] == scientific['pdf_pages'] == 80,
            'abstract revision changed expected pagination')
    require(revision['other_pdf_pages_text_unchanged'] and revision['results_and_classifications_unchanged'],
            'abstract revision must preserve results and other page texts')
    require(set(revision['source_sha256']) == {'projeto-latex-java/Configuracoes/dados_documento.tex'},
            'unexpected abstract revision source scope')
    for name, digest in revision['source_sha256'].items():
        require(sha(REPO / name) == digest, 'abstract source differs from reviewed revision')
    require(sha(ROOT / 'evidencias/catalogo-campanha.json') == scientific['catalog_sha256'] == sha(REPORT / 'resultados-a1/catalog.json'), 'catalog copy differs')
    require(sha(ROOT / 'evidencias/validacao-cientifica.json') == sha(REPORT / 'VALIDACAO-FINAL.json'), 'scientific validation copy differs')
    deck_revision = json.loads((ROOT / 'evidencias/revisao-apresentacao.json').read_text(encoding='utf-8'))
    require(deck_revision['base_pptx_sha256'] == '43e8b0ea342d3f550c16465d0020f4a68380e5c296e68abb5e95fc0a1d64e247',
            'presentation revision lost original provenance')
    require(sha(ROOT / 'Apresentacao-Entrega04-final.pptx') == deck_revision['pptx_sha256'], 'PPTX differs from visually reviewed revision')
    require(deck_revision['pdf_unchanged_sha256'] == revision['pdf_sha256'], 'presentation revision changed PDF provenance')
    require(deck_revision['changed_slides'] == [6, 8] and deck_revision['changed_speaker_notes'] == [1, 6, 8]
            and deck_revision['slide_count'] == 10 and deck_revision['native_table_slides'] == [4, 5, 6, 7, 8, 9],
            'unexpected presentation revision scope')
    require(deck_revision['results_and_classifications_unchanged'] and deck_revision['other_eight_slide_renders_unchanged'],
            'presentation revision must preserve results and unrelated slide renders')
    require(set(deck_revision['source_sha256']) == {'fontes-apresentacao/build.mjs', 'fontes-apresentacao/explicacao-parcial.mjs',
                                                   'fontes-apresentacao/revisar_parcial.mjs'}, 'unexpected presentation revision sources')
    for name, digest in deck_revision['source_sha256'].items():
        require(sha(ROOT / name) == digest, 'presentation source differs from reviewed revision')
    with ZipFile(ROOT / 'Apresentacao-Entrega04-final.pptx') as archive:
        require(archive.testzip() is None, 'invalid PPTX archive')
        owners = []
        texts = []
        speaker_notes = []
        for number in range(1, 11):
            xml = ET.fromstring(archive.read(f'ppt/slides/slide{number}.xml'))
            if xml.findall('.//a:tbl', NS): owners.append(number)
            texts.append(' '.join(node.text or '' for node in xml.findall('.//a:t', NS)))
            note = ET.fromstring(archive.read(f'ppt/notesSlides/notesSlide{number}.xml'))
            speaker_notes.append(' '.join(node.text or '' for node in note.findall('.//a:t', NS)))
            require(len(speaker_notes[-1]) > 100, 'speaker notes absent')
        require(owners == [4, 5, 6, 7, 8, 9], 'editable table owners changed')
        size = ET.fromstring(archive.read('ppt/presentation.xml')).find('p:sldSz', NS)
        require(size.attrib['cx'] == '12192000' and size.attrib['cy'] == '6858000', 'slide size changed')
        require('4,34' in texts[3] and '2,60' in texts[3] and '3,92' in texts[3] and '5,83' in texts[3], 'latency table differs')
        require('8.352' in texts[5] and '10.790' in texts[5] and '14' in texts[5] and '2.452' in texts[5], 'destination table differs')
        require('Evento no banco apesar de HTTP 503' in texts[7] and 'Horário de um commit ausente' in texts[7]
                and '4 pares completos' in texts[7] and '1 de 1.667' in texts[7], 'clear partial evidence explanation absent')
        require('A parada do banco era planejada.' in texts[7] and 'falta do horário de commit foi imprevista' in texts[7],
                'planned outage and missing timing must remain distinct')
        require(all(phrase in speaker_notes[7] for phrase in ['limitação não planejada da medição',
                'O 503 continua contado como erro HTTP.', 'quatro pares completos', 'Não estimamos o horário ausente.']),
                'partial evidence explanation missing from speaker notes')
        require('1 de 5' in texts[8] and '38,71' in texts[8] and 'DLQ' in texts[8], 'recovery caveat absent')
        guide = (ROOT / 'ROTEIRO-APRESENTACAO.md').read_text(encoding='utf-8')
        sections = re.split(r'^## Slide \d+ \(\d+ s\)\n\n', guide, flags=re.MULTILINE)[1:]
        require(len(sections) == 10 and all(section.strip() == note.strip() for section, note in zip(sections, speaker_notes)),
                'written guide differs from embedded speaker notes')
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
            'pdf_identical_to_reviewed_abstract_revision': True,
            'presentation_partial_explanation_verified': True,
            'original_scientific_validation_preserved': True, 'campaign': {'complete': 64, 'partial': 1},
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
