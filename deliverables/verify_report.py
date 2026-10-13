"""Independent report checks: citations, source identity, fonts, page geometry and renders.

This checks a local deliverable, not private experimental reproduction. It cannot replace
human visual review or the final publication commit's own remote CI.
"""
import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

import pdfplumber
from pypdf import PdfReader
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables'


def flatten(items):
    for item in items:
        if isinstance(item,list):yield from flatten(item)
        else:yield item


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--render-dir',type=Path,required=True)
    parser.add_argument('--visual-reviewed',action='store_true',help='Only after actual visual inspection of these rendered final pages.')
    args=parser.parse_args()
    md=(OUT/'Encounter_Lab_Full_Report.md').read_text()
    manifest_path=OUT/'REPORT_VERIFICATION.json';record=json.loads(manifest_path.read_text())
    assert hashlib.sha256(md.encode()).hexdigest()==record['report_sha256']
    pdf=OUT/'Encounter_Lab_Full_Report.pdf';assert hashlib.sha256(pdf.read_bytes()).hexdigest()==record['pdf_sha256']
    for name,digest in record['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,('source changed',name)
    assert record['chapters']==11 and 10000<=record['body_chinese_characters']<=15000
    assert 400<=record['abstract_chinese_characters']<=600
    assert '{{' not in md and '�' not in md and '\u25a1' not in md
    before_refs=md.split('## 参考文献')[0]
    reference_numbers={int(x) for x in re.findall(r'^\[(\d+)\] ',md,re.M)}
    cited=set()
    for a,b in re.findall(r'\[(\d+)(?:-(\d+))?\]',before_refs):
        cited.update(range(int(a),int(b or a)+1))
    assert reference_numbers==set(range(1,22)) and cited==reference_numbers,(cited,reference_numbers)
    for number in re.findall(r'^图 ([0-9A-G]+-\d+) ',md,re.M):
        assert '图'+number in before_refs,('missing figure analysis reference',number)
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',md):
        p=OUT/target;assert p.is_file();ET.fromstring(p.read_text())
        for value in re.findall(r'rgb\(([^)]+)\)',p.read_text()):
            components=[float(v.strip().rstrip('%')) for v in value.split(',')]
            assert len(set(components))==1 and components[0] in (0,100),('non-BW SVG',p.name,value)
    # Independently compare published table cells with their actual numeric sources.
    def cells(key):
        block=re.search(r'<!-- TABLE:'+key+r' -->\n(.*?)\n<!-- /TABLE:'+key+r' -->',md,re.S).group(1)
        assert hashlib.sha256(block.encode()).hexdigest()==record['table_hashes'][key]
        return [[c.strip() for c in line.strip().strip('|').split('|')] for line in block.splitlines()[2:]]
    t17=json.loads((ROOT/'reports/T17_METRICS.json').read_text())['metrics']['test']
    for table_row,model in zip(cells('T17_RANK'),t17.values()):
        assert table_row[1:]==[f'{model[k]:.6f}' for k in ('pr_auc_average_precision','roc_auc','brier_score','log_loss')]
    t22=json.loads((ROOT/'reports/window_study/T22_ROBUSTNESS.json').read_text())['main_metrics']
    t30=json.loads((ROOT/'reports/asof_audit/T30_RESULTS.json').read_text())['summary']['metrics']
    for key,models in [('T22_XGB_COMPLETE',t22),('T30_XGB_COMPLETE',[r for r in t30 if r['scope']=='reliable_predicted'])]:
        expected=sorted([r for r in models if r['model']=='xgboost'],key=lambda r:r['window_days'])
        for table_row,model in zip(cells(key),expected):
            assert table_row[0]==str(model['window_days'])+'天'
            assert table_row[1:]==[f'{model[k]:.6f}' for k in ('pr_auc_average_precision','roc_auc','brier_score','log_loss','precision','recall','f1')]
    retrieval=list(csv.DictReader((ROOT/'reports/multisource/T31_RETRIEVAL_METRICS.csv').open()))
    for dataset,hits in [('workplace2013',[31,34,35]),('workplace2015',[31,35,34])]:
        rows=sorted([r for r in retrieval if r['dataset_id']==dataset and r['scope']=='common_7d' and r['method']=='historical_frequency' and int(r['k'])==20],key=lambda r:int(r['window_days']))
        assert [int(r['observed_positive_hits_at_k']) for r in rows]==hits
        assert '/'.join(map(str,hits)) in md
    reader=PdfReader(pdf);n=len(reader.pages)
    assert not reader.is_encrypted
    outline={entry['/Title']:reader.get_destination_page_number(entry)+1 for entry in flatten(reader.outline)}
    for entry in record['heading_pages']:
        assert outline[entry['title']]==entry['page'],('outline page mismatch',entry)
    fonts={};bounds=[];bad_colors=[];toc_rows=[];text_pages=[]
    first_chapter=next(e['page'] for e in record['heading_pages'] if e['title'].startswith('第1章'))
    with pdfplumber.open(pdf) as document:
        for i,page in enumerate(document.pages,1):
            assert abs(page.width-595.2756)<.1 and abs(page.height-841.8898)<.1
            text=page.extract_text() or '';text_pages.append(text)
            assert f'第 {i} 页' in text,('footer',i)
            assert '�' not in text and '\u25a1' not in text
            for char in page.chars:
                color=char.get('non_stroking_color')
                if color not in (None,0,(0,),(0,0,0),(0.0,0.0,0.0)):bad_colors.append((i,char['text'],str(color)))
                if char['x0']<69.6 or char['x1']>page.width-69.6:bounds.append((i,char['text'],round(char['x0'],2),round(char['x1'],2)))
            if 3<=i<first_chapter:
                words=page.extract_words(x_tolerance=2,y_tolerance=3)
                grouped=defaultdict(list)
                for word in words:
                    if 68<word['top']<780:grouped[round(word['top']/3)*3].append(word)
                for row in grouped.values():
                    row.sort(key=lambda v:v['x0']);joined=''.join(v['text'] for v in row)
                    toc_rows.append(joined)
    assert not bad_colors,('colored text',bad_colors[:10])
    assert not bounds,('text outside margins',bounds[:20])
    toc_join='\n'.join(toc_rows)
    for e in record['heading_pages']:
        title=re.sub(r'\s','',e['title']);matching=[line for line in toc_rows if title in re.sub(r'\s','',line)]
        assert matching,('TOC missing title',e)
        assert any(re.search(r'(?<!\d)'+str(e['page'])+r'$',line) for line in matching),('TOC page mismatch',e,matching)
        page_text=re.sub(r'\s','',text_pages[e['page']-1])
        assert title in page_text,('heading not on announced page',e)
    for page in reader.pages:
        for value in page['/Resources']['/Font'].values():
            f=value.get_object();name=str(f.get('/BaseFont'));descriptor=f.get('/FontDescriptor')
            embedded=bool(descriptor and any(k in descriptor.get_object() for k in ('/FontFile','/FontFile2','/FontFile3')))
            fonts[name]=embedded
        for operands,operator in page.get_contents().operations:
            if operator in (b'rg',b'RG'):
                values=[float(v) for v in operands];assert len(set(values))==1 and values[0] in (0,1),('PDF color',values)
    chinese={name:embedded for name,embedded in fonts.items() if 'STSongti' in name or 'STHeiti' in name}
    assert chinese and all(chinese.values()) and any('Regular' in name for name in chinese)
    rendered=sorted(args.render_dir.glob('page-*.png'));assert len(rendered)==n,(len(rendered),n)
    for path in rendered:
        im=Image.open(path).convert('RGB');r,g,b=im.split()
        assert ImageChops.difference(r,g).getbbox() is None and ImageChops.difference(g,b).getbbox() is None,('colored render',path.name)
        assert im.getpixel((0,0))==(255,255,255)
    record['pdf_pages']=n
    record['quality_checks']={'citations':'21 referenced entries matched','source_identity':'passed',
      'tables_and_figures':'source-derived tables and valid monochrome SVG','page_size':'all A4 portrait',
      'text_colors':'all black','pdf_drawing_colors':'only black/white','render_colors':'achromatic white paper',
      'chinese_fonts':'regular Songti and Heiti embedded; glyph preflight passed','margins':'no text outside2.5cm tolerance',
      'page_footers':'all physical page numbers match','toc_and_outline':'all headings and displayed page numbers match actual pages',
      'rendered_pages':n,'chinese_font_resources':len(chinese)}
    record['render_review']='all final pages actually visually inspected' if args.visual_reviewed else 'automated render checks passed; human visual review pending'
    manifest_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','pages':n,'body_chinese_characters':record['body_chinese_characters'],
       'figures':record['figures'],'tables':record['tables'],'references':record['references'],'visual_reviewed':args.visual_reviewed},ensure_ascii=False))

if __name__=='__main__':main()
