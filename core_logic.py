# core_logic.py
import os
import io
import re
import json
import base64
import random
import asyncio
import aiohttp
import requests 
import urllib3 
import numpy as np 
import cv2 
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

async def fetch_url(url, method="GET", data=None, headers=None, json_data=None):
    async with aiohttp.ClientSession() as session:
        try:
            if method == "GET":
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200: return await resp.json() if "application/json" in resp.headers.get("Content-Type", "") else await resp.read()
            elif method == "POST":
                async with session.post(url, data=data, json=json_data, headers=headers, ssl=False, timeout=15) as resp:
                    return await resp.text()
        except: return None
    return None

def setup_resources():
    if not os.path.exists("kalpurush.ttf"):
        try: open("kalpurush.ttf", "wb").write(requests.get(URL_FONT).content)
        except: pass
    if not os.path.exists("haarcascade_frontalface_default.xml"):
        try: open("haarcascade_frontalface_default.xml", "wb").write(requests.get(URL_MODEL).content)
        except: pass

def get_font(size=60, bold=False):
    try:
        if os.path.exists("kalpurush.ttf"): return ImageFont.truetype("kalpurush.ttf", size)
        return ImageFont.load_default()
    except: return ImageFont.load_default()

def upload_image_core(file_content):
    try:
        response = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload", "userhash": ""}, files={"fileToUpload": ("image.png", file_content, "image/png")}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
        if response.status_code == 200: return response.text.strip()
    except: pass
    return None

def upload_to_catbox_bytes(img_bytes):
    try:
        if hasattr(img_bytes, 'read'): img_bytes.seek(0); data = img_bytes.read()
        else: data = img_bytes
        return upload_image_core(data)
    except: return None

def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f: return upload_image_core(f.read())
    except: return None

def extract_tmdb_id(text):
    tmdb_match = re.search(r'themoviedb\.org/(movie|tv)/(\d+)', text)
    if tmdb_match: return tmdb_match.group(1), tmdb_match.group(2)
    imdb_id_match = re.search(r'(tt\d{6,})', text)
    if imdb_id_match: return "imdb", imdb_id_match.group(1)
    return None, None

async def search_tmdb(query):
    try:
        match = re.search(r'(.+?)\s*\(?(\d{4})\)?$', query)
        name = match.group(1).strip() if match else query.strip()
        year = match.group(2) if match else None
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={name}&include_adult=true"
        if year: url += f"&year={year}"
        data = await fetch_url(url)
        return [r for r in data.get("results", []) if r.get("media_type") in ["movie", "tv"]][:15] if data else []
    except: return []

async def get_tmdb_details(media_type, media_id):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={TMDB_API_KEY}&append_to_response=credits,similar,images,videos&include_image_language=en,null"
    return await fetch_url(url)

async def create_paste_link(content):
    if not content: return None
    url = "https://dpaste.com/api/"
    link = await fetch_url(url, method="POST", data={"content": content, "syntax": "html", "expiry_days": 14, "title": "Movie Post Code"}, headers={'User-Agent': 'Mozilla/5.0'})
    if link and "dpaste.com" in link: return link.strip()
    return None

def get_smart_badge_position(pil_img):
    try:
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        if not os.path.exists("haarcascade_frontalface_default.xml"): return int(pil_img.height * 0.40) 
        faces = cv2.CascadeClassifier("haarcascade_frontalface_default.xml").detectMultiScale(gray, 1.1, 4)
        if len(faces) > 0:
            lowest_y = max([y + h for (x, y, w, h) in faces])
            target_y = lowest_y + 40 
            return 80 if target_y > (pil_img.height - 130) else target_y
        return int(pil_img.height * 0.40) 
    except: return 200

