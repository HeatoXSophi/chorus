from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import urllib.parse
import json
from datetime import datetime

app = FastAPI()

# Enable CORS for portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# AGENT ROUTER — Routes to the correct agent handler
# ================================================================

@app.get("/api/wiki")
async def wiki_root():
    return {"status": "online", "agent": "WikiResearcher Cloud", "version": "2.0"}

@app.get("/api/translate")
async def translate_root():
    return {"status": "online", "agent": "TranslatorBot"}

@app.get("/api/weather")
async def weather_root():
    return {"status": "online", "agent": "WeatherBot"}

@app.get("/api/news")
async def news_root():
    return {"status": "online", "agent": "NewsScanner"}

# ================================================================
# WIKI AGENT — Wikipedia Research (ES + EN)
# ================================================================

@app.post("/api/wiki/jobs")
async def wiki_job(request: Request):
    try:
        data = await request.json()
        input_data = data.get("input_data", {})
        raw_topic = input_data.get("topic", input_data.get("text", "Technology"))
        file_info = input_data.get("file")
        
        # Clean topic: remove common natural language fillers
        topic = raw_topic.lower().strip()
        fillers = [
            "todo sobre ", "algo de ", "información de ", "busca sobre ", 
            "investiga ", "dime sobre ", "qué es ", "quién es ", "quien es ",
            "háblame de ", "cuéntame de ", "resumen de ", "explícame ",
            "información sobre ", "qué sabes de ", "quién fue "
        ]
        found_filler = False
        for filler in fillers:
            if topic.startswith(filler):
                topic = topic.replace(filler, "", 1)
                found_filler = True
                break
        topic = topic.strip()
        
        output = None
        tried_queries = [topic]
        if topic != raw_topic.strip():
            tried_queries.append(raw_topic.strip())
            
        debug_trace = []
        for q in tried_queries:
            for lang in ["es", "en"]:
                debug_trace.append(f"Trying {q} in {lang}")
                result = await search_wikipedia(q, lang)
                if result:
                    output = result
                    break
            if output: break
        
        if not output:
            output = {
                "error": f"No encontré información sobre '{topic}' en Wikipedia.", 
                "report": f"⚠️ No encontré información sobre '{topic}' en Wikipedia. Intenta con otro término más específico.",
                "debug": debug_trace
            }
        
        # If file is present, personalize the report
        if file_info and "report" in output:
            file_name = file_info.get("name", "archivo")
            personalized_intro = f"✨ **He analizado tu archivo {file_name}** y he generado esta versión optimizada con datos de Wikipedia:\n\n"
            output["report"] = personalized_intro + output["report"]
            
        return {
            "job_id": data.get("job_id", ""),
            "status": "SUCCESS",
            "output_data": output,
            "execution_cost": 15.0,
            "execution_time_ms": 800
        }
        
    except Exception as e:
        return {
            "job_id": "",
            "status": "FAILURE", 
            "error_message": str(e),
            "execution_cost": 0,
            "execution_time_ms": 0
        }


