"""Read public frozen aggregates and typeset the report; never fit or read private samples.

Requires a separate document environment with reportlab, pypdf, pdfplumber and Pillow.
No project dependency or scientific code is modified. PDF stays local; SVG/Markdown are text.
"""
import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Rect, Line, Polygon, Circle, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether, CondPageBreak
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'
FIGDIR = OUT / 'Encounter_Lab_Report_Figures'
MD = OUT / 'Encounter_Lab_Full_Report.md'
BASELINE = '478a320c0a8146cf8dfdcbb8c0d93b16640b8594'
SOURCES = [
 'reports/T17_METRICS.json', 'reports/T17_SAFE_METADATA.json', 'reports/T17_REAL_EXPERIMENT.md', 'reports/T17_DATA_DIAGNOSTICS.md',
 'reports/window_study/T19_COHORT_AUDIT.md', 'reports/window_study/T19_COHORT_MANIFEST.json', 'reports/window_study/T20_FEATURE_AUDIT.md',
 'reports/window_study/T22_ROBUSTNESS.json', 'reports/window_study/T22_METRICS.csv', 'reports/window_study/T22_WINDOW_COMPARISON.md',
 'reports/asof_audit/T30_RESULTS.json', 'reports/asof_audit/T30_METRICS.csv', 'reports/asof_audit/T30_SELECTION_BIAS.csv',
 'reports/multisource/T31_SOURCE_SUMMARY.json', 'reports/multisource/T31_RETRIEVAL_METRICS.csv',
 'reports/performance/T32_BENCHMARK.csv', 'reports/performance/T32_PARITY.json',
 'ASOF_INFERENCE.md', 'ASOF_AUDIT.md', 'MULTISOURCE_STUDY.md', 'PERFORMANCE_AUDIT.md', 'FINAL_RESEARCH_AUDIT.md',
 'PRODUCT_DELIVERY.md', 'PRODUCT_PLAN.md', 'EXPLORE_GUIDE.md', 'REPRODUCIBILITY.md', 'FINAL_RELEASE_CHECKLIST.md',
 'CI_VERIFICATION.md', 'DEVELOPMENT_HISTORY.md', 'PORTFOLIO_GUIDE.md', 'README.md', 'PROJECT_SPEC.md',
 'src/label_builder.py', 'src/window_cohort.py', 'src/window_features.py', 'src/feature_engineering.py',
 'src/temporal_split.py', 'src/baselines.py', 'src/model_registry.py', 'src/train.py', 'src/calibration.py',
 'src/window_study.py', 'src/evaluate.py', 'src/asof_inference.py', 'src/time_machine.py',
 'src/network.py', 'src/positive_retrieval.py', 'src/multisource_exploration.py', 'src/encounter_graph.py',
 'src/chance_encounter.py', 'src/chance_encounter_ui.py', 'src/encounter_insights.py', 'src/welcome.py',
 'src/snapshot_manager.py', 'src/safe_cache.py', 'src/preprocessing.py', 'src/loader.py', 'src/dataset_catalog.py',
 'src/ui.py', 'app.py', '.github/workflows/ci.yml', 'tools/check_repository_safety.py',
 'tests/test_asof_inference.py', 'tests/test_time_machine_coverage.py', 'tests/test_product_navigation.py',
 'tests/test_product_experience.py', 'tests/test_repository_safety.py', 'tests/test_final_audit.py',
]
NAMES = {'constant':'常数概率','historical_frequency':'历史频率','logistic_regression':'逻辑回归',
         'xgboost_raw':'XGBoost原始','xgboost_sigmoid':'XGBoost校准','xgboost':'XGBoost'}


def read_json(name): return json.loads((ROOT / name).read_text())
def read_csv(name): return list(csv.DictReader((ROOT / name).open()))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] + ['| '+' | '.join(map(str,row))+' |' for row in rows])
def f6(value): return f'{float(value):.6f}'