def apply_badge_to_poster(poster_bytes, text):
    try:
        base_img = Image.open(io.BytesIO(poster_bytes)).convert("RGBA")
        width, height = base_img.size
        font = get_font(size=70) 
        pos_y = get_smart_badge_position(base_img)
        draw = ImageDraw.Draw(base_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        padding_x, padding_y = 40, 20
        box_w = text_w + (padding_x * 2)
        box_h = text_h + (padding_y * 2)
        pos_x = (width - box_w) // 2
        
        overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rectangle([pos_x, pos_y, pos_x + box_w, pos_y + box_h], fill=(0, 0, 0, 150))
        base_img = Image.alpha_composite(base_img, overlay)
        
        draw = ImageDraw.Draw(base_img)
        cx, cy = pos_x + padding_x, pos_y + padding_y - 12
        words = text.split()
        if len(words) >= 2:
            draw.text((cx, cy), words[0], font=font, fill="#FFEB3B")
            draw.text((cx + draw.textlength(words[0], font=font) + 15, cy), " ".join(words[1:]), font=font, fill="#FF5722")
        else:
            draw.text((cx, cy), text, font=font, fill="#FFEB3B")

        img_buffer = io.BytesIO()
        base_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer
    except: return io.BytesIO(poster_bytes)

# 🔥 Plugin Compatibility Maintained (5 arguments only)
def generate_html_code(data, links, user_ad_links_list, owner_ad_links_list, admin_share_percent=20):
    
    # 🔥 Data Dictionary থেকে টাইমারটি বের করা হলো (এতে আর এরর আসবে না)
    wait_timer_seconds = data.get("wait_time", 5)
    
    title = data.get("title") or data.get("name")
    overview = data.get("overview", "No plot available.")
    poster = data.get('manual_poster_url') or f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}"
    
    backdrop = data.get('backdrop_path')
    bg_url = f"https://image.tmdb.org/t/p/original{backdrop}" if backdrop else poster

    is_adult = data.get('adult', False) or data.get('force_adult', False)
    is_batch = data.get('is_batch', False)
    post_id = data.get('post_id', '')
    quality = data.get('custom_quality', '').upper()

    theme = data.get("theme", "netflix")
    if theme == "netflix": root_css = "--bg-color: #0f0f13; --box-bg: #1a1a24; --text-main: #ffffff; --text-muted: #d1d1d1; --primary: #E50914; --accent: #00d2ff; --border: #2a2a35; --btn-grad: linear-gradient(90deg, #E50914 0%, #ff5252 100%); --btn-shadow: 0 10px 30px rgba(229, 9, 20, 0.4);"
    elif theme == "prime": root_css = "--bg-color: #050505; --box-bg: #111111; --text-main: #eeeeee; --text-muted: #8197a4; --primary: #00A8E1; --accent: #00A8E1; --border: #222222; --btn-grad: linear-gradient(90deg, #00A8E1 0%, #00d2ff 100%); --btn-shadow: 0 10px 30px rgba(0, 168, 225, 0.4);"
    else: root_css = "--bg-color: #1a1b26; --box-bg: #24283b; --text-main: #c0caf5; --text-muted: #a9b1d6; --primary: #ff79c6; --accent: #bb9af7; --border: #414868; --btn-grad: linear-gradient(90deg, #ff79c6 0%, #bd93f9 100%); --btn-shadow: 0 10px 30px rgba(255, 121, 198, 0.4);"

    lang_str = data.get('custom_language', 'Dual Audio').strip()
    if data.get('is_manual'):
        genres_str, year, rating, runtime_str, cast_names = "Custom / Unknown", "N/A", "0.0", "N/A", "N/A"
    else:
        genres_list =[g['name'] for g in data.get('genres',[])]
        genres_str = ", ".join(genres_list) if genres_list else "Movie"
        year = str(data.get("release_date") or data.get("first_air_date") or "----")[:4]
        rating = f"{data.get('vote_average', 0):.1f}"
        runtime = data.get('runtime') or (data.get('episode_run_time',[0])[0] if data.get('episode_run_time') else "N/A")
        runtime_str = f"{runtime} min" if runtime != "N/A" else "N/A"
        cast_list = data.get('credits', {}).get('cast',[])
        cast_names = ", ".join([c['name'] for c in cast_list[:4]]) if cast_list else "Unknown"

    badges_html = f'<div class="badge">{lang_str}</div><div class="badge">⭐ {rating}/10</div><div class="badge">{year}</div>'
    if '1080P' in quality: badges_html += '<div class="badge badge-hdr">1080p Full HD</div>'
    if '4K' in quality or '2160P' in quality: badges_html += '<div class="badge badge-4k">4K UHD</div>'
    badges_html += '<div class="badge">Dolby 5.1</div><div class="badge">HEVC</div>'

    server_list_html = ""
    if not links:
        server_list_html = '<div style="color: #ff5252; text-align: center; padding: 15px; background: rgba(255,0,0,0.1); border-radius: 8px;">⚠️ দুঃখিত! ডাটাবেসে সেভ না হওয়ায় লিংক তৈরি হয়নি।</div>'
    elif is_batch and post_id:
        tg_url = links[0].get("tg_url", "")
        base_url = tg_url.split("?start=")[0] if "?start=" in tg_url else "https://t.me/getnewlink11"
        batch_link = f"{base_url}?start=batch-{post_id}"
        batch_b64 = base64.b64encode(batch_link.encode('utf-8')).decode('utf-8')
        file_count = len(links)
        
        server_list_html = f'''
        <div class="quality-title" style="border-left-color:#00e676;">📁 EPISODES / BATCH FILES</div>
        <div class="server-grid" style="display: flex; justify-content: center; width: 100%;">
            <div class="rgb-btn-wrapper" style="width: 100%; max-width: 500px;">
                <button class="rgb-btn" onclick="goToLink('{batch_b64}')">
                    <div style="font-size:15px; font-weight:bold; color:var(--text-main); margin-bottom:5px;">🎬 📦 All Episodes Batch ({file_count} Files)</div>
                    <div style="font-size:12px; color:#00e676; font-weight:bold;">⬇️ Get File</div>
                </button>
            </div>
        </div>
        '''
    else:
        grouped_links = {}
        for link in links:
            lbl = link.get('label', 'Download Link')
            if lbl not in grouped_links: grouped_links[lbl] = []
            grouped_links[lbl].append(link)

        for lbl, grp in grouped_links.items():
            server_list_html += f'<div class="quality-title">📺 {lbl}</div>\n<div class="server-grid">\n'
            for link in grp:
                if link.get("is_grouped") and link.get("tg_url"):
                    tg_b64 = base64.b64encode(link['tg_url'].encode('utf-8')).decode('utf-8')
                    server_list_html += f'''
                    <div class="rgb-btn-wrapper">
                        <button class="rgb-btn" onclick="goToLink('{tg_b64}')">
                            <div style="font-size:14px; font-weight:bold; color:var(--text-main); margin-bottom:3px;">⬇️ Download {lbl}</div>
                            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; background:rgba(0,0,0,0.5); border-radius:4px; padding:2px 5px; display:inline-block;">Telegram Server</div>
                        </button>
                    </div>'''
                else:
                    url_str = link.get('url', '')
                    if url_str:
                        encoded_url = base64.b64encode(url_str.encode('utf-8')).decode('utf-8')
                        server_list_html += f'''
                        <div class="rgb-btn-wrapper">
                            <button class="rgb-btn" onclick="goToLink('{encoded_url}')">
                                <div style="font-size:14px; font-weight:bold; color:var(--text-main); margin-bottom:3px;">⬇️ Direct Link</div>
                                <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; background:rgba(0,0,0,0.5); border-radius:4px; padding:2px 5px; display:inline-block;">Direct Server</div>
                            </button>
                        </div>'''
            server_list_html += '</div>\n'

    weighted_ad_list =[]
    if not user_ad_links_list: weighted_ad_list = owner_ad_links_list if owner_ad_links_list else["https://google.com"]
    elif not owner_ad_links_list: weighted_ad_list = user_ad_links_list
    else:
        for _ in range(int(admin_share_percent)): weighted_ad_list.append(random.choice(owner_ad_links_list))
        for _ in range(100 - int(admin_share_percent)): weighted_ad_list.append(random.choice(user_ad_links_list))
    random.shuffle(weighted_ad_list) 

    clean_desc = overview.replace('"', "'").replace('\n', ' ')

    return f"""
    <!-- 🛡️ Anti-AdBlock Script -->
    <script>
    async function detectAdBlock() {{
      let adBlockEnabled = false;
      const googleAdUrl = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js';
      try {{ await fetch(new Request(googleAdUrl)).catch(_ => adBlockEnabled = true); }} catch (e) {{ adBlockEnabled = true; }}
      if (adBlockEnabled) {{
        document.body.innerHTML = `
        <div style="position:fixed;top:0;left:0;width:100%;height:100%;background:#0f0f13;z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-family:sans-serif;text-align:center;padding:20px;">
            <h1 style="color:#ff5252;font-size:50px;">🚫</h1>
            <h2>Ad-Blocker Detected!</h2>
            <p style="color:#aaa;max-width:400px;">আমাদের সার্ভার খরচ চালানোর জন্য বিজ্ঞাপনের প্রয়োজন। দয়া করে আপনার <b>Ad-Blocker</b> বন্ধ করে পেজটি রিফ্রেশ দিন।</p>
            <button onclick="window.location.reload()" style="background:#E50914;color:#fff;border:none;padding:12px 25px;border-radius:5px;cursor:pointer;font-weight:bold;margin-top:20px;font-size:16px;">আমি বন্ধ করেছি, রিফ্রেশ দিন!</button>
        </div>`;
      }}
    }}
    window.onload = function() {{ detectAdBlock(); }};
    </script>

    <!-- Hidden tags for Blogger SEO & Preview -->
    <div style="height:0px;width:0px;overflow:hidden;visibility:hidden;display:none;float:left;">
        <img src="{poster}" alt="{title} Thumbnail" />
    </div>
    <div style="display:none;font-size:1px;color:rgba(0,0,0,0);line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
        🎬 {title} - {clean_desc[:100]}... Download now in High Quality.
    </div>

    <!-- 💎 Single Clean Schema.org Data -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Movie",
      "name": "{title}",
      "image": "{poster}",
      "description": "{clean_desc[:150]}",
      "aggregateRating": {{
        "@type": "AggregateRating",
        "ratingValue": "{rating}",
        "bestRating": "10",
        "ratingCount": "150"
      }}
    }}
    </script>

    <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {{ {root_css} }}
        body {{ margin: 0; padding: 0; background: var(--bg-color) !important; background-image: linear-gradient(to bottom, rgba(5,6,10,0.85), var(--bg-color)), url('{bg_url}') !important; background-attachment: fixed !important; background-size: cover !important; background-position: center !important; font-family: 'Poppins', sans-serif; }}
        
        .app-wrapper {{ max-width: 800px; margin: 20px auto; background: var(--box-bg); border-radius: 20px; padding: 25px; color: var(--text-main); border: 1px solid var(--border); box-shadow: 0 20px 50px rgba(0,0,0,0.9); position: relative; overflow: visible !important; }}
        
        .movie-title {{ font-family: 'Oswald', sans-serif; font-size: 35px; font-weight: bold; color: var(--text-main); text-align: center; text-transform: uppercase; margin-bottom: 30px; background: linear-gradient(to right, #fff 20%, #777 80%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; }}
        
        .media-badges {{ display: flex; gap: 8px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }}
        .badge {{ background: var(--primary); color: #fff; font-size: 11px; padding: 3px 10px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; box-shadow: var(--btn-shadow); border: 1px solid rgba(255,255,255,0.2); }}
        .badge-4k {{ color: #ffd700; border-color: #ffd700; background: rgba(255,255,255,0.1); }}
        .badge-hdr {{ color: #00d1b2; border-color: #00d1b2; background: rgba(255,255,255,0.1); }}
        
        .info-box {{ display: flex; flex-direction: column; align-items: center; gap: 20px; margin-bottom: 25px; background: rgba(255,255,255,0.03) !important; border-radius: 20px !important; padding: 25px !important; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05) !important; }}
        .info-poster img { width: 180px; height: 270px; object-fit: cover; border-radius: 15px; box-shadow: var(--btn-shadow); border: 2px solid rgba(255,255,255,0.1) !important; transition: 0.5s; }
        .info-poster img:hover {{ transform: scale(1.05) translateY(-10px); }}
        
        .info-text {{ display: flex; flex-direction: column; gap: 12px; width: 100%; max-width: 400px; margin: 0 auto; }}
        .info-text div {{ background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px; font-size: 16px; font-weight: 600; color: var(--text-main); border: 1px solid var(--border); text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
        .info-text span {{ display: block; color: var(--primary); font-size: 12px; text-transform: uppercase; font-weight: bold; margin-bottom: 5px; letter-spacing: 1.5px; }}
        
        .section-title {{ font-size: 16px; color: var(--text-main); margin: 25px 0 15px; border-bottom: 2px solid var(--primary); display: inline-block; padding-bottom: 4px; font-weight: 600; text-transform: uppercase; }}
        .plot-box {{ background: rgba(0,0,0,0.1); padding: 15px; border-radius: 8px; font-size: 13px; line-height: 1.7; color: var(--text-muted); border: 1px solid var(--border); text-align: justify; }}
        
        /* 🔥 Bangla Guide CSS */
        .guide-container {{ background: rgba(229, 9, 20, 0.05); border: 2px dashed var(--primary); border-radius: 15px; padding: 20px; margin: 25px 0; font-family: 'Poppins', sans-serif; text-align: left; color: #fff; animation: borderPulse 2s infinite; }}
        .guide-header {{ color: var(--primary); font-weight: bold; font-size: 18px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }}
        .step {{ display: flex; gap: 15px; margin-bottom: 12px; align-items: flex-start; }}
        .step-num {{ background: var(--primary); color: #fff; min-width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; flex-shrink: 0; margin-top: 2px; box-shadow: var(--btn-shadow); }}
        .step-text {{ font-size: 14px; line-height: 1.5; color: var(--text-muted); }}
        .step-text b {{ color: #ffeb3b; }}
        @keyframes borderPulse {{ 0% {{ border-color: var(--primary); }} 50% {{ border-color: #ff5252; }} 100% {{ border-color: var(--primary); }} }}

        .step-container {{ background: rgba(0,0,0,0.2); padding: 25px; border-radius: 12px; text-align: center; border: 1px solid var(--border); position: relative; overflow: hidden; }}
        .step-title {{ color: var(--primary); font-size: 14px; font-weight: 600; letter-spacing: 1px; margin-bottom: 15px; text-transform: uppercase; }}
        .unlock-btn {{ background: var(--primary); color: #fff; border: none; padding: 15px 20px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; width: 100%; box-shadow: var(--btn-shadow); }}
        .unlock-btn:disabled {{ background: #555 !important; filter: brightness(0.8); cursor: not-allowed; box-shadow: none; }}
        
        #glow-bar {{ position: absolute; bottom: 0; left: 0; height: 100%; width: 0%; background: rgba(255, 255, 255, 0.2); box-shadow: inset 0 0 20px rgba(255,255,255,0.5); transition: width {wait_timer_seconds}s linear; z-index: 1; }}

        .quality-title {{ background: rgba(0,0,0,0.2); border-left: 4px solid var(--primary); border-radius: 4px; padding: 10px 15px; font-size: 14px; font-weight: bold; color: var(--text-main); margin-top: 25px; text-transform: uppercase; border: 1px solid var(--border); }}
        .server-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }} 
        
        .rgb-btn-wrapper {{ position: relative; border-radius: 8px; padding: 2px; background: linear-gradient(45deg, #ff0000, #ff7300, #fffb00, #48ff00, #00ffd5, #002bff, #7a00ff, #ff00c8, #ff0000); background-size: 400%; animation: glowing 20s linear infinite; }}
        .rgb-btn {{ background: #1a1c22 !important; width: 100%; height: 100%; border: none; border-radius: 6px; padding: 15px; cursor: pointer; transition: 0.3s; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
        .rgb-btn:hover {{ background: var(--primary) !important; filter: brightness(1.2); transform: translateY(-5px); box-shadow: var(--btn-shadow); }}
        
        @keyframes glowing {{ 0% {{ background-position: 0 0; }} 50% {{ background-position: 400% 0; }} 100% {{ background-position: 0 0; }} }}
        .nsfw-blur {{ filter: blur(25px) !important; }}
    </style>

    <div class="app-wrapper">
        <div id="view-details">
            <div class="media-badges">
                {badges_html}
            </div>
            
            <div class="movie-title">{title}</div>
            
            <div class="info-box">
                <div class="info-poster">
                    <img src="{poster}" alt="Poster" class="{'nsfw-blur' if is_adult else ''}">
                </div>
                <div class="info-text">
                    <div><span>⭐ Rating:</span> {rating}/10</div>
                    <div><span>🎭 Genre:</span> {genres_str}</div>
                    <div><span>🗣️ Language:</span> {lang_str}</div>
                    <div><span>⏱️ Runtime:</span> {runtime_str}</div>
                    <div><span>📅 Release:</span> {year}</div>
                    <div><span>👥 Cast:</span> {cast_names}</div>
                </div>
            </div>
            
            <div class="section-title">📖 Storyline</div>
            <div class="plot-box">{overview}</div>

            <div class="guide-container">
                <div class="guide-header">🎬 মুভিটি কিভাবে দেখবেন বা ডাউনলোড করবেন?</div>
                <div class="step"><div class="step-num">১</div><div class="step-text">নিচের <b>"STEP 1"</b> বাটনে ক্লিক করুন এবং <b>{wait_timer_seconds} সেকেন্ড</b> অপেক্ষা করুন।</div></div>
                <div class="step"><div class="step-num">২</div><div class="step-text">বাটনে ক্লিক করলে একটি বিজ্ঞাপন (Ad) ওপেন হতে পারে, সেটি কেটে দিয়ে <b>এই পেজেই ফিরে আসুন</b>।</div></div>
                <div class="step"><div class="step-num">৩</div><div class="step-text">এরপর বাটনটি সবুজ হয়ে <b>STEP 2</b> লেখা আসবে, সেখানে ক্লিক করে আবার <b>{wait_timer_seconds} সেকেন্ড</b> অপেক্ষা করুন।</div></div>
                <div class="step"><div class="step-num">৪</div><div class="step-text">টাইমার শেষ হলে অটোমেটিক নিচের দিকে <b>সার্ভার লিস্ট এবং প্লেয়ার</b> খুলে যাবে। সেখানে ক্লিক করে হাই-স্পিডে মুভি উপভোগ করুন!</div></div>
                <div style="font-size: 12px; color: #888; margin-top: 10px; text-align: center; font-style: italic;">⚠️ যদি কোনো লিংক কাজবিধা না করে, তবে টেলিগ্রাম গ্রুপে রিপোর্ট করুন।</div>
            </div>

            <div class="step-container" id="step-box">
                <div class="step-title" id="st-txt">STEP 1: VERIFICATION</div>
                <button class="unlock-btn" id="st-btn" onclick="processUnlock()">🔓 UNLOCK LINK (STEP 1)</button>
            </div>
        </div>

        <div id="view-links" style="display:none;">
            <div style="text-align:center; color:#00e676; font-size:15px; font-weight:bold; margin-bottom:25px; border:1px solid rgba(0,230,118,0.3); padding:15px; border-radius:8px; background:rgba(0,230,118,0.05);">✅ ALL LINKS UNLOCKED SUCCESSFULLY!</div>
            
            {server_list_html}

            <div style="margin-top: 40px; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-size: 14px; color: #fff; margin-bottom: 15px; font-weight: 600;">🔗 মুভিটি বন্ধুদের সাথে শেয়ার করুন:</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <a href="https://t.me/getnewlink11" target="_blank" style="background: #0088cc; color: white; padding: 12px; border-radius: 8px; text-decoration: none; text-align: center; font-size: 14px; font-weight: bold;">✈️ Telegram</a>
                    <a href="whatsapp://send?text=Visit%20Our%20Website" target="_blank" style="background: #25D366; color: white; padding: 12px; border-radius: 8px; text-decoration: none; text-align: center; font-size: 14px; font-weight: bold;">💬 WhatsApp</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=https://t.me/getnewlink11" target="_blank" style="background: #1877F2; color: white; padding: 12px; border-radius: 8px; text-decoration: none; text-align: center; font-size: 14px; font-weight: bold;">📘 Facebook</a>
                    <button onclick="navigator.clipboard.writeText(window.location.href); alert('লিংক কপি হয়েছে!');" style="background: #555; border: none; color: white; padding: 12px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold; font-family: 'Poppins', sans-serif;">🔗 Copy Link</button>
                </div>
            </div>
            
        </div>
    </div>

    <script>
    const AD_LINKS = {json.dumps(weighted_ad_list)};
    let currentStep = 1;
    let waitSeconds = {wait_timer_seconds};

    function processUnlock() {{
        let btn = document.getElementById('st-btn');
        let title = document.getElementById('st-txt');
        
        let randomAd = AD_LINKS[Math.floor(Math.random() * AD_LINKS.length)];
        window.open(randomAd, '_blank');
        
        if (currentStep === 1) {{
            btn.disabled = true;
            btn.style.position = 'relative';
            btn.style.overflow = 'hidden';
            btn.innerHTML = `<span style="position:relative; z-index:2;">⏳ Verifying... Please Wait ${{waitSeconds}}s</span><div id="glow-bar"></div>`;
            
            setTimeout(() => {{ let bar = document.getElementById('glow-bar'); if(bar) bar.style.width = '100%'; }}, 50);
            
            setTimeout(() => {{
                currentStep = 2;
                btn.disabled = false;
                btn.style.background = "#00e676";
                btn.style.boxShadow = "0 5px 15px rgba(0, 230, 118, 0.4)";
                btn.innerHTML = "🔓 FINAL UNLOCK (STEP 2)";
                title.innerHTML = "STEP 2: FINAL VERIFICATION";
                title.style.color = "#00e676";
            }}, waitSeconds * 1000);
            
        }} else if (currentStep === 2) {{
            btn.disabled = true;
            btn.innerHTML = `<span style="position:relative; z-index:2;">⏳ Finalizing Request...</span><div id="glow-bar" style="width:0%;"></div>`;
            
            setTimeout(() => {{ let bar = document.getElementById('glow-bar'); if(bar) bar.style.width = '100%'; }}, 50);
            
            setTimeout(() => {{
                document.getElementById('view-details').style.display = 'none';
                document.getElementById('view-links').style.display = 'block';
                window.scrollTo({{top: 0, behavior: 'smooth'}});
            }}, waitSeconds * 1000);
        }}
    }}
    function goToLink(e) {{ window.location.href = atob(e); }}
    </script>
    """

