import io, json, re, time, html, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dateutil import parser as dtparse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from free_research import discover, extractive_review, ollama_review
from agent_workflow import rank_candidates, parse_edit_request, apply_editorial_operations
from model_gateway import chat_json, interpret_edit

BASE=Path(__file__).parent
RULES=json.loads((BASE/'searching_rules/config.json').read_text(encoding='utf-8'))
REGIONS=RULES['regions']
REGION_CODES={'北美地区':'NA','亚太地区':'APAC','中东地区':'ME','欧洲地区':'EU','拉美地区':'LATAM','非洲地区':'AFR'}
CODE_REGIONS={v:k for k,v in REGION_CODES.items()}
def region_name(value):
    return CODE_REGIONS.get(str(value).strip(),str(value).strip() if str(value).strip() in REGIONS else '亚太地区')
def region_code(value):
    return REGION_CODES.get(region_name(value),'APAC')
COLS=['region_code','region_name_zh','title','date','location','tags','summary','url','url_label','icon_img_url']
AUDIT=['score','status','evidence','source_date','source_domain','source_access','reason','selected','order']
st.set_page_config(page_title='XSTAR News Research Agent',layout='wide',page_icon='📰')
st.title('XSTAR · 全球汽车行业新闻研究 Agent')
st.caption('日期 / 可选线索 → 免费多语言新闻发现 → 原文日期检查 → 可选自建 AI / 免费摘录 → 编辑 → Excel + Outlook HTML')

def search_news(query,start,end,num=10):
    return discover(query,start,end,num)


def scrape(url):
    try:
        r=requests.get(url,timeout=14,headers={'User-Agent':'Mozilla/5.0 (compatible; XSTARResearch/1.0)'},allow_redirects=True)
        if r.status_code!=200:return {'text':'','date':'','access':f'HTTP {r.status_code}'}
        soup=BeautifulSoup(r.text,'html.parser')
        for x in soup(['script','style','nav','footer','header']):x.decompose()
        meta=[]
        for attr,key in [('property','article:published_time'),('name','date'),('itemprop','datePublished'),('name','pubdate'),('name','datePublished')]:
            tag=soup.find('meta',attrs={attr:key})
            if tag and tag.get('content'):meta.append(tag['content'])
        t=soup.find('time',attrs={'datetime':True})
        if t:meta.append(t['datetime'])
        for node in soup.select('article p, main p')[:80]:pass
        paras=[x.get_text(' ',strip=True) for x in soup.select('article p, main p') if len(x.get_text(' ',strip=True))>35]
        if len(paras)<3:paras=[x.get_text(' ',strip=True) for x in soup.find_all('p') if len(x.get_text(' ',strip=True))>35]
        text=' '.join(paras)[:15000]
        blocked=bool(re.search(r'subscribe to (read|continue)|sign in to (read|continue)|already a subscriber|register to read',text[:3000],re.I))
        return {'text':text,'date':meta[0] if meta else '', 'access':'paywall_possible' if blocked else ('accessible' if len(text)>350 else 'insufficient_text')}
    except Exception as e:return {'text':'','date':'','access':f'error: {type(e).__name__}'}

def parse_date(v):
    if not v:return ''
    try:return dtparse.parse(str(v),fuzzy=True).date().isoformat()
    except Exception:return ''

def analyze_news(prompt,mode,endpoint,model,api_key="",base_url=""):
    if mode=="自带 API Key":return chat_json(prompt,api_key,model,base_url)
    if mode=="Ollama（自建模型）":
        return ollama_review(prompt,endpoint,model)
    return None


def country_region(s):
    s=str(s).lower()
    rules=[('北美地区','美国 usa united states 加拿大 canada 墨西哥 mexico'),('拉美地区','巴西 brazil 阿根廷 argentina 智利 chile 哥伦比亚 colombia'),('欧洲地区','英国 uk britain 德国 germany 法国 france 欧洲 europe 欧盟 eu 意大利 italy'),('中东地区','中东 middle east 沙特 saudi 阿联酋 uae 伊朗 iran 以色列 israel'),('非洲地区','非洲 africa 南非 south africa 埃及 egypt')]
    for reg,words in rules:
        if any(w in s for w in words.split(' ')):return reg
    return '亚太地区'