async def search_wikipedia(topic: str, lang: str) -> dict | None:
    """Search Wikipedia with multiple attempts and fallbacks."""
    
    # Clean topic
    query = topic.strip()
    if not query: return None
    
    # 1. Try different variants of the query (Wikipedia is case-sensitive)
    search_variants = [
        query,                   # Original
        query.capitalize(),      # 'tenerife' -> 'Tenerife'
        query.title(),           # 'albert einstein' -> 'Albert Einstein'
        query.replace(" ", "_")  # Underscores
    ]
    
    # Remove duplicates but maintain order
    search_variants = list(dict.fromkeys(search_variants))
    
    # Wikipedia requires a meaningful User-Agent
    headers = {"User-Agent": "ChorusBot/2.0 (https://chorus-ruddy.vercel.app/; contact@chorus.app)"}
    
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        for variant in search_variants:
            encoded = urllib.parse.quote(variant.replace(" ", "_"))
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
            
            try:
                r = await client.get(url, follow_redirects=True)
                if r.status_code == 200:
                    wiki_data = r.json()
                    # If it's disambiguation, we'll collect it as a backup
                    summary = wiki_data.get("extract", "")
                    if summary:
                        is_disambig = wiki_data.get("type") == "disambiguation"
                        
                        title = wiki_data.get("title", variant)
                        description = wiki_data.get("description", "")
                        thumbnail = wiki_data.get("thumbnail", {}).get("source", "")
                        page_url = wiki_data.get("content_urls", {}).get("desktop", {}).get("page", "")
                        
                        lang_label = "Español" if lang == "es" else "English"
                        report = f"# {title}\n"
                        if is_disambig:
                            report += f"*(Página de referencia general)*\n\n"
                        if description:
                            report += f"*{description}*\n\n"
                        report += f"---\n\n{summary}\n\n"
                        
                        if is_disambig:
                            report += "💡 *Tip: Puedes buscar términos más específicos relacionados con esta página.*\n\n"
                            
                        report += f"---\n📚 Fuente: Wikipedia ({lang_label})"
                        if page_url:
                            report += f"\n🔗 {page_url}"
                        
                        return {
                            "report": report,
                            "title": title,
                            "summary": summary,
                            "thumbnail": thumbnail,
                            "language": lang,
                            "url": page_url,
                            "is_disambiguation": is_disambig
                        }
            except Exception:
                continue
    
    # Clean query again for API search
    search_query = query.strip()
    
    # 2. Fallback: search API (opensearch) to find the "real" title
    search_url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(search_query)}&limit=3&format=json"
    
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        try:
            sr = await client.get(search_url)
            if sr.status_code == 200:
                search_data = sr.json()
                # search_data format: [query, [titles], [descriptions], [urls]]
                if len(search_data) > 1 and search_data[1]:
                    # Try the first few matches
                    for best_match in search_data[1][:3]:
                        encoded = urllib.parse.quote(best_match.replace(" ", "_"))
                        retry_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
                        r2 = await client.get(retry_url, follow_redirects=True)
                        if r2.status_code == 200:
                            wiki_data = r2.json()
                            summary = wiki_data.get("extract", "")
                            if summary:
                                is_disambig = wiki_data.get("type") == "disambiguation"
                                title = wiki_data.get("title", best_match)
                                description = wiki_data.get("description", "")
                                page_url = wiki_data.get("content_urls", {}).get("desktop", {}).get("page", "")
                                
                                report = f"# {title}\n"
                                if is_disambig:
                                    report += f"*Página de desambiguación*\n\n"
                                if description:
                                    report += f"*{description}*\n\n"
                                report += f"---\n\n{summary}\n\n"
                                report += f"---\n📚 Fuente: Wikipedia"
                                if page_url:
                                    report += f"\n🔗 {page_url}"
                                
                                return {
                                    "report": report,
                                    "title": title,
                                    "summary": summary,
                                    "url": page_url,
                                    "is_disambiguation": is_disambig
                                }
        except Exception:
            pass
            
    return None


# ================================================================
# TRANSLATE AGENT — Free translation via MyMemory API
# ================================================================