def generate_formatted_caption(data, pid=None):
    title = data.get("title") or data.get("name") or "N/A"
    is_adult = data.get('adult', False) or data.get('force_adult', False)
    
    if data.get('is_manual'): year, rating, genres, language = "Custom", "⭐ N/A", "Custom", "N/A"
    else:
        year = (data.get("release_date") or data.get("first_air_date") or "----")[:4]
        rating = f"⭐ {data.get('vote_average', 0):.1f}/10"
        genres = ", ".join([g["name"] for g in data.get("genres",[])] or["N/A"])
        language = data.get('custom_language', '').title()
    
    overview = data.get("overview", "No plot available.")
    caption = f"🎬 **{title} ({year})**\n"
    if pid: caption += f"🆔 **ID:** `{pid}` (Use to Edit)\n\n"
    if is_adult: caption += "⚠️ **WARNING: 18+ Content.**\n_Suitable for mature audiences only._\n\n"
    if not data.get('is_manual'): caption += f"**🎭 Genres:** {genres}\n**🗣️ Language:** {language}\n**⭐ Rating:** {rating}\n\n"
    caption += f"**📝 Plot:** _{overview[:300]}..._\n\n⚠️ _Disclaimer: Informational post only._"

    tags = [
        f"{title} Full Movie Download", f"{title} {year} Dual Audio", 
        f"{title} {language} Download", f"{title} HD 1080p", 
        f"Download {title} Movie", "CineZoneBD1", "Banglaflix4k"
    ]
    caption += f"\n\n🏷️ **SEO Labels:**\n`{', '.join(tags)}`"
    
    return caption

