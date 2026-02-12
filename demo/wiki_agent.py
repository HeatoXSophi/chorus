
import chorus
import httpx

def wiki_handler(data):
    """
    Research Agent: Fetches a summary from Wikipedia.
    Input: {"topic": "Rome", "lang": "es"}
    """
    topic = data.get("topic", "Artificial Intelligence")
    lang = data.get("lang", "es")
    
    print(f"📚 Researching '{topic}' in {lang}...")
    
    try:
        # Wikipedia API is free and doesn't require keys
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{topic}"
        r = httpx.get(url, timeout=10.0)
        
        if r.status_code == 200:
            summary = r.json().get("extract", "No summary available.")
            title = r.json().get("title", topic)
            
            # Format as a "Redacted Work"
            report = f"""
# Reporte: {title}
--------------------------------------------------
{summary}
--------------------------------------------------
Fuente: Wikipedia ({lang})
Generado por: Chorus Research Agent
            """
            return {"report": report.strip(), "source": url}
            
        else:
            return {"error": f"No article found for '{topic}'."}
            
    except Exception as e:
        return {"error": str(e)}

def main():
    print("🚀 Starting Chorus Research Agent...")
    
    # Connect
    # Note: In a real scenario, we'd ask for credentials or use env vars.
    # For this demo, we assume the user edits this or we use the defaults if valid.
    # Re-using the key from supabase_demo.py for convenience in this specific environment
    SUPABASE_URL = "https://yjhwxelvgwaqszletlkk.supabase.co"
    SUPABASE_KEY = "sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu" 
    
    # Ask for login to be safe, or hardcode if user just ran the other demo
    email = "pablo@chorus.dev"
    password = "demo123"

    try:
        chorus.connect(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY, email=email, password=password)
    except:
        print("Connection failed. Check credentials.")
        return

    # Publish
    agent = chorus.publish(
        name="WikiResearcher",
        skill="research",
        cost=15.0, # $1.50
        handler=wiki_handler,
        description="I write summaries about any topic using Wikipedia.",
        serverless=False
    )
    
    print(f"\n✅ WikiResearcher is LIVE at {agent['endpoint']}")
    print("Go to the Studio and try it!")
    
    import time
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