def aggregates():
    t17 = read_json(SOURCES[0])['metrics']['test']
    meta = read_json(SOURCES[1])
    t22 = read_json('reports/window_study/T22_ROBUSTNESS.json')['main_metrics']
    csv22 = read_csv('reports/window_study/T22_METRICS.csv')
    for row in t22:
        other = next(r for r in csv22 if int(r['window_days'])==row['window_days'] and r['model']==row['model'])
        for key in ('pr_auc_average_precision','roc_auc','brier_score','log_loss','precision','recall','f1','positive_rate'):
            assert abs(float(other[key])-row[key]) < 1e-12, ('T22 CSV parity',key)
        assert int(other['rows'])==row['rows']==25569
    t30 = read_json('reports/asof_audit/T30_RESULTS.json')['summary']['metrics']
    t30 = [r for r in t30 if r['scope']=='reliable_predicted']
    csv30 = read_csv('reports/asof_audit/T30_METRICS.csv')
    for row in t30:
        other=next(r for r in csv30 if r['scope']==row['scope'] and r['model']==row['model'] and int(r['window_days'])==row['window_days'])
        for key in ('pr_auc_average_precision','roc_auc','brier_score','log_loss','precision','recall','f1'):
            assert abs(float(other[key])-row[key])<1e-12
        assert row['rows']==27802
    source = read_json('reports/multisource/T31_SOURCE_SUMMARY.json')
    perf = read_csv('reports/performance/T32_BENCHMARK.csv')
    for row in perf:
        assert int(row['repeat_count'])==5 and row['parity_status']=='passed'
        before,after=float(row['before_median_seconds']),float(row['after_median_seconds'])
        assert abs((1-after/before)*100-float(row['duration_reduction_pct']))<1e-9
    return t17,meta,t22,t30,source,perf


def fill_tables(text, data):
    t17,meta,t22,t30,source,perf=data
    c=next(d for d in meta['datasets'] if d['dataset']=='Copenhagen')
    source_rows=[['Copenhagen',f"{c['participants_with_valid_contacts']}（接触）",f"{c['valid_contact_records']:,}",f"{c['full_period_observed_pairs_descriptive_only']:,}",f"{c['span_days']:.3f}天",'覆盖策略下二分类']]
    labels={'workplace2013':'Workplace2013','workplace2015':'Workplace2015','highschool2013':'High School2013','reality_mining_mendeley':'MIT处理档案','social_evolution':'Social Evolution'}
    for s in source['sources']:
        source_rows.append([labels[s['dataset_id']], s.get('participants') or '未取得',
             f"{s['unique_contact_records']:,}" if s.get('unique_contact_records') is not None else '未取得',
             f"{s['valid_pairs']:,}" if s.get('valid_pairs') is not None else '未取得',
             f"{s['span_days']:.3f}天" if s.get('span_days') is not None else '单位/来源未核实',
             '描述与正检索' if s['dataset_id'] in ('workplace2013','workplace2015','highschool2013') else '仅拓扑' if s['dataset_id']=='reality_mining_mendeley' else '不可用'])
    split_rows=[]
    for kind,ch in [('train','训练'),('validation','验证'),('test','测试')]:
        row=meta['split'][kind];split_rows.append(['T17',ch,f"{row['samples']:,}",row['positive'],row['negative'],row['snapshot_times']])
    # T19's published audit is the authority for split support; assert exact saved wording.
    audit=(ROOT/'reports/window_study/T19_COHORT_AUDIT.md').read_text()
    assert all(s in audit for s in ('54,677','14,816','25,569','5,423'))
    cohort=read_json('reports/window_study/T19_COHORT_MANIFEST.json')['support']['sets']
    for key,label in (('train','训练'),('validation','验证'),('test','测试')):
        row=cohort[key];split_rows.append(['T22',label,f"{row['rows']:,}",f"{row['positive']:,}",f"{row['negative']:,}",row['distinct_prediction_days']])
    def complete(rows):
        return [[str(r['window_days'])+'天']+[f6(r[k]) for k in ('pr_auc_average_precision','roc_auc','brier_score','log_loss','precision','recall','f1')] for r in sorted(rows,key=lambda r:r['window_days']) if r['model']=='xgboost']
    # Cross-check all displayed population counts in the audited public selection CSV.
    selection=read_csv('reports/asof_audit/T30_SELECTION_BIAS.csv')
    by_population={r['population']:r for r in selection}
    assert set(by_population) >= {'all_asof','old_t22','added_asof'}
    populations=[]
    for key,label in (('all_asof','全部候选'),('old_t22','旧T22'),('added_asof','新增候选')):
        row=by_population[key];populations.append([label]+[f"{int(row[k]):,}" for k in ('rows','positive','negative','unknown')])
    summary=read_json('reports/asof_audit/T30_RESULTS.json')['summary']
    allrow=by_population['all_asof']
    populations.append(['可揭晓',f"{summary['reliable_labels']:,}",f"{int(allrow['positive']):,}",f"{int(allrow['negative']):,}",'0'])
    common=t30[0];n=common['rows'];positive=round(n*common['positive_rate'])
    populations.append(['可预测且可揭晓',f'{n:,}',f'{positive:,}',f'{n-positive:,}','0'])
    perf_rows=[]
    for op in ('features','predict_models'):
        for mode in ('cold','warm'):
            r=next(r for r in perf if r['operation']==op and r['cache_mode']==mode)
            perf_rows.append(['多窗口特征' if op=='features' else '保存模型预测','冷' if mode=='cold' else '暖',f6(r['before_median_seconds']),f6(r['after_median_seconds']),f"{float(r['duration_reduction_pct']):+.3f}%（耗时减少）"])
    blocks={
      'SOURCE_TABLE':table(['来源','参与者','规范接触记录','唯一配对','时间跨度','适用性'],source_rows),
      'SPLIT_TABLE':table(['实验','集合','样本数','正例','负例','时点数'],split_rows),
      'T17_RANK':table(['模型','AP','ROC-AUC','Brier','Log Loss'],[[NAMES[k]]+[f6(v[m]) for m in ('pr_auc_average_precision','roc_auc','brier_score','log_loss')] for k,v in t17.items()]),
      'T17_CLASSIFY':table(['模型','验证阈值','Precision','Recall','F1'],[[NAMES[k]]+[f6(v[m]) for m in ('threshold','precision','recall','f1')] for k,v in t17.items()]),
      'T22_METRICS':table(['窗口','模型','AP','ROC-AUC','Brier','Log Loss','F1'],[[str(r['window_days'])+'天',NAMES[r['model']]]+[f6(r[k]) for k in ('pr_auc_average_precision','roc_auc','brier_score','log_loss','f1')] for r in t22]),
      'T30_POPULATIONS':table(['范围','样本','正例','负例','Unknown'],populations),
      'PERFORMANCE_TABLE':table(['操作','模式','优化前秒','优化后秒','同模式变化'],perf_rows),
      'T22_XGB_COMPLETE':table(['窗口','AP','ROC-AUC','Brier','Log Loss','Precision','Recall','F1'],complete(t22)),
      'T30_XGB_COMPLETE':table(['窗口','AP','ROC-AUC','Brier','Log Loss','Precision','Recall','F1'],complete(t30)),
    }
    for key,value in blocks.items():
        block='<!-- TABLE:'+key+' -->\n'+value+'\n<!-- /TABLE:'+key+' -->'
        placeholder='{{'+key+'}}'
        if placeholder in text:text=text.replace(placeholder,block)
        else:
            pattern=r'<!-- TABLE:'+key+r' -->.*?<!-- /TABLE:'+key+r' -->'
            assert re.search(pattern,text,re.S),key
            text=re.sub(pattern,lambda _:block,text,flags=re.S)
    assert not re.search(r'\{\{[A-Z_]+\}\}',text)
    return text, blocks


