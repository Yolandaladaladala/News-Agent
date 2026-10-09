"""Keyless news discovery with GDELT and Google News RSS.

No paid search API. Publication date is checked against the original article;
RSS and GDELT timestamps are only discovery hints, never verification.
"""
import re
import time
import html
from datetime import timedelta
from urllib.parse import urlparse, urlencode, quote, parse_qs, unquote
import requests
from bs4 import BeautifulSoup

HEADERS={"User-Agent":"Mozilla/5.0 (compatible; XSTAR-NewsResearch/2.0; +https://github.com/Yolandaladaladala/News-Agent)"}
TIMEOUT=7

def publisher_url(url):
    """Resolve aggregator links to publisher pages. Unresolved links are not publishable."""
    url=str(url or "").strip()
    if not url.startswith(("https://","http://")):return ""
    host=(urlparse(url).hostname or "").lower()
    if host not in ("news.google.com","google.com","www.google.com"):return url
    qs=parse_qs(urlparse(url).query)
    for key in ("url","u","q"):
        for candidate in qs.get(key,[]):
            candidate=unquote(candidate)
            if candidate.startswith(("https://","http://")) and "google.com" not in (urlparse(candidate).hostname or ""):
                return candidate
    try:
        r=requests.get(url,headers=HEADERS,timeout=TIMEOUT,allow_redirects=True,stream=True)
        target=r.url
        r.close()
        if (urlparse(target).hostname or "").lower() not in ("news.google.com","google.com","www.google.com"):
            return target
    except requests.RequestException:pass
    return ""

def _unique(rows):
    out=[];seen=set()
    for row in rows:
        url=str(row.get("url","")).strip()
        if not url.startswith(("http://","https://")):continue
        key=url.split("#")[0].split("?")[0].rstrip("/")
        if key in seen:continue
        seen.add(key);out.append(row)
    return out

def gdelt_search(query,start,end,num=15):
    """GDELT DOC API; no key, availability and rate limits vary."""
    params={"query":query[:200],"mode":"artlist","format":"json",
            "startdatetime":start.strftime("%Y%m%d")+"000000",
            "enddatetime":(end+timedelta(days=1)).strftime("%Y%m%d")+"000000",
            "maxrecords":min(75,num),"sort":"datedesc"}
    r=requests.get("https://api.gdeltproject.org/api/v2/doc/doc",
                   params=params,headers=HEADERS,timeout=TIMEOUT)
    r.raise_for_status()
    try:articles=r.json().get("articles",[])
    except ValueError:return []
    return [{"title":x.get("title",""),"url":x.get("url",""),
             "snippet":"","date_hint":x.get("seendate",""),
             "discovery_source":"GDELT"} for x in articles]

def google_news_rss(query,start,end,num=15):
    """Public RSS discovery. News links may redirect; access is not guaranteed."""
    q=f'{query[:150]} after:{start.isoformat()} before:{(end+timedelta(days=1)).isoformat()}'
    params={"q":q,"hl":"en-US","gl":"US","ceid":"US:en"}
    url="https://news.google.com/rss/search?"+urlencode(params)
    r=requests.get(url,headers=HEADERS,timeout=TIMEOUT)
    r.raise_for_status()
    soup=BeautifulSoup(r.content,"xml")
    out=[]
    for item in soup.find_all("item")[:num]:
        title=item.find("title");link=item.find("link");published=item.find("pubDate")
        if not link:continue
        out.append({"title":title.get_text(" ",strip=True) if title else "",
                    "url":link.get_text(" ",strip=True),"snippet":"",
                    "date_hint":published.get_text(" ",strip=True) if published else "",
                    "discovery_source":"Google News RSS"})
    return out

def discover(query,start,end,num=15):
    """Fail over between independent free discovery channels."""
    rows=[];errors=[]
    for name,fn in [("GDELT",gdelt_search),("Google News RSS",google_news_rss)]:
        try:
            rows.extend(fn(query,start,end,num))
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:160]}")
        if len(_unique(rows))>=num:break
        # Google News is only a discovery fallback; resolve links before publication.
    return _unique(rows)[:num],errors

def extractive_review(title,text,source_domain,official=False):
    """Conservative, deterministic fallback: NEVER invent a Chinese translation."""
    text=re.sub(r"\s+"," ",text or "").strip()
    sentences=re.split(r"(?<=[.!?。！？])\s+",text)
    sentences=[s.strip() for s in sentences if len(s.strip())>=40]
    keywords=("loan","credit","finance","financing","vehicle","car","auto","bank",
              "interest","rate","sales","production","tariff","recall","electric",
              "battery","robot","investment","สินเชื่อ","รถยนต์","汽车","贷款","银行")
    def weight(s):
        low=s.lower()
        return sum(1 for k in keywords if k in low)
    sentences.sort(key=weight,reverse=True)
    quote=sentences[0][:280] if sentences else ""
    score=min(90,35+min(30,weight((title or "")+" "+quote)*6)+(20 if official else 5))
    # Extractive mode does not claim AI-verified facts, translation or original-date validation.
    return {"title":title,"summary":quote[:220],"evidence":quote,
            "score":score,"reason":"自动摘录，未使用语言模型；需人工审核中文摘要和数字",
            "supported":False,"model_mode":"extractive"}

def ollama_review(prompt,endpoint,model):
    """Optional self-hosted LLM; no third-party model API key."""
    import json
    endpoint=(endpoint or "").rstrip("/")
    if not endpoint.startswith(("http://","https://")):
        raise ValueError("Ollama endpoint must start with http:// or https://")
    r=requests.post(endpoint+"/api/chat",json={"model":model,"stream":False,
        "format":"json","messages":[{"role":"system","content":"你是严格的新闻核验员。只引用给定原文，不编造事实。只输出JSON。"},
        {"role":"user","content":prompt}]},timeout=120)
    r.raise_for_status()
    body=r.json().get("message",{}).get("content","{}")
    return json.loads(body)
