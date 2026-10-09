"""Pure, testable editorial workflow for XSTAR. No Streamlit or network dependency."""
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def canonical_url(url):
    p=urlparse(str(url or "").strip())
    query=urlencode([(k,v) for k,v in parse_qsl(p.query) if not (k.lower().startswith("utm_") or k.lower() in {"fbclid","gclid"})])
    return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip("/"),"",query,""))

def event_key(row):
    title=re.sub(r"[^\w\u4e00-\u9fff]+","",str(row.get("title","")).lower())
    return title[:65] or canonical_url(row.get("url"))

def rank_candidates(rows, target=30):
    """Return an editorial shortlist and reserve; never fabricate missing rows."""
    unique={}
    for r in rows:
        if not str(r.get("title","")).strip():continue
        key=canonical_url(r.get("url")) or event_key(r)
        if key not in unique or int(r.get("score") or 0)>int(unique[key].get("score") or 0):
            unique[key]=dict(r)
    items=sorted(unique.values(),key=lambda r:(str(r.get("status","")).startswith("已核验"),int(r.get("score") or 0)),reverse=True)
    for i,r in enumerate(items,1):r["news_id"]=i
    return items[:target],items[target:]

def parse_edit_request(message, rows):
    """Conservative no-LLM fallback: deletion only; ambiguous edits are never guessed."""
    text=str(message or "").strip()
    ids=[]
    for match in re.finditer(r"(?:删除|删掉|去掉|移除|不要|remove|delete)\s*([\d\s,，、和及与]+)",text,re.I):
        ids.extend(int(v) for v in re.findall(r"\d+",match.group(1)))
    existing={int(r.get("news_id",i+1)) for i,r in enumerate(rows)}
    ids=sorted(set(ids))
    if any(i not in existing for i in ids):
        return {"action":"error","message":"编号不存在，请使用当前清单中的编号","ids":ids}
    if ids:
        remaining=[dict(r) for i,r in enumerate(rows) if int(r.get("news_id",i+1)) not in ids]
        return {"action":"delete","rows":remaining,"ids":ids}
    return {"action":"needs_ai","message":"这条指令需要语言模型理解；免费模式不会猜测你的编辑意图。"}

def apply_editorial_operations(rows,operations):
    """Validated structured operations from an LLM; never modify rows outside requested IDs."""
    updated=[dict(r) for r in rows]
    for op in operations:
        action=op.get("action")
        if action not in {"delete","update"}:raise ValueError("Unsupported operation: "+str(action))
        news_id=int(op["news_id"])
        matching=[r for r in updated if int(r["news_id"])==news_id]
        if len(matching)!=1:raise ValueError("Unknown news_id "+str(news_id))
        if action=="delete":updated=[r for r in updated if int(r["news_id"])!=news_id]
        else:
            allowed={"title","summary","tags","location","region_name_zh","region_code","order"}
            fields=op.get("fields",{})
            if not isinstance(fields,dict) or set(fields)-allowed:raise ValueError("Invalid update fields")
            matching[0].update(fields)
    return updated