BLACK,WHITE=colors.black,colors.white

def label(d,x,y,text,size=10,anchor='middle',font='ReportSong'):
    for i,line in enumerate(text.split('\n')):
        d.add(String(x,y-i*(size+4),line,fontName=font,fontSize=size,fillColor=BLACK,textAnchor=anchor))

def box(d,x,y,w,h,text,size=10):
    d.add(Rect(x,y,w,h,fillColor=WHITE,strokeColor=BLACK,strokeWidth=.8))
    label(d,x+w/2,y+h/2+(len(text.split('\n'))-1)*(size+4)/2-3,text,size)

def arrow(d,x1,y1,x2,y2,dashed=False):
    d.add(Line(x1,y1,x2,y2,strokeColor=BLACK,strokeWidth=.8,strokeDashArray=[3,2] if dashed else None))
    import math
    a=math.atan2(y2-y1,x2-x1);s=5
    d.add(Polygon([x2,y2,x2-s*math.cos(a-.5),y2-s*math.sin(a-.5),x2-s*math.cos(a+.5),y2-s*math.sin(a+.5)],fillColor=BLACK,strokeColor=BLACK))

def hatch(d,x,y,w,h,step=6):
    for start in range(-int(h),int(w)+1,step):
        a=max(0,-start);b=min(h,w-start)
        if b>a:d.add(Line(x+start+a,y+a,x+start+b,y+b,strokeColor=BLACK,strokeWidth=.45))


