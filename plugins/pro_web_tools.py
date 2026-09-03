# plugins/pro_web_tools.py
import json
import base64
from pyrogram import filters
import __main__ # মেইন কোডকে এক্সেস করার জন্য

# --- 💎 SEO & SCHEMA MARKUP ---
def get_seo_schema(data):
    title = data.get("title") or data.get("name")
    poster = data.get('manual_poster_url') or f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}"
    overview = data.get("overview", "No plot available.")[:160]
    rating = data.get('vote_average', 0)
    schema = {"@context": "https://schema.org","@type": "Movie","name": title,"image": poster,"description": overview,"aggregateRating": {"@type": "AggregateRating","ratingValue": rating,"bestRating": "10","ratingCount": "150"}}
    return f'<script type="application/ld+json">{json.dumps(schema)}</script>'

# --- 🛡️ ANTI-ADBLOCK ---
def get_anti_adblock_js():
    return """
    <script>
    async function detectAdBlock() {
      let adBlockEnabled = false;
      const googleAdUrl = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js';
      try { await fetch(new Request(googleAdUrl)).catch(_ => adBlockEnabled = true); } catch (e) { adBlockEnabled = true; }
      if (adBlockEnabled) {
        document.body.innerHTML = `
        <div style="position:fixed;top:0;left:0;width:100%;height:100%;background:#0f0f13;z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-family:sans-serif;text-align:center;padding:20px;">
            <h1 style="color:#ff5252;font-size:50px;">🚫</h1>
            <h2>Ad-Blocker Detected!</h2>
            <p style="color:#aaa;max-width:400px;">আমাদের সার্ভার খরচ চালানোর জন্য বিজ্ঞাপনের প্রয়োজন। দয়া করে আপনার <b>Ad-Blocker</b> বন্ধ করে পেজটি রিফ্রেশ দিন।</p>
            <button onclick="window.location.reload()" style="background:#E50914;color:#fff;border:none;padding:12px 25px;border-radius:5px;cursor:pointer;font-weight:bold;margin-top:20px;font-size:16px;">আমি বন্ধ করেছি, রিফ্রেশ দিন!</button>
        </div>`;
      }
    }
    window.onload = function() { detectAdBlock(); };
    </script>
    """

# --- 🎨 NEW PREMIUM THEMES (CSS) ---
def get_enhanced_css(theme):
    if theme == "light": # Anime Pink Theme
        return """<style>
        :root { --bg-color: #1a1b26; --box-bg: #24283b; --text-main: #c0caf5; --primary: #ff79c6; --accent: #bb9af7; --border: #414868; --btn-grad: linear-gradient(90deg, #ff79c6 0%, #bd93f9 100%); }
        .app-wrapper { border-top: 5px solid var(--primary) !important; box-shadow: 0 0 50px rgba(255,121,198,0.2) !important; }
        .movie-title { font-family: 'Poppins', sans-serif; font-weight: 900 !important; letter-spacing: 1px; }
        </style>"""
    elif theme == "prime": # Futuristic Cyan Theme
        return """<style>
        :root { --bg-color: #050505; --box-bg: #111; --text-main: #eee; --primary: #00d1b2; --accent: #00d1b2; --border: #222; --btn-grad: linear-gradient(90deg, #00d1b2 0%, #00947e 100%); }
        .app-wrapper { border: 1px solid #00d1b2 !important; box-shadow: inset 0 0 20px rgba(0,209,178,0.1) !important; border-radius: 0px !important; }
        .main-btn { border: 1px solid var(--primary) !important; background: transparent !important; color: var(--primary) !important; }
        .main-btn:hover { background: var(--primary) !important; color: #000 !important; }
        </style>"""
    return ""

# ==========================================================
# 🔥 MONKEY PATCHING (মেইন কোড পরিবর্তন না করে আপডেট করার যাদু)
# ==========================================================

# মেইন কোডের অরিজিনাল ফাংশনটি কপি করে রাখা
original_generate_html = __main__.generate_html_code

def enhanced_html_code(data, links, user_ad_links_list, owner_ad_links_list, admin_share_percent=20):
    # অরিজিনাল কোড থেকে বেসিক HTML জেনারেট করা
    html = original_generate_html(data, links, user_ad_links_list, owner_ad_links_list, admin_share_percent)
    
    # নতুন ফিচারগুলো তৈরি করা
    seo_code = get_seo_schema(data)
    anti_adblock = get_anti_adblock_js()
    theme_css = get_enhanced_css(data.get("theme", "netflix"))
    
    # সবগুলো মিলিয়ে ফাইনাল কোড রিটার্ন করা
    return f"{seo_code}\n{theme_css}\n{anti_adblock}\n{html}"

# মেইন কোডের ফাংশনটিকে আমাদের নতুন ফাংশন দিয়ে রিপ্লেস করা
__main__.generate_html_code = enhanced_html_code

async def register(bot):
    # এই প্লাগইনে নতুন কোনো কমান্ডের প্রয়োজন নেই, এটি অটোমেটিক কাজ করবে
    print("💎 Pro Web Tools: Monkey Patch Applied Successfully!")

print("✅ Pro Web Tools Plugin Loaded!")
