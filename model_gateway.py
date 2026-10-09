"""Optional OpenAI-compatible model endpoint. Keys are never persisted or logged."""
import json
import requests

def chat_json(prompt, api_key, model, base_url="https://openrouter.ai/api/v1", timeout=65):
    if not api_key or not str(api_key).strip():raise ValueError("API key required")
    url=str(base_url).rstrip("/")
    if not url.startswith("https://"):raise ValueError("Model endpoint must use HTTPS")
    if not url.endswith("/chat/completions"):url+="/chat/completions"
    response=requests.post(url,headers={"Authorization":"Bearer "+api_key.strip(),"Content-Type":"application/json"},
        json={"model":model,"temperature":0.1,"messages":[
            {"role":"system","content":"You are a precise automotive industry research editor. Only return valid JSON. Never fabricate article facts."},
            {"role":"user","content":prompt}]},timeout=timeout)
    response.raise_for_status()
    text=response.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text=text.split("\n",1)[-1].rsplit("```",1)[0].strip()
    return json.loads(text)

def interpret_edit(message,rows,api_key,model,base_url):
    index=[{"news_id":int(r["news_id"]),"title":str(r.get("title",""))[:130]} for r in rows]
    prompt=("Interpret the user's Chinese or English editorial request. "
            "Return JSON {operations:[{action:'delete'|'update',news_id:integer,fields:{...}}],"
            "research_requests:[string], notes:string}. "
            "Only existing IDs can be deleted/updated. Allowed update fields: title,summary,tags,location,region_name_zh,region_code,order. "
            "For new news or topical supplementation, put the search request in research_requests; never invent a news row. "
            "Never infer deletions unless explicitly requested. "
            "News index: "+json.dumps(index,ensure_ascii=False)+"\nUser request: "+message)
    result=chat_json(prompt,api_key,model,base_url)
    if not isinstance(result,dict):raise ValueError("Model returned invalid edit JSON")
    return result