def figures(data):
    t17,meta,t22,t30,source,perf=data
    fig={}
    d=Drawing(450,205)
    for x,txt in [(0,'来源核验\n字段、时间、许可'),(155,'规范数据\n接触与观测分离'),(310,'离线研究\n标签、特征、训练')]:box(d,x,148,140,44,txt)
    arrow(d,140,170,155,170);arrow(d,295,170,310,170)
    box(d,155,70,140,45,'过去候选与有界特征\n核验模型信息截止')
    box(d,310,70,140,45,'历史预测 → 冻结\n独立未来揭晓')
    arrow(d,225,148,225,115);arrow(d,295,92,310,92);arrow(d,380,148,380,115)
    box(d,0,0,140,44,'Play会话规则\n不调用研究模型')
    box(d,155,0,140,44,'Explore\n个人线索与公开聚合')
    box(d,310,0,140,44,'Research界面\n原有科研工具')
    arrow(d,140,22,155,22);arrow(d,380,70,380,44)
    label(d,70,94,'独立娱乐通路',10)
    fig['figure_2_1']=d
    d=Drawing(450,170)
    box(d,0,112,128,40,'文件与签名校验\n合法来源、真实字段')
    box(d,160,112,130,40,'单位与ID规范化\n精确事件去重')
    box(d,322,112,128,40,'质量与适用性报告\n已知/未知分开')
    arrow(d,128,132,160,132);arrow(d,290,132,322,132)
    box(d,100,35,130,40,'接触记录\n时间、配对、信号')
    box(d,270,35,130,40,'扫描观测\n独立覆盖证据')
    arrow(d,205,112,165,75);arrow(d,245,112,335,75)
    label(d,225,8,'两类规范文件为不同服务提供输入，不以无接触替代在线证据',9)
    fig['figure_3_1']=d
    d=Drawing(450,160)
    arrow(d,20,82,430,82)
    for x,txt in [(35,'t-7d'),(135,'t-3d'),(235,'t-1d'),(320,'t'),(415,'t+24h')]:
        d.add(Line(x,70,x,95,strokeColor=BLACK));label(d,x,54,txt,10)
    for y,left,name in [(140,35,'7天'),(121,135,'3天'),(102,235,'1天')]:
        d.add(Line(left,y,318,y,strokeColor=BLACK,strokeWidth=1.2));label(d,left+5,y+3,name,9,'start')
    d.add(Line(320,25,320,150,strokeColor=BLACK,strokeDashArray=[3,3]))
    arrow(d,325,112,415,112);label(d,371,131,'未来标签',10)
    label(d,160,12,'输入：[t-w,t)，不读取t及以后',10);label(d,370,12,'标签：(t,t+24h]',9)
    fig['figure_4_1']=d
    d=Drawing(450,205)
    x0,w0,y0=120,280,30
    for i,(k,row) in enumerate(reversed(list(t17.items()))):
        y=y0+i*31;v=row['pr_auc_average_precision'];w=w0*v/.5
        label(d,111,y+7,NAMES[k],10,'end');d.add(Rect(x0,y,w,19,fillColor=WHITE,strokeColor=BLACK));hatch(d,x0,y,w,19,6+i)
        label(d,x0+w+5,y+6,f6(v),9,'start')
    for v in (0,.1,.2,.3,.4,.5):
        x=x0+w0*v/.5;d.add(Line(x,23,x,27,strokeColor=BLACK));label(d,x,9,f'{v:.1f}',9)
    label(d,270,190,'T17：同一260,170条测试样本',10)
    fig['figure_6_1']=d
    d=Drawing(450,225);x0,y0,w,h=48,42,365,160
    d.add(Line(x0,y0,x0,y0+h,strokeColor=BLACK));d.add(Line(x0,y0,x0+w,y0,strokeColor=BLACK))
    for v in (0,.25,.5,.75,1):
        y=y0+h*v;d.add(Line(x0-3,y,x0,y,strokeColor=BLACK));label(d,x0-8,y-3,f'{v:.2f}',9,'end')
    rows=[r for r in t22 if r['model']=='xgboost']
    for i,r in enumerate(rows):
        x=83+i*122;bh=h*r['pr_auc_average_precision'];d.add(Rect(x,y0,65,bh,fillColor=WHITE,strokeColor=BLACK));hatch(d,x,y0,65,bh,7+i*2)
        label(d,x+32.5,y0+bh+8,f6(r['pr_auc_average_precision']),10)
        label(d,x+32.5,23,str(r['window_days'])+'天历史',10)
    label(d,25,212,'AP',10);label(d,245,5,'同一25,569样本；4个主测试日',9)
    fig['figure_6_2']=d
    d=Drawing(450,180);x0,w=105,310
    populations=[]
    selection={r['population']:r for r in read_csv('reports/asof_audit/T30_SELECTION_BIAS.csv')}
    for key,name in (('old_t22','旧T22'),('added_asof','新增候选'),('all_asof','全部候选')):
        row=selection[key];populations.append((name,*[int(row[k]) for k in ('positive','negative','unknown')]))
    for i,(name,pos,neg,unk) in enumerate(populations):
        y=120-i*39;left=x0;label(d,97,y+8,name,10,'end')
        for value,kind in [(pos,'pos'),(neg,'neg'),(unk,'unk')]:
            width=w*value/38005
            if width:
                d.add(Rect(left,y,width,22,fillColor=BLACK if kind=='pos' else WHITE,strokeColor=BLACK))
                if kind=='unk':hatch(d,left,y,width,22)
            left+=width
        label(d,left+5,y+7,str(pos+neg+unk),9,'start')
    for x,kind,txt in [(110,'pos','已知正例'),(215,'neg','已知负例'),(320,'unk','Unknown')]:
        d.add(Rect(x,10,18,12,fillColor=BLACK if kind=='pos' else WHITE,strokeColor=BLACK))
        if kind=='unk':hatch(d,x,10,18,12)
        label(d,x+23,11,txt,9,'start')
    label(d,225,164,'标签可见性比较（计数尺度相同）',10)
    fig['figure_6_3']=d
    network=next(n for n in source['networks'] if n['dataset_id']=='workplace2013')
    activity=network['activity'];assert sum(a['records'] for a in activity)==9827
    d=Drawing(450,225);x0,y0,w,h=50,45,370,150
    d.add(Line(x0,y0,x0,y0+h,strokeColor=BLACK));d.add(Line(x0,y0,x0+w,y0,strokeColor=BLACK))
    for value in (0,500,1000,1500):
        yy=y0+h*value/1500;d.add(Line(x0-3,yy,x0,yy,strokeColor=BLACK));label(d,x0-7,yy-3,str(value),9,'end')
    previous=None
    for a in activity:
        x=x0+(a['study_day']-1)*w/11;y=y0+a['records']*h/1500
        if previous:d.add(Line(*previous,x,y,strokeColor=BLACK,strokeWidth=1))
        d.add(Circle(x,y,2.2,strokeColor=BLACK,fillColor=WHITE));label(d,x,25,str(a['study_day']),9)
        previous=(x,y)
    label(d,225,207,'Workplace2013：记录条数，不是见面次数',10)
    label(d,235,6,'相对研究日；零仅表示无记录',9)
    fig['figure_7_1']=d
    d=Drawing(450,175)
    label(d,108,155,'历史接触语义',11);label(d,338,155,'自填线索语义',11)
    for x,txt in [(45,'v1'),(165,'v2')]:d.add(Circle(x,90,18,strokeColor=BLACK,fillColor=WHITE));label(d,x,87,txt,11)
    d.add(Line(63,90,147,90,strokeColor=BLACK));label(d,105,118,'窗口内接触证据',9)
    for x,txt in [(263,'A'),(413,'B')]:d.add(Circle(x,90,16,strokeColor=BLACK,fillColor=WHITE));label(d,x,87,txt,11)
    box(d,303,45,70,32,'距离线索',9);d.add(Line(278,83,303,61,strokeColor=BLACK));d.add(Line(398,83,373,61,strokeColor=BLACK))
    box(d,297,107,82,26,'自述汇总',9);d.add(Line(278,98,297,120,strokeColor=BLACK));d.add(Line(398,98,379,120,strokeColor=BLACK))
    label(d,225,10,'结构示意；符号不是研究参与者，边不是实际抽取记录',9)
    fig['figure_7_2']=d
    d=Drawing(450,165)
    box(d,170,117,110,35,'Home',12)
    for x,txt,detail in [(0,'Play','固定娱乐规则\n仅当前问卷'),(160,'Explore','个人线索\n独立公开聚合'),(320,'Research','离线模型与审计\n历史模拟工具')]:
        box(d,x,57,130,38,txt,11);box(d,x,0,130,43,detail,10);arrow(d,225,117,x+65,95);arrow(d,x+65,57,x+65,43)
    fig['figure_8_1']=d
    for name,drawing in fig.items():
        svg=renderSVG.drawToString(drawing)
        svg=svg.replace('font-family: ReportSong','font-family: Songti SC, SimSun, serif').replace('font-family: ReportHei','font-family: Heiti SC, SimHei, sans-serif')
        (FIGDIR/(name+'.svg')).write_text(svg)
    return fig


