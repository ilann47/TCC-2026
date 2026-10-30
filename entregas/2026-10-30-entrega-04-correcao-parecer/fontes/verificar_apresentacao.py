"""Read-only checks for the published presentation and its scientific sources."""
import hashlib
import io
import json
import posixpath
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PUBLIC = REPO / 'implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/resultados-a1'
NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compact(value):
    return ' '.join(value.split())


def all_text(element):
    return compact(' '.join(element.itertext()))


def verify():
    deck = ROOT / 'Apresentacao-Entrega04-correcoes.pptx'
    require(sha(deck) == 'a03b9ab96dc2b44b108fcad8f1037868a34378160ae35dd436a80240719f4916', 'published presentation differs')
    require(sha(REPO / 'entregas/2026-10-27-entrega-04-java-final/Apresentacao-Entrega04-final.pptx') == '71be8450168428ef77c447068c0b22e21bd51eeaec329194b0a96aefcbe77f33', 'historical presentation changed')
    require(sha(ROOT / 'TCC-Entrega04-correcoes.pdf') == 'ba2ff74ba5e2f85b1662b85c26723b539b99f027a9d0da6d3b16efbe64273463', 'reviewed TCC changed')
    groups = json.loads((PUBLIC / 'group-summary.json').read_text(encoding='utf-8'))
    exploration = json.loads((ROOT / 'recuperacao-exploratoria.json').read_text(encoding='utf-8'))
    guide = (ROOT / 'ROTEIRO-APRESENTACAO.md').read_text(encoding='utf-8')
    guide_parts = re.split(r'## Slide (\d+)([^\n]*)\n\n', guide)[1:]
    require(len(guide_parts) == 17 * 3, 'speaker guide incomplete')
    times = []
    with ZipFile(deck) as package:
        require(package.testzip() is None, 'PPTX CRC error')
        slide_names = sorted((n for n in package.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)), key=lambda n: int(re.search(r'(\d+)\.xml', n)[1]))
        require(len(slide_names) == 17, 'expected 17 slides')
        presentation = ET.fromstring(package.read('ppt/presentation.xml'))
        size = presentation.find('p:sldSz', NS)
        require((size.get('cx'), size.get('cy')) == ('12192000', '6858000'), 'reference dimensions differ')
        slides = [ET.fromstring(package.read(n)) for n in slide_names]
        texts = [all_text(s) for s in slides]
        table_owners = [i + 1 for i, s in enumerate(slides) if s.findall('.//a:tbl', NS)]
        chart_owners = [i + 1 for i, s in enumerate(slides) if s.findall('.//c:chart', NS)]
        require(table_owners == [4, 5, 6, 7, 8, 9, 11, 12, 14], 'native table owners differ')
        require(chart_owners == [15, 16], 'native chart owners differ')
        fonts = {e.get('typeface') for s in slides for e in s.findall('.//a:latin', NS)}
        require(fonts == {'Arial'}, 'reference font differs')
        for i in range(1, 18):
            note = ET.fromstring(package.read(f'ppt/notesSlides/notesSlide{i}.xml'))
            number, heading, body = guide_parts[(i - 1) * 3:i * 3]
            require(int(number) == i, 'guide order differs')
            require(compact(body) in all_text(note), f'guide and notes differ on slide {i}')
            require('Fontes:' in body, f'missing source notes on slide {i}')
            if i <= 10:
                times.append(int(re.search(r'\((\d+) s\)', heading)[1]))
        require(sum(times) == 300 and 'não duração medida' in guide, 'suggested timing misrepresented')
        require('Profa. Dra. Alessandra Bussador' in texts[0], 'advisor differs')
        require('65 coletas em 13 condições' in texts[2], 'sampling description differs')
        for phrase in ['4 pares completos', 'Inválido, sem alteração', '1 de 1.667 registros', 'após 37 coletas, antes das 28 restantes', 'Sem estimar o instante ausente']:
            require(phrase in texts[7], 'partial evidence missing: ' + phrase)
        for phrase in ['original permanece em 1 de 5', 'observou 5 de 5', '14 eventos terminais continuam sem gravação']:
            require(phrase in texts[8], 'recovery distinction missing: ' + phrase)
        require('revisão pessoal integral do autor ainda está pendente' in texts[16], 'author review status differs')
        require('Não' in texts[11] and 'pós-hoc' in texts[11], 'exploratory label missing')
        rows = slides[11].findall('.//a:tbl/a:tr', NS)
        values = [[all_text(cell) for cell in row.findall('a:tc', NS)] for row in rows]
        expected = [
            [str(r['dlq_terminal']) for r in exploration['runs']],
            ['Sim' if r['original']['observed'] else 'Não' for r in exploration['runs']],
            ['Sim' if r['exploratory']['observed'] else 'Não' for r in exploration['runs']],
            [f"{r['exploratory']['timing']['confirmed_after_restore_s']:.2f}".replace('.', ',') for r in exploration['runs']],
        ]
        require([row[1:] for row in values[1:]] == expected, 'exploratory table differs from audited data')
        specifications = [(48, ['http_success_p95_ms', 'commit_p95_ms'], 2), (12, ['business_cpu_mean_percent'], 2), (12, ['business_memory_mean_mib'], 1)]
        charts = sorted(n for n in package.namelist() if re.fullmatch(r'ppt/slides/charts/chart\d+\.xml', n))
        require(len(charts) == 3, 'expected three native charts')
        for name, (rate, metrics, digits) in zip(charts, specifications):
            chart = ET.fromstring(package.read(name))
            series = chart.findall('.//c:barChart/c:ser', NS)
            actual = [[float(v.text) for v in s.findall('c:val/c:numRef/c:numCache/c:pt/c:v', NS)] for s in series]
            expected = [[round(next(g for g in groups if g['profile'] == 'steady' and g['rate'] == rate and g['variant'] == variant)['metrics'][metric]['mean'], digits) for metric in metrics] for variant in ['sync', 'async']]
            require(actual == expected, 'chart differs from run-level source: ' + name)
            rels_name = posixpath.join(posixpath.dirname(name), '_rels', posixpath.basename(name) + '.rels')
            relationships = ET.fromstring(package.read(rels_name))
            target = next(r for r in relationships if r.get('Type', '').endswith('/package'))
            require(target.get('TargetMode') != 'External', 'external workbook not allowed')
            workbook_name = posixpath.normpath(posixpath.join(posixpath.dirname(name), target.get('Target')))
            with ZipFile(io.BytesIO(package.read(workbook_name))) as workbook:
                numeric = []
                for sheet in (n for n in workbook.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n)):
                    for cell in ET.fromstring(workbook.read(sheet)).findall('.//s:c', NS):
                        value = cell.find('s:v', NS)
                        if cell.get('t', 'n') == 'n' and value is not None:
                            numeric.append(float(value.text))
                require(sorted(numeric) == sorted(v for row in actual for v in row), 'editable workbook differs from chart cache')
    return dict(slides=17,main=10,support=7,suggested_seconds=300,native_table_slides=table_owners,native_charts=3,notes=17,scientific_sources_unchanged=True,author_personal_review_pending=True)


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False))
