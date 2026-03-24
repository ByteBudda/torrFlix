import os, json, httpx, aiofiles, hashlib, secrets
from fastapi import FastAPI, HTTPException, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBasic()

# Настройки доступа (берутся из Docker Compose или дефолтные)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "pass777")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
CACHE_DIR = os.path.join(BASE_DIR, 'cache_img')
os.makedirs(CACHE_DIR, exist_ok=True)

class Settings(BaseModel):
    tmdb_key: str = ""
    jack_url: str = "http://127.0.0.1:9117"
    jack_key: str = ""

def get_cfg():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return Settings(**json.load(f))
        except: pass
    return Settings()

def save_cfg(s: Settings):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(s.model_dump(), f)

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    is_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    is_pass = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (is_user and is_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_magnet_from_torrent(content: bytes) -> str:
    try:
        start = content.find(b'4:info') + 6
        end = content.rfind(b'ee') + 1
        if start > 5 and end > start:
            sha1 = hashlib.sha1(content[start:end]).hexdigest()
            return f"magnet:?xt=urn:btih:{sha1}"
    except: pass
    return None

async def tmdb_req(url):
    cfg = get_cfg()
    if not cfg.tmdb_key: return {"results": []}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url.replace("API_KEY", cfg.tmdb_key))
        data = r.json()
        if 'results' in data:
            for i in data['results']:
                if i.get('poster_path'):
                    # Проксируем картинки через наш сервер для обхода блокировок
                    i['poster_url'] = f"/proxy-img?url={i['poster_path']}&id={i['id']}"
        return data

# --- АДМИН-ПАНЕЛЬ ---
@app.get("/api/admin/config")
async def get_config_endpoint(user: str = Depends(authenticate)):
    return get_cfg()

@app.post("/api/admin/config")
async def save_config_endpoint(s: Settings, user: str = Depends(authenticate)):
    save_cfg(s)
    return {"status": "ok"}

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return """
    <html><head><title>torrFLIX Admin</title><style>
        body { background: #0a0a0a; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { background: #141414; padding: 40px; border-radius: 15px; border: 1px solid #333; width: 400px; }
        h2 { margin-top: 0; color: #e50914; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid #444; color: white; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: #e50914; border: none; color: white; font-weight: bold; cursor: pointer; border-radius: 5px; margin-top: 10px; }
        #m { text-align: center; margin-top: 10px; font-size: 14px; }
    </style></head><body>
        <div class="box">
            <h2>Настройки</h2>
            <input id="t" placeholder="TMDB API Key">
            <input id="u" placeholder="Jackett URL (ex: http://ip:9117)">
            <input id="k" placeholder="Jackett API Key">
            <button onclick="save()">СОХРАНИТЬ</button>
            <p id="m"></p>
        </div>
        <script>
            async function load(){
                const r = await fetch('/api/admin/config');
                if(r.ok){
                    const d = await r.json();
                    document.getElementById('t').value = d.tmdb_key;
                    document.getElementById('u').value = d.jack_url;
                    document.getElementById('k').value = d.jack_key;
                }
            }
            async function save(){
                const d = { tmdb_key: document.getElementById('t').value, jack_url: document.getElementById('u').value, jack_key: document.getElementById('k').value };
                const r = await fetch('/api/admin/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(d) });
                document.getElementById('m').innerText = r.ok ? "Сохранено успешно!" : "Ошибка сохранения";
            }
            load();
        </script>
    </body></html>
    """

# --- ПУБЛИЧНОЕ API ---
@app.get("/")
async def index():
    async with aiofiles.open(os.path.join(BASE_DIR, "index.html"), mode='r', encoding='utf-8') as f:
        return HTMLResponse(content=await f.read())

@app.get("/api/{mtype}/category")
async def get_cat(mtype: str, cat: str = "popular", page: int = 1):
    return await tmdb_req(f"https://api.themoviedb.org/3/{mtype}/{cat}?api_key=API_KEY&language=ru-RU&page={page}")

@app.get("/api/search/all")
async def search_all(query: str, page: int = 1):
    return await tmdb_req(f"https://api.themoviedb.org/3/search/multi?api_key=API_KEY&language=ru-RU&query={query}&page={page}")

@app.get("/api/search/torrents")
async def search_torrents(title: str, orig_title: str = ""):
    c = get_cfg()
    if not c.jack_key: return []
    query = f"{title} {orig_title}" if orig_title and orig_title != title else title
    
    # Категории: 2000 (Movies), 5000 (TV)
    cats = [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060, 2070, 2080, 5000, 5010, 5020, 5030, 5040, 5045, 5060, 5070, 5080]
    cat_params = "".join([f"&Category[]={cat}" for cat in cats])
    
    url = f"{c.jack_url}/api/v2.0/indexers/all/results?apikey={c.jack_key}&Query={query}{cat_params}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(url)
            res = r.json().get("Results", [])
            return sorted([
                {"Title": t['Title'], "Size": t['Size'], "Seeders": t['Seeders'], "Link": t.get('MagnetUri') or t.get('Link'), "Details": t.get('Details')} 
                for t in res
            ], key=lambda x: x['Seeders'], reverse=True)[:40]
        except: return []

@app.get("/api/play")
async def play(link: str):
    if link.startswith("magnet:"): return RedirectResponse(url=link)
    async with httpx.AsyncClient(follow_redirects=True, timeout=25.0) as client:
        try:
            r = await client.get(link)
            if "magnet:" in str(r.url): return RedirectResponse(url=str(r.url)[str(r.url).find("magnet:?"):])
            if b"announce" in r.content[:200] or "torrent" in r.headers.get("Content-Type", ""):
                mag = get_magnet_from_torrent(r.content)
                if mag: return RedirectResponse(url=mag)
            return RedirectResponse(url=str(r.url))
        except: return RedirectResponse(url=link)

@app.get("/proxy-img")
async def proxy_img(url: str, id: str):
    path = os.path.join(CACHE_DIR, f"{id}.jpg")
    if os.path.exists(path): return FileResponse(path)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"https://image.tmdb.org/t/p/w500{url}")
            if r.status_code == 200:
                async with aiofiles.open(path, 'wb') as f: await f.write(r.content)
                return FileResponse(path)
        except: pass
    return Response(status_code=404)

@app.get("/api/genres/{mtype}")
async def genres(mtype: str):
    return await tmdb_req(f"https://api.themoviedb.org/3/genre/{mtype}/list?api_key=API_KEY&language=ru-RU")

@app.get("/api/trailer/{mtype}/{mid}")
async def trailer(mtype: str, mid: int):
    v = (await tmdb_req(f"https://api.themoviedb.org/3/{mtype}/{mid}/videos?api_key=API_KEY&language=ru-RU")).get('results', [])
    return {"key": next((i['key'] for i in v if i['site'] == 'YouTube'), None)}

@app.get("/api/discover/{mtype}/{gid}")
async def discover(mtype: str, gid: int, page: int = 1):
    return await tmdb_req(f"https://api.themoviedb.org/3/discover/{mtype}?api_key=API_KEY&language=ru-RU&with_genres={gid}&page={page}&sort_by=popularity.desc")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8800)