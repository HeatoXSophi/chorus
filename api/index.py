
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

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
        lang = input_data.get("lang", "es")
        
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{topic}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
            
        if r.status_code == 200:
            summary = r.json().get("extract", "No summary.")
            title = r.json().get("title", topic)
            report = f"# Reporte: {title}\n---\n{summary}\n---\nFuente: Wikipedia ({lang})"
            output = {"report": report}
        else:
            output = {"error": "Not found"}
            
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
