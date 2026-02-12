
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import urllib.parse

app = FastAPI()

@app.get("/api/wiki")
async def wiki_root():
    return {"status": "online", "agent": "WikiResearcher Cloud"}

@app.post("/api/wiki/jobs")
async def wiki_job(request: Request):
    try:
        data = await request.json()
        input_data = data.get("input_data", {})
        
        # Core Logic
        topic = input_data.get("topic", "Technology")
        
        # Try Spanish Wikipedia first, then English
        output = None
        for lang in ["es", "en"]:
            result = await search_wikipedia(topic, lang)
            if result:
                output = result
                break
        
        if not output:
            output = {"error": f"No encontré información sobre '{topic}' en Wikipedia."}
            
        return {
            "job_id": data.get("job_id"),
            "status": "SUCCESS",
            "output_data": output,
            "execution_cost": 15.0
        }
        
    except Exception as e:
        return {
            "status": "FAILURE", 
            "error_message": str(e)
        }


async def search_wikipedia(topic: str, lang: str) -> dict | None:
    """Search Wikipedia for a topic. Returns dict with report or None if not found."""
    
    encoded_topic = urllib.parse.quote(topic.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
    
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=10.0, follow_redirects=True)
        
    if r.status_code == 200:
        wiki_data = r.json()
        # Skip disambiguation pages
        if wiki_data.get("type") == "disambiguation":
            return None
            
        summary = wiki_data.get("extract", "")
        if not summary:
            return None
            
        title = wiki_data.get("title", topic)
        description = wiki_data.get("description", "")
        thumbnail = wiki_data.get("thumbnail", {}).get("source", "")
        
        lang_label = "Español" if lang == "es" else "English"
        report = f"# {title}\n"
        if description:
            report += f"*{description}*\n\n"
        report += f"---\n\n{summary}\n\n"
        report += f"---\n📚 Fuente: Wikipedia ({lang_label})"
        
        return {
            "report": report,
            "title": title,
            "summary": summary,
            "thumbnail": thumbnail,
            "language": lang
        }
    
    # If direct lookup failed, try search
    search_url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(topic)}&limit=1&format=json"
    
    async with httpx.AsyncClient() as client:
        sr = await client.get(search_url, timeout=10.0)
    
    if sr.status_code == 200:
        search_data = sr.json()
        if len(search_data) > 1 and search_data[1]:
            best_match = search_data[1][0].replace(" ", "_")
            retry_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(best_match)}"
            async with httpx.AsyncClient() as client:
                r2 = await client.get(retry_url, timeout=10.0, follow_redirects=True)
            if r2.status_code == 200:
                wiki_data = r2.json()
                summary = wiki_data.get("extract", "")
                if summary:
                    title = wiki_data.get("title", topic)
                    description = wiki_data.get("description", "")
                    lang_label = "Español" if lang == "es" else "English"
                    
                    return {
                        "report": f"# {title}\n*{description}*\n\n---\n\n{summary}\n\n---\n📚 Fuente: Wikipedia ({lang_label})",
                        "title": title,
                        "summary": summary,
                        "language": lang
                    }
    
    return None