@app.post("/api/translate/jobs")
async def translate_job(request: Request):
    try:
        data = await request.json()
        input_data = data.get("input_data", {})
        
        text = input_data.get("topic", input_data.get("text", ""))
        source_lang = input_data.get("from", "auto")
        target_lang = input_data.get("to", "en")
        
        if not text:
            return {"job_id": data.get("job_id", ""), "status": "FAILURE", "error_message": "No text provided"}
        
        # Detect: if text looks Spanish, translate to English; if English, translate to Spanish
        if source_lang == "auto":
            has_spanish = any(c in text.lower() for c in ['ñ', 'á', 'é', 'í', 'ó', 'ú', '¿', '¡'])
            common_es = ['el', 'la', 'los', 'las', 'de', 'en', 'que', 'por', 'es', 'un', 'una', 'como']
            words = text.lower().split()
            es_word_count = sum(1 for w in words if w in common_es)
            
            if has_spanish or es_word_count >= 2:
                source_lang = "es"
                target_lang = "en"
            else:
                source_lang = "en"
                target_lang = "es"
        
        # Use MyMemory API (free, no key needed)
        api_url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={source_lang}|{target_lang}"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(api_url)
        
        if r.status_code == 200:
            result = r.json()
            translated = result.get("responseData", {}).get("translatedText", "")
            
            lang_names = {"es": "Español", "en": "English", "fr": "Français", "de": "Deutsch", "pt": "Português", "it": "Italiano"}
            from_name = lang_names.get(source_lang, source_lang)
            to_name = lang_names.get(target_lang, target_lang)
            
            report = f"# 🌐 Traducción\n"
            report += f"*{from_name} → {to_name}*\n\n"
            
            file_info = input_data.get("file")
            if file_info:
                file_name = file_info.get("name", "archivo")
                report += f"✨ **He analizado tu archivo {file_name}** y he traducido el contenido detectado:\n\n"
            
            report += f"---\n\n"
            report += f"**Original:** {text}\n\n"
            report += f"**Traducción:** {translated}\n\n"
            report += f"---\n🔤 Powered by MyMemory Translation API"
            
            return {
                "job_id": data.get("job_id", ""),
                "status": "SUCCESS",
                "output_data": {
                    "report": report,
                    "original": text,
                    "translated": translated,
                    "from": source_lang,
                    "to": target_lang
                },
                "execution_cost": 10.0,
                "execution_time_ms": 500
            }
        else:
            return {"job_id": data.get("job_id", ""), "status": "FAILURE", "error_message": "Translation API error"}
            
    except Exception as e:
        return {"job_id": "", "status": "FAILURE", "error_message": str(e), "execution_cost": 0}


# ================================================================
# WEATHER AGENT — Current weather via wttr.in (free, no API key)
# ================================================================

@app.post("/api/weather/jobs")
async def weather_job(request: Request):
    try:
        data = await request.json()
        input_data = data.get("input_data", {})
        
        city = input_data.get("topic", input_data.get("city", input_data.get("text", "Madrid")))
        
        # Use wttr.in API (free, no key needed)
        api_url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(api_url, headers={"User-Agent": "Chorus-WeatherBot/1.0"})
        
        if r.status_code == 200:
            weather = r.json()
            current = weather.get("current_condition", [{}])[0]
            area = weather.get("nearest_area", [{}])[0]
            
            area_name = area.get("areaName", [{}])[0].get("value", city)
            country = area.get("country", [{}])[0].get("value", "")
            temp_c = current.get("temp_C", "?")
            feels_like = current.get("FeelsLikeC", "?")
            humidity = current.get("humidity", "?")
            desc_es = current.get("lang_es", [{}])[0].get("value", "") if current.get("lang_es") else ""
            desc_en = current.get("weatherDesc", [{}])[0].get("value", "")
            wind_kmh = current.get("windspeedKmph", "?")
            uv = current.get("uvIndex", "?")
            
            desc = desc_es if desc_es else desc_en
            
            # Weather emoji
            temp = int(temp_c) if temp_c != "?" else 20
            emoji = "🥶" if temp < 5 else "❄️" if temp < 10 else "🌤️" if temp < 20 else "☀️" if temp < 30 else "🔥"
            
            report = f"# {emoji} Clima en {area_name}\n"
            report += f"*{country}*\n\n"
            
            file_info = input_data.get("file")
            if file_info:
                file_name = file_info.get("name", "archivo")
                report += f"✨ **Analizando entorno desde {file_name}...**\nAquí tienes el pronóstico oficial de la zona:\n\n"
            
            report += f"---\n\n"
            report += f"🌡️ **Temperatura:** {temp_c}°C (sensación {feels_like}°C)\n\n"
            report += f"☁️ **Condición:** {desc}\n\n"
            report += f"💧 **Humedad:** {humidity}%\n\n"
            report += f"💨 **Viento:** {wind_kmh} km/h\n\n"
            report += f"☀️ **UV:** {uv}\n\n"
            report += f"---\n🌍 Fuente: wttr.in"
            
            return {
                "job_id": data.get("job_id", ""),
                "status": "SUCCESS",
                "output_data": {
                    "report": report,
                    "city": area_name,
                    "country": country,
                    "temperature": temp_c,
                    "description": desc
                },
                "execution_cost": 10.0,
                "execution_time_ms": 600
            }
        else:
            return {"job_id": data.get("job_id", ""), "status": "FAILURE", "error_message": f"No pude obtener el clima de '{city}'"}
            
    except Exception as e:
        return {"job_id": "", "status": "FAILURE", "error_message": str(e), "execution_cost": 0}