def inline(value):
    value=html.escape(value)
    value=re.sub(r'`([^`]+)`',r'\1',value)
    value=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',value)
    value=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:'<link href="'+m[2]+'" color="black">'+m[1]+'</link>',value)
    return value


class ReportDoc(BaseDocTemplate):
    def __init__(self,path,styles):
        self.styles=styles;self.heading_pages=[];self.element_bounds=[]
        super().__init__(str(path),pagesize=A4,leftMargin=2.5*cm,rightMargin=2.5*cm,topMargin=2.5*cm,bottomMargin=2.5*cm,
                         title='Encounter Lab：完整项目研究报告',author='Encounter Lab project documentation',allowSplitting=True)
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='body')
        self.addPageTemplates(PageTemplate(id='A4',frames=[frame],onPage=self.page))
    def page(self,canvas,doc):
        canvas.saveState();canvas.setFillColor(WHITE);canvas.rect(0,0,A4[0],A4[1],stroke=0,fill=1)
        canvas.setFillColor(BLACK);canvas.setStrokeColor(BLACK)
        if doc.page>1:
            canvas.setFont('ReportSong',9);canvas.drawString(self.leftMargin,A4[1]-self.topMargin+19,'Encounter Lab 项目研究报告')
            canvas.setLineWidth(.4);canvas.line(self.leftMargin,A4[1]-self.topMargin+12,A4[0]-self.rightMargin,A4[1]-self.topMargin+12)
        canvas.setFont('ReportSong',9);canvas.drawCentredString(A4[0]/2,35,'第 '+str(doc.page)+' 页');canvas.restoreState()
    def beforeDocument(self): self.heading_pages=[]
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and getattr(flowable,'toc_level',None) is not None:
            title=flowable.getPlainText();key='section-'+str(len(self.heading_pages))
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(title,key,flowable.toc_level,False)
            self.notify('TOCEntry',(flowable.toc_level,title,self.page,key))
            self.heading_pages.append({'level':flowable.toc_level,'title':title,'page':self.page})


