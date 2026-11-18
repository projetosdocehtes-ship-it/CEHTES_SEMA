"""Atualiza o conteúdo de consulta e o download a partir do POP revisado."""
import json
import shutil
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

root = Path(__file__).resolve().parents[2]
source = Path(__file__).with_name('POP_SIM_001_FV_BESS.docx')
public = root / 'frontend/public/documentos'
data = root / 'frontend/src/data'
public.mkdir(parents=True, exist_ok=True)
data.mkdir(parents=True, exist_ok=True)
doc = Document(source)
blocks = []
for element in doc.element.body:
    if element.tag.endswith('}tbl'):
        table = Table(element, doc)
        blocks.append({'type': 'table', 'rows': [[cell.text for cell in row.cells] for row in table.rows]})
    elif element.tag.endswith('}p'):
        para = Paragraph(element, doc)
        if para.text.strip():
            blocks.append({'type': 'text', 'style': para.style.name,
                           'runs': [{'text': run.text, 'bold': bool(run.bold)} for run in para.runs]})
        if element.xpath('.//w:drawing'):
            blocks.append({'type': 'image', 'src': 'equipamentos-partida.png', 'alt': 'Resultado de referência com pré-carga e atendimento da carga de 120 kW'})
(data / 'pop.json').write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding='utf-8')
shutil.copy2(source, public / source.name)
shutil.copy2(root / 'equipamentos-partida.png', public / 'equipamentos-partida.png')
print(f'POP publicado: {len(blocks)} blocos')