def generate_image(data):
    try:
        poster_url = data.get('manual_poster_url') or (f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get('poster_path') else None)
        if not poster_url: return None, None
            
        poster_bytes = requests.get(poster_url, timeout=10, verify=False).content
        is_adult = data.get('adult', False) or data.get('force_adult', False)
        if data.get('badge_text'): poster_bytes = apply_badge_to_poster(poster_bytes, data['badge_text']).getvalue()

        poster_img = Image.open(io.BytesIO(poster_bytes)).convert("RGBA").resize((400, 600))
        if is_adult: poster_img = poster_img.filter(ImageFilter.GaussianBlur(20))

        bg_img = Image.new('RGBA', (1280, 720), (10, 10, 20))
        backdrop = poster_img.resize((1280, 720))
        if data.get('backdrop_path') and not data.get('is_manual'):
            try: backdrop = Image.open(io.BytesIO(requests.get(f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}", timeout=10, verify=False).content)).convert("RGBA").resize((1280, 720))
            except: pass
            
        bg_img = Image.alpha_composite(backdrop.filter(ImageFilter.GaussianBlur(10)), Image.new('RGBA', (1280, 720), (0, 0, 0, 150))) 
        bg_img.paste(poster_img, (50, 60), poster_img)
        draw = ImageDraw.Draw(bg_img)
        
        title = data.get("title") or data.get("name")
        year = "" if data.get('is_manual') else (data.get("release_date") or data.get("first_air_date") or "----")[:4]
        draw.text((480, 80), f"{title} {year}", font=get_font(36, True), fill="white", stroke_width=1, stroke_fill="black")
        
        if not data.get('is_manual'):
            draw.text((480, 140), f"⭐ {data.get('vote_average', 0):.1f}/10", font=get_font(24), fill="#00e676")
            if is_adult: draw.text((480, 180), "⚠️ RESTRICTED CONTENT", font=get_font(18), fill="#FF5252")
            else: draw.text((480, 180), " | ".join([g["name"] for g in data.get("genres",[])]), font=get_font(18), fill="#00bcd4")
        
        overview = data.get("overview", "")
        y_text = 250
        for line in [overview[i:i+80] for i in range(0, len(overview), 80)][:6]:
            draw.text((480, y_text), line, font=get_font(24), fill="#E0E0E0")
            y_text += 30
            
        img_buffer = io.BytesIO()
        img_buffer.name = "poster.png"
        bg_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer, poster_bytes 
    except: return None, None