def make_pdf(text,fig):
    body=ParagraphStyle('Body',fontName='ReportSong',fontSize=12,leading=18,textColor=BLACK,alignment=TA_JUSTIFY,
                        firstLineIndent=24,rightIndent=12,spaceAfter=3,wordWrap='CJK',allowWidows=0,allowOrphans=0)
    styles={'body':body,
      'plain':ParagraphStyle('Plain',parent=body,alignment=TA_LEFT,firstLineIndent=0),
      'h1':ParagraphStyle('Heading1',fontName='ReportHei',fontSize=16,leading=24,spaceAfter=10,keepWithNext=True,textColor=BLACK,wordWrap='CJK'),
      'h2':ParagraphStyle('Heading2',fontName='ReportHei',fontSize=14,leading=21,spaceBefore=8,spaceAfter=4,keepWithNext=True,textColor=BLACK,wordWrap='CJK'),
      'h3':ParagraphStyle('Heading3',fontName='ReportHei',fontSize=12,leading=18,spaceBefore=8,spaceAfter=5,keepWithNext=True,textColor=BLACK,wordWrap='CJK'),
      'caption':ParagraphStyle('Caption',fontName='ReportSong',fontSize=11,leading=16.5,spaceAfter=8,spaceBefore=5,alignment=TA_CENTER,textColor=BLACK,wordWrap='CJK'),
      'tablecaption':ParagraphStyle('TableCaption',fontName='ReportHei',fontSize=11,leading=16.5,spaceAfter=6,spaceBefore=8,alignment=TA_CENTER,keepWithNext=True,textColor=BLACK,wordWrap='CJK'),
      'table':ParagraphStyle('TableBody',fontName='ReportSong',fontSize=10,leading=15,textColor=BLACK,wordWrap='CJK',alignment=TA_LEFT),
      'reference':ParagraphStyle('Reference',parent=body,fontSize=10.5,leading=15.75,firstLineIndent=0,alignment=TA_LEFT,spaceAfter=8),
      'code':ParagraphStyle('Code',fontName='Courier',fontSize=9,leading=14,textColor=BLACK,wordWrap='CJK',spaceAfter=2),
      'cover':ParagraphStyle('Cover',fontName='ReportHei',fontSize=20,leading=31,alignment=TA_CENTER,textColor=BLACK,spaceAfter=26,wordWrap='CJK'),
      'covertext':ParagraphStyle('CoverText',fontName='ReportSong',fontSize=12,leading=21,alignment=TA_CENTER,textColor=BLACK,spaceAfter=12,wordWrap='CJK')}
    story=[Spacer(1,65),Paragraph('Encounter Lab：<br/>面向未来24小时接触事件预测的<br/>数据分析、机器学习建模与<br/>交互式可视化系统设计与实现',styles['cover']),
       Paragraph('Encounter Lab: Design and Implementation of a Data Analytics, Machine Learning and Interactive Visualization System for 24-Hour Contact Prediction',styles['covertext']),
       Spacer(1,42),Paragraph('完整项目研究报告',styles['covertext']),Paragraph('审阅与编制日期：2026年10月13日',styles['covertext']),
       Paragraph('研究与工程基准：research-v2.2 /478a320',styles['covertext']),Paragraph('涵盖T01-T34与P01-P03',styles['covertext']),
       Paragraph('依据公开源码、冻结聚合材料与实际CI记录编写',styles['covertext'])]
    lines=text.splitlines();i=next(i for i,line in enumerate(lines) if line=='## 中文摘要');refs=False
    while i<len(lines):
        line=lines[i].strip()
        if not line or line.startswith('<!--'):i+=1;continue
        if line.startswith('## '):
            title=line[3:]
            if (re.match(r'第\d+章',title) and not title.startswith('第1章')) or title.startswith('附录'):
                story.extend([CondPageBreak(215),Spacer(1,16)])
            else:story.append(PageBreak())
            p=Paragraph(inline(title),styles['h1'])
            if title!='目录':p.toc_level=0
            story.append(p);refs=title=='参考文献'
            if title=='目录':
                toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC0',fontName='ReportHei',fontSize=11,leading=18,spaceBefore=6,textColor=BLACK,wordWrap='CJK'),ParagraphStyle('TOC1',fontName='ReportSong',fontSize=10,leading=15,leftIndent=15,textColor=BLACK,wordWrap='CJK')]
                story.append(toc);i+=1
                while i<len(lines) and not lines[i].startswith('## '):i+=1
                continue
            i+=1;continue
        if line.startswith('### '):
            p=Paragraph(inline(line[4:]),styles['h2']);p.toc_level=1;story.append(p);i+=1;continue
        if line.startswith('#### '):story.append(Paragraph(inline(line[5:]),styles['h3']));i+=1;continue
        if line.startswith('!['):
            match=re.match(r'!\[([^]]+)\]\([^)]*/([^/]+)\.svg\)',line);assert match,line
            caption=match[1];drawing=fig[match[2]];story.append(KeepTogether([drawing,Paragraph(inline(caption),styles['caption'])]));i+=1
            while i<len(lines) and not lines[i].strip():i+=1
            if i<len(lines) and lines[i].strip().startswith('图 '):i+=1
            continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in cells):rows.append(cells)
                i+=1
            n=len(rows[0]);width=A4[0]-5*cm
            if n==3:weights=[.16,.37,.47]
            elif n==2:weights=[.26,.74]
            elif n==5:weights=[.28,.18,.18,.18,.18]
            elif n==6:weights=[.20,.14,.19,.14,.15,.18]
            elif n==7:weights=[.08,.19,.14,.145,.145,.15,.15]
            else:weights=[1/n]*n
            cellstyle=styles['table']
            if n>=7:cellstyle=ParagraphStyle('CompactTable',parent=cellstyle,fontSize=9,leading=13.5)
            cells=[[Paragraph(inline(c),cellstyle) for c in row] for row in rows]
            t=Table(cells,colWidths=[width*w/sum(weights) for w in weights],repeatRows=1,hAlign='CENTER')
            t.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),.8,BLACK),('LINEBELOW',(0,0),(-1,0),.6,BLACK),('LINEBELOW',(0,-1),(-1,-1),.8,BLACK),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,8)]);continue
        if line.startswith('```'):
            i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                story.append(Paragraph(html.escape(lines[i]),styles['code']));i+=1
            i+=1;story.append(Spacer(1,5));continue
        if re.match(r'^表 [0-9A-G]+-\d+ ',line):story.append(Paragraph(inline(line),styles['tablecaption']));i+=1;continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||!\[|<!--|```)',lines[i]):parts.append(lines[i].strip());i+=1
        paragraph=' '.join(parts)
        story.append(Paragraph(inline(paragraph),styles['reference'] if refs else styles['plain'] if paragraph.startswith('关键词') else styles['body']))
    doc=ReportDoc(OUT/'Encounter_Lab_Full_Report.pdf',styles);doc.multiBuild(story)
    return doc.heading_pages


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serif',default='/System/Library/Fonts/Supplemental/Songti.ttc')
    parser.add_argument('--sans',default='/System/Library/Fonts/STHeiti Medium.ttc')
    args=parser.parse_args()
    pdfmetrics.registerFont(TTFont('ReportSong',args.serif,subfontIndex=6))
    pdfmetrics.registerFont(TTFont('ReportHei',args.sans,subfontIndex=1))
    pdfmetrics.registerFontFamily('ReportSong',normal='ReportSong',bold='ReportHei',italic='ReportSong',boldItalic='ReportHei')
    FIGDIR.mkdir(parents=True,exist_ok=True)
    data=aggregates();text,blocks=fill_tables(MD.read_text(),data)
    if 'figure_3_1.svg' not in text:
        target='### 3.5 质量检查'
        addition='图3-1概括从来源校验到两类规范文件的预处理过程。接触与观测分别保存，使历史输入、未来标签与覆盖审查可以按各自边界读取，而不把无记录误作在线负例。\n\n![图 3-1 数据预处理与接触观测分离](Encounter_Lab_Report_Figures/figure_3_1.svg)\n\n图 3-1 数据预处理与接触观测分离\n\n'
        text=text.replace(target,addition+target)
    MD.write_text(text)
    # Fail rather than silently emit a missing Chinese or mathematical glyph.
    for name in ('ReportSong','ReportHei'):
        font=pdfmetrics.getFont(name)
        missing={ch for ch in text if ord(ch)>127 and ord(ch) not in font.face.charToGlyph}
        assert not missing,(name,sorted(missing))
    figs=figures(data);headings=make_pdf(text,figs)
    body=text[text.index('## 第1章'):text.index('## 参考文献')]
    body=re.sub(r'(?m)^!\[.*?\]\([^)]*\)\s*$', '', body)
    abstract=text.split('## 中文摘要',1)[1].split('关键词：',1)[0]
    result={'baseline':BASELINE,'date':'2026-10-13','scope':'public aggregates and reviewed source only; no fitting or raw reproduction',
      'source_sha256':{n:digest(ROOT/n) for n in SOURCES},'report_sha256':digest(MD),'pdf_sha256':digest(OUT/'Encounter_Lab_Full_Report.pdf'),
      'word_count_method':'Chinese Han characters in chapters1-11 including headings/tables/captions; image-alt duplication, abstract/references/appendices excluded',
      'body_chinese_characters':len(re.findall(r'[\u4e00-\u9fff]',body)), 'abstract_chinese_characters':len(re.findall(r'[\u4e00-\u9fff]',abstract)),
      'chapters':len(re.findall(r'^## 第\d+章',text,re.M)), 'figures':len(figs),'tables':len(re.findall(r'^表 [0-9A-G]+-\d+ ',text,re.M)),
      'references':len(re.findall(r'^\[\d+\] ',text,re.M)), 'table_hashes':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in blocks.items()},
      'metric_checks':{'T22_JSON_CSV':'passed','T30_JSON_CSV':'passed','T32_arithmetic':'passed','Workplace2013_activity_sum':9827},
      'pdf_settings':{'page':'A4 portrait','margins_cm':2.5,'body_pt':12,'leading_pt':18,'first_line_indent_pt':24,'right_ink_guard_pt':12,'h1_pt':16,'h2_pt':14,'palette':'black/white'},
      'heading_pages':headings,'fonts':'embedded Chinese Songti SC and Heiti SC; glyph preflight passed', 'render_review':'pending independent verification'}
    (OUT/'REPORT_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('body_chinese_characters','abstract_chinese_characters','chapters','figures','tables','references')},ensure_ascii=False))

if __name__=='__main__':main()