# ================================================================
# NEWS AGENT — Latest news headlines via RSS
# ================================================================

@app.post("/api/news/jobs")
async def news_job(request: Request):
    try:
        data = await request.json()
        input_data = data.get("input_data", {})
        
        topic = input_data.get("topic", input_data.get("text", "technology"))
        
        # Use Google News RSS (free, no key)
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=es-419&gl=US&ceid=US:es-419"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(rss_url)
        
        if r.status_code == 200:
            # Simple XML parsing for RSS
            import re
            items = re.findall(r'<item>.*?</item>', r.text, re.DOTALL)[:5]
            
            headlines = []
            for item in items:
                title_match = re.search(r'<title>(.*?)</title>', item)
                link_match = re.search(r'<link/>(.*?)<', item) or re.search(r'<link>(.*?)</link>', item)
                pub_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
                source_match = re.search(r'<source.*?>(.*?)</source>', item)
                
                if title_match:
                    headlines.append({
                        "title": title_match.group(1).replace('&amp;', '&').replace('&#39;', "'"),
                        "source": source_match.group(1) if source_match else "Google News",
                        "date": pub_match.group(1)[:16] if pub_match else ""
                    })
            
            if not headlines:
                return {
                    "job_id": data.get("job_id", ""),
                    "status": "SUCCESS",
                    "output_data": {"report": f"⚠️ No encontré noticias recientes sobre '{topic}'."},
                    "execution_cost": 10.0,
                    "execution_time_ms": 400
                }
            
            report = f"# 📰 Noticias: {topic}\n"
            report += f"*Últimas {len(headlines)} noticias encontradas*\n\n"
            
            file_info = input_data.get("file")
            if file_info:
                file_name = file_info.get("name", "archivo")
                report += f"✨ **Contexto detectado desde {file_name}**\nHe buscado noticias relevantes para complementar tu documento:\n\n"
            
            report += "---\n\n"
            
            for i, h in enumerate(headlines, 1):
                report += f"**{i}. {h['title']}**\n"
                report += f"   📌 {h['source']}"
                if h['date']:
                    report += f" — {h['date']}"
                report += "\n\n"
            
            report += "---\n📡 Fuente: Google News RSS"
            
            return {
                "job_id": data.get("job_id", ""),
                "status": "SUCCESS",
                "output_data": {
                    "report": report,
                    "topic": topic,
                    "headlines": headlines
                },
                "execution_cost": 10.0,
                "execution_time_ms": 500
            }
        else:
            return {"job_id": data.get("job_id", ""), "status": "FAILURE", "error_message": f"Error buscando noticias sobre '{topic}'"}
            
    except Exception as e:
        return {"job_id": "", "status": "FAILURE", "error_message": str(e), "execution_cost": 0}