def extract_clues(file,txt):
    clues=[x.strip() for x in txt.splitlines() if x.strip()]
    old=[]
    if file:
        w=pd.ExcelFile(file)
        sh=next((s for s in w.sheet_names if 'news' in s.lower() or '新闻' in s),w.sheet_names[-1])
        df=pd.read_excel(file,sheet_name=sh,usecols=lambda c:str(c) in COLS)
        for _,r in df.iterrows():
            title=str(r.get('title','')).strip()
            if title and title.lower()!='nan':clues.append(title);old.append(title)
    return list(dict.fromkeys(clues)),old

def research(start,end,clues,mode,endpoint,model,progress,depth='快速研究',api_key='',base_url='',target=80):
    fast=depth=='快速研究'
    maxq=24 if fast else int(RULES.get('max_queries',65))
    reserve=min(int(RULES.get('search_budget',{}).get('reserve_queries_for_gap_search',10)),maxq//3)
    buckets=[list(v) for v in RULES.get('local_queries',{}).values()]
    local=[]
    while any(buckets):
        for bucket in buckets:
            if bucket:local.append(bucket.pop(0))
    core=list(RULES.get('topics',[]))
    broad=[v for pair in __import__('itertools').zip_longest(core,local) for v in pair if v]
    direct_urls=[str(x).strip() for x in clues if str(x).strip().startswith(('https://','http://'))]
    clue_queries=[str(x).strip()[:150] for x in clues if str(x).strip() and not str(x).strip().startswith(('https://','http://'))]
    # Put XSTAR priority markets first instead of spreading the first 16 queries thinly.
    if fast:
        priority=[]
        for market in ('泰国','美国','中国','新加坡','日本','韩国','印尼','越南'):
            priority.extend(RULES.get('local_queries',{}).get(market,[])[:2])
        broad=priority+core+local
    all_queries=list(dict.fromkeys(clue_queries+broad))
    primary=all_queries[:maxq-reserve]
    queries=primary+all_queries[maxq-reserve:maxq]
    seen=set(); candidates=[]; errors=[]
    for url in direct_urls:
        key=url.split('?')[0].rstrip('/')
        if key and key not in seen:
            seen.add(key);candidates.append({'title':url,'url':url,'snippet':'','date_hint':''})
    if len(all_queries)>maxq:
        errors.append(f'搜索预算上限 {maxq} 次，剩余 {len(all_queries)-maxq} 个查询未执行。')
    # Small worker pool speeds up independent RSS queries without a 65-request wait.
    # GDELT is fallback only; free providers may still throttle.
    def search_task(item):
        i,q=item
        try:
            found,errs=search_news(q,start,end,RULES['results_per_query'])
            return i,q,found,errs
        except Exception as exc:
            return i,q,[],[str(exc)]
    with ThreadPoolExecutor(max_workers=3 if fast else 2) as pool:
        futures={pool.submit(search_task,item):item for item in enumerate(queries)}
        for done,future in enumerate(as_completed(futures),1):
            i,q,found,errs=future.result()
            progress.progress(done/max(1,len(queries))*0.35,
                              text=f'新闻发现 {done}/{len(queries)} · {q[:32]}')
            errors.extend(f'{q[:30]}: {err}' for err in errs)
            for x in found:
                key=x['url'].split('?')[0].rstrip('/')
                if key and key not in seen:
                    seen.add(key);candidates.append(x)
    if not candidates:raise RuntimeError('免费新闻源没有返回结果。请缩短日期范围、减少搜索词，或稍后重试。')
    # Search rank can be noisy; prioritize accessible official sources without excluding other credible media.
    def rank(x):
        d=urlparse(x['url']).netloc.lower()
        official=any(d==z or d.endswith('.'+z) for z in RULES['primary_domains'])
        return (0 if official else 1,-sum(k in (x['title']+' '+x['snippet']).lower() for k in ['loan','credit','bank','auto','vehicle','car','finance','สินเชื่อ','汽车','รถยนต์']))
    candidates.sort(key=rank)
    rows=[]
    limit=min(len(candidates),max(target,80) if fast else RULES['max_articles_to_review'])
    with ThreadPoolExecutor(max_workers=6) as fetch_pool:
        documents=list(fetch_pool.map(lambda item: scrape(item['url']),candidates[:limit]))
    for i,(x,doc) in enumerate(zip(candidates[:limit],documents)):
        progress.progress(.35+.65*(i+1)/max(1,limit),text=f'分析新闻 {i+1}/{limit}')
        d=parse_date(doc['date'])
        # Search snippet date is not sufficiently authoritative for auto-selection.
        valid_date=bool(d and start.isoformat()<=d<=end.isoformat())
        evidence=doc['text'][:10500]
        if len(evidence)<350 or not valid_date or doc['access']!='accessible':
            rows.append({'region_code':region_code(country_region(x['title'])),'region_name_zh':country_region(x['title']),'title':x['title'],'date':d,'location':'','tags':'','summary':x['snippet'],'url':x['url'],'url_label':urlparse(x['url']).netloc,'icon_img_url':'','score':0,'status':'待核验','evidence':'','source_date':d,'source_domain':urlparse(x['url']).netloc,'source_access':doc['access'],'reason':'原文日期缺失/超范围或正文不可访问','selected':False,'order':i+1})
            continue
        prompt=f'''根据下方原文判断新闻是否值得进入XSTAR全球汽车金融行业快讯。研究日期 {start} 至 {end}。必须逐字摘取原文中支持核心事件及数字的证据片段（连续20-160字符）。不得使用片段之外的信息。\n评分权重：业务相关性30，行业影响25，来源可信度20，时效性15，可行动性10。\n返回JSON对象字段 title(中文), location(中文国家), region(六区之一), tags(2-3个中文标签用；分隔), summary(中文70-150字), evidence(原文逐字证据), score(0-100整数), reason(简短), supported(boolean)。\n标题:{x['title']}\n来源:{x['url']}\n正文:{evidence}'''
        try:
            a=analyze_news(prompt,mode,endpoint,model,api_key,base_url)
            if a is None:
                a=extractive_review(x['title'],evidence,urlparse(x['url']).netloc,
                    any(urlparse(x['url']).netloc.lower().endswith(z) for z in RULES['primary_domains']))
                a['region']=country_region(x['title']+' '+evidence[:500])
                a['location']=''
                a['tags']='待编辑'
                a['supported']=False
            quote=str(a.get('evidence','')).strip()
            summary=str(a.get('summary',''))
            nums=re.findall(r'(?<![\w])\d[\d,.]*%?',summary)
            source_nums=set(re.sub(r'[,，\s]','',v) for v in re.findall(r'(?<![\w])\d[\d,.]*%?',evidence))
            numeric_ok=all(re.sub(r'[,，\s]','',v) in source_nums for v in nums)
            supported=bool(a.get('supported')) and len(quote)>=20 and quote in evidence and numeric_ok
            score=max(0,min(100,int(a.get('score',0)))) if (supported or mode=='免费摘录（无需任何 API Key）') else 0
            region=region_name(a.get('region')) if a.get('region') in REGIONS or a.get('region') in CODE_REGIONS else country_region(a.get('location','')+' '+x['title'])
            rows.append({'region_code':region_code(region),'region_name_zh':region,'title':str(a.get('title') or x['title']),'date':d,'location':str(a.get('location','')),'tags':str(a.get('tags','')),'summary':str(a.get('summary','')),'url':x['url'],'url_label':urlparse(x['url']).netloc,'icon_img_url':'','score':score,'status':'已核验' if supported else ('待人工审核（免费摘录）' if mode=='免费摘录（无需任何 API Key）' else '待核验'),'evidence':quote if (supported or mode!='Ollama（自建模型）') else '', 'source_date':d,'source_domain':urlparse(x['url']).netloc,'source_access':doc['access'],'reason':str(a.get('reason','')) if (supported or mode!='Ollama（自建模型）') else '引文无法定位或摘要数字未在原文中匹配','selected':supported and score>=RULES['min_score'],'order':i+1})
        except Exception as e:errors.append(f'AI分析失败 {x["title"][:35]}: {e}')
    # Near-title duplicate filter; preserves candidates for review.
    tokens=set()
    for row in sorted(rows,key=lambda r:-r['score']):
        key=re.sub(r'[^\w\u4e00-\u9fff]','',row['title'].lower())[:48]
        if key in tokens:row['selected']=False;row['status']='疑似重复';row['reason']='标题重复'
        tokens.add(key)
    chosen=sorted((r for r in rows if r['selected']),key=lambda r:-r['score'])
    for r in chosen[RULES['max_report_items']:]:r['selected']=False
    return rows,errors,len(candidates)

def excel_bytes(df,start,end,issue,original=None,baseline=None):
    """Never rebuild the user's Excel. Preserve the original OOXML bytes if unchanged.
    On edits, change only the news cell values in a copy of the original workbook;
    preserve all untouched text, formatting, dimensions, meta and other worksheets.
    """
    master=BASE/'templates/XSTAR_Excel_Master.xlsx'
    if original is None and not master.exists():
        w=Workbook();w.active.title='news'
        for j,key in enumerate(COLS,1):w.active.cell(1,j,key)
        for i,(_,row) in enumerate(df.iterrows(),2):
            for j,key in enumerate(COLS,1):
                value=row.get(key,'')
                if pd.isna(value):value=None
                if key=='date' and value:
                    dt=pd.to_datetime(value,errors='coerce')
                    value=dt.to_pydatetime() if pd.notna(dt) else None
                w.active.cell(i,j,value)
        out=io.BytesIO();w.save(out);return out.getvalue()
    template=original if original is not None else master.read_bytes()
    same=False
    if baseline is not None and len(df)==len(baseline):
        def normalized(d):
            return [[str(v) if pd.notna(v) else '' for v in row] for row in d[COLS].itertuples(index=False,name=None)]
        same=normalized(df)==normalized(baseline)
    if same:return template
    w=load_workbook(io.BytesIO(template))
    sh=w['news']
    header={str(c.value):c.column for c in sh[1] if c.value is not None}
    if any(k not in header for k in COLS):raise ValueError('范本缺少必要的 news 列')
    original_count=len(baseline) if baseline is not None else sh.max_row-1
    # Preserve template styles, column widths, merged ranges, hyperlinks, row heights.
    from copy import copy
    template_row=2
    for i,(_,r) in enumerate(df.iterrows(),2):
        if i>sh.max_row:
            sh.row_dimensions[i].height=sh.row_dimensions[template_row].height
            for j in range(1,sh.max_column+1):
                src=sh.cell(template_row,j);dst=sh.cell(i,j)
                if src.has_style:dst._style=copy(src._style)
                dst.alignment=copy(src.alignment)
                dst.protection=copy(src.protection)
        for k in COLS:
            cell=sh.cell(i,header[k]);value=r.get(k,'')
            if k=='date':
                parsed=pd.to_datetime(value,errors='coerce')
                value=parsed.to_pydatetime() if pd.notna(parsed) else None
            elif pd.isna(value):value=None
            if cell.value!=value:cell.value=value
    # Clear only old news values, without deleting rows or their styles.
    for i in range(len(df)+2,max(original_count+2,sh.max_row+1)):
        for k in COLS:sh.cell(i,header[k]).value=None
    out=io.BytesIO();w.save(out);return out.getvalue()

def imported_rows(file):
    data=file.getvalue();xls=pd.ExcelFile(io.BytesIO(data))
    sheet=next((x for x in xls.sheet_names if x.lower()=='news'),None)
    if not sheet:raise ValueError('上传的 Excel 必须包含 news Sheet')
    df=pd.read_excel(io.BytesIO(data),sheet_name=sheet,dtype=object)
    missing=[x for x in COLS if x not in df.columns]
    if missing:raise ValueError('缺少列：'+', '.join(missing))
    df=df[COLS].copy().fillna('')
    df['date']=df['date'].apply(lambda x:pd.to_datetime(x,errors='coerce').strftime('%Y-%m-%d') if pd.notna(pd.to_datetime(x,errors='coerce')) else '')
    for k in AUDIT:
        df[k]=False if k=='selected' else (0 if k=='score' else '')
    df['selected']=True  # Imported editorial selection is preserved for preview, not AI-verified.
    df['status']='导入原稿（未自动核验）'
    df['order']=range(1,len(df)+1)
    return df,data

def report_html(df,end,issue,order,meta=None):
    """Render the user's own Outlook generator markup, including VML tags."""
    E=lambda x:html.escape(str(x if pd.notna(x) else ''),quote=True)
    meta=meta or {}
    def date_str(v):
        if isinstance(v,(datetime,date)):return v.strftime('%Y年%m月%d日')
        try:return pd.to_datetime(v).strftime('%Y年%m月%d日')
        except:return str(v or '')
    sections=[]
    for region in order:
        part=df[df.region_code.apply(region_name)==region]
        if part.empty:continue
        cards=[]
        for _,r in part.iterrows():
            tags=str(r.get('tags','') or '')
            pills=[]
            for t in re.split(r'[,，；;]',tags):
                t=t.strip()
                if not t:continue
                w=min(160,max(40,7*len(t)+22))
                bg,fg='#e8f5e9','#2e7d32'
                pills.append(f'<!--[if mso]><v:roundrect arcsize="50%" stroked="f" fillcolor="{bg}" style="height:18px;v-text-anchor:middle;width:{w}px;display:inline-block;vertical-align:middle;"><w:anchorlock/><center style="color:{fg};font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:18px;">{E(t)}</center></v:roundrect><![endif]--><!--[if !mso]><!----><span style="display:inline-block;vertical-align:middle;padding:0 8px;border-radius:999px;background:{bg};color:{fg};font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:18px;">{E(t)}</span><!--<![endif]-->')
            metadata=' | '.join(x for x in [f'<span>📍 {E(r.get("location",""))}</span>' if str(r.get('location','')).strip() else '',f'<span>📅 {E(date_str(r.get("date","")))}</span>' if str(r.get('date','')).strip() else '', ' '.join(pills)] if x)
            url=str(r.get('url','')).strip()
            link=f'<a href="{E(url)}" style="display:inline-block;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.4;text-decoration:none;background:#2563EB;color:#ffffff;padding:8px 12px;border-radius:10px;" target="_blank">🔗 查看原文 ({E(r.get("url_label","原文"))})</a>' if url.startswith(('https://','http://')) else ''
            cards.append(f'<tr><td style="padding:10px 26px;"><table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #e5e7eb;border-radius:12px;"><tr><td style="padding:14px 14px 6px 14px;"><div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;font-weight:700;color:#111827;margin:0;">{E(r.get("title",""))}</div><div style="margin-top:8px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.6;color:#6b7280;">{metadata}</div></td></tr><tr><td style="padding:8px 14px 8px 14px;"><p style="margin:0 0 10px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:1.7;color:#374151;">{E(r.get("summary",""))}</p></td></tr><tr><td style="padding:0 14px 14px 14px;">{link}</td></tr></table></td></tr>')
        sections.append(f'<tr><td style="padding:18px 26px 6px 26px;"><div style="font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.4;font-weight:700;color:#111827;margin:0;">🌍 {E(region)}</div></td></tr>'+''.join(cards))
    html_path=BASE/'templates/HTML_Reference.html'
    if not html_path.exists():
        raise FileNotFoundError('缺少 templates/HTML_Reference.html')
    tpl=html_path.read_text(encoding='utf-8')
    for k,v in {'REPORT_TITLE':meta.get('report_title','全球汽车行业快讯'),'REPORT_DATE':meta.get('report_date',f'{end.year}年{end.month}月'),'REPORT_ISSUE':meta.get('report_issue',issue),'PREHEADER':meta.get('preheader',''),'LAST_UPDATED':meta.get('last_updated',date.today().isoformat()),'REGION_SECTIONS':''.join(sections)}.items():
        tpl=tpl.replace('{{'+k+'}}',E(v) if k!='REGION_SECTIONS' else v)
    return tpl

def read_meta(data):
    if not data:return {}
    try:
        w=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
        if 'meta' not in w.sheetnames:return {}
        sh=w['meta'];pairs={str(r[0]).strip():r[1] for r in sh.iter_rows(min_row=1,max_col=2,values_only=True) if r[0] is not None}
        return {k:str(pairs[k]) for k in ['report_title','report_date','report_issue','preheader','last_updated'] if k in pairs and pairs[k] is not None}
    except Exception:return {}

with st.sidebar:
    st.header('研究设置')
    start=st.date_input('开始日期',date.today()-timedelta(days=14))
    end=st.date_input('结束日期',date.today())
    issue=st.text_input('期数','第1期')
    file=st.file_uploader('上传原版 Excel（直接预览，保留全部原文和格式）',type=['xlsx'])
    clues_text=st.text_area('可选：粘贴新闻标题或 URL（每行一条）',height=130)
    st.caption('Excel 上传后直接预览；不调用 AI，不重写任何原文。AI 搜索是独立的补充功能。')
    mode=st.radio('内容处理方式',['免费摘录（无需任何 API Key）','自带 API Key','Ollama（自建模型）'],index=0)
    endpoint='';model='';api_key='';base_url=''
    if mode=='自带 API Key':
        base_url=st.text_input('OpenAI 兼容 API Base URL',value='https://openrouter.ai/api/v1')
        api_key=st.text_input('你的 API Key（不保存）',type='password')
        model=st.text_input('模型 ID',value='openai/gpt-4o-mini')
    if mode=='Ollama（自建模型）':
        endpoint=st.text_input('Ollama 服务地址',value='',placeholder='https://your-private-ollama-host')
        model=st.text_input('Ollama 模型名称',value='qwen2.5:7b')
        st.warning('云端 Streamlit 无法访问你电脑上的 localhost。请使用自己管理的可访问模型服务，并做好认证与访问控制。')
    elif mode=='免费摘录（无需任何 API Key）':
        st.caption('免费摘录不调用语言模型，复杂指令和中文摘要需自带 API Key 或 Ollama。')
    load=st.button('📂 加载 Excel 并立即预览',use_container_width=True,disabled=file is None)
    depth=st.radio('研究深度',['快速研究','深度研究'],horizontal=True,help='快速研究最多24组查询和80篇正文；深度研究使用完整预算。')
    run=st.button('🔎 免费搜索 / 补充研究',type='primary',use_container_width=True)
    st.caption('规则可直接修改 searching_rules/config.json 和 RESEARCH_RULES.md')
if load and file is not None:
    try:
        loaded,original=imported_rows(file)
        st.session_state.rows=loaded
        st.session_state.original_xlsx=original
        st.session_state.original_rows=loaded[COLS].copy(deep=True)
        st.session_state.errors=[]
        st.session_state.found=len(loaded)
        st.session_state.range=(start,end,issue)
        st.session_state.editor_version=st.session_state.get('editor_version',0)+1
        st.success(f'已载入 {len(loaded)} 条新闻。无需 API，可直接预览和下载。')
    except Exception as e:st.error(f'Excel 载入失败：{e}')
if run:
    if start>end:st.error('开始日期不能晚于结束日期')
    elif mode=='Ollama（自建模型）' and not endpoint:st.error('请填写 Ollama 服务地址')
    elif mode=='自带 API Key' and not api_key:st.error('请填写 API Key')
    else:
        try:
            clues,old=extract_clues(file,clues_text)
            bar=st.progress(0,text='准备搜索')
            rows,errors,n=research(start,end,clues,mode,endpoint,model,bar,depth,api_key,base_url)
            st.session_state.candidate_pool=rows
            shortlist,reserve=rank_candidates(rows,30)
            st.session_state.reserve_pool=reserve
            rows=shortlist
            for item in rows:
                item['selected']=True  # Editorial shortlist, not a claim of verification.
            if 'rows' in st.session_state and len(st.session_state.rows):
                prior=st.session_state.rows
                rows_df=pd.DataFrame(rows)
                combined=pd.concat([prior,rows_df],ignore_index=True)
                combined=combined.drop_duplicates(subset=['url'],keep='first')
                st.session_state.rows=combined
            else:st.session_state.rows=pd.DataFrame(rows)
            st.session_state.editor_version=st.session_state.get('editor_version',0)+1
            st.session_state.errors=errors
            st.session_state.found=n
            st.session_state.range=(start,end,issue)
            bar.empty()
        except Exception as e:st.error(f'研究未完成：{e}')
if 'rows' in st.session_state:
    df=st.session_state.rows
    st.success(f'当前精选 {len(df)} 条；其中 {int(df.selected.sum())} 条纳入报告。可通过自然语言修改。')
    st.warning('自动入选不等于事实核验通过。请检查 status 和原文证据后再发布。')
    if st.session_state.errors:
        with st.expander(f'搜索/分析异常 {len(st.session_state.errors)} 条'):
            st.code('\n'.join(st.session_state.errors[:80]))
    st.subheader('自然语言修改与补充')
    instruction=st.text_area('例如：删除3、7；补充泰国央行汽车金融新闻；把第5条标题改成……',key='edit_instruction')
    if st.button('应用修改指令'):
        if instruction.strip():
            try:
                current=st.session_state.rows.to_dict('records')
                for i,row in enumerate(current,1):row.setdefault('news_id',i)
                if mode=='自带 API Key' and api_key:
                    plan=interpret_edit(instruction,current,api_key,model,base_url)
                    updated=apply_editorial_operations(current,plan.get('operations',[]))
                    additions=plan.get('research_requests',[])
                    if additions:
                        bar=st.progress(0,text='仅搜索补充线索')
                        extra,errs,_=research(start,end,additions,mode,endpoint,model,bar,'快速研究',api_key,base_url,target=15)
                        st.session_state.errors=st.session_state.get('errors',[])+errs
                        seen_urls={str(x.get('url')) for x in updated}
                        updated.extend(x for x in extra if str(x.get('url')) not in seen_urls)
                        bar.empty()
                    st.session_state.rows=pd.DataFrame(updated)
                    st.success('已应用修改，请审核。')
                else:
                    plan=parse_edit_request(instruction,current)
                    if plan['action']=='delete':
                        st.session_state.rows=pd.DataFrame(plan['rows'],columns=st.session_state.rows.columns)
                        st.success('已删除：'+str(plan['ids']))
                    else:st.warning(plan['message'])
                st.session_state.editor_version=st.session_state.get('editor_version',0)+1
                st.rerun()
            except Exception as ex:st.error(f'修改失败：{ex}')
    if st.session_state.get('reserve_pool'):
        with st.expander('查看未入选候选'):
            st.dataframe(pd.DataFrame(st.session_state.reserve_pool)[['news_id','title','score','status','url']],hide_index=True)
    st.subheader('1 · 新闻研究与编辑')
    st.caption('上传的 Excel 原文、列顺序、meta 与格式不自动改写；编辑内容后仅更新对应新闻单元格。纳入状态只影响 HTML 快报。')
    if 'news_id' not in df.columns:df=df.copy();df['news_id']=range(1,len(df)+1)
    edited=st.data_editor(df,hide_index=True,num_rows='dynamic',use_container_width=True,key=f"news_editor_{st.session_state.get('editor_version',0)}",column_config={'selected':st.column_config.CheckboxColumn('纳入快报'),'score':st.column_config.NumberColumn('分数',min_value=0,max_value=100),'region_code':st.column_config.SelectboxColumn('地区',options=list(REGION_CODES.values())),'order':st.column_config.NumberColumn('顺序',min_value=0)},disabled=['news_id','source_date','source_access','source_domain'],height=520)
    st.session_state.rows=edited
    st.subheader('2 · 地区顺序')
    region_order=st.multiselect('按选择顺序显示地区',REGIONS,default=REGIONS)
    region_order=region_order+[x for x in REGIONS if x not in region_order]
    selected=edited[edited['selected'].fillna(False).astype(bool)].copy()
    selected['order']=pd.to_numeric(selected['order'],errors='coerce').fillna(9999)
    selected=selected.sort_values('order')
    selected['region_code']=selected['region_code'].apply(region_code)
    html_rows=pd.concat([selected[selected.region_code==REGION_CODES[r]] for r in region_order],ignore_index=True)
    s,e,iss=st.session_state.range
    # Excel retains the user's original news text, rows, metadata, and formatting.
    # Inclusion/order only control the HTML, unless actual news cell text is edited.
    xlsx=None;page=None
    try:
        xlsx=excel_bytes(edited,s,e,iss,st.session_state.get('original_xlsx'),st.session_state.get('original_rows'))
    except Exception as ex:st.error(f'Excel 导出不可用：{ex}')
    try:
        page=report_html(html_rows,e,iss,region_order,read_meta(st.session_state.get('original_xlsx')))
    except Exception as ex:st.error(f'HTML 预览不可用：{ex}')
    st.subheader('3 · Outlook HTML 实时预览')
    if st.session_state.get('original_xlsx') is None and not (BASE/'templates/XSTAR_Excel_Master.xlsx').exists():
        st.info('当前 Excel 为简化备用格式。上传原版母版后才能保持原始版式。')
    if page:st.components.v1.html(page,height=720,scrolling=True)
    a,b,c=st.columns(3)
    with a:st.download_button('📊 下载 Excel',xlsx if xlsx is not None else b'',disabled=xlsx is None,file_name=f'XSTAR_news_{s}_{e}.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
    with b:st.download_button('📧 下载 HTML 快报',page or '',disabled=page is None,file_name=f'全球汽车行业快讯_{e}.html',mime='text/html',use_container_width=True)
    with c:st.download_button('🔍 下载全部研究审计 CSV',edited.to_csv(index=False).encode('utf-8-sig'),file_name=f'XSTAR_audit_{e}.csv',mime='text/csv',use_container_width=True)
else:
    st.info('上传 Excel 后点击「加载 Excel 并立即预览」，不需要 API；或者填写日期，点击「AI 搜索 / 补充研究」。')
