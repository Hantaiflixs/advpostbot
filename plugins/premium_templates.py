# plugins/premium_templates.py
import __main__
import base64
import json

# --- 💎 ADVANCED CSS OVERRIDE (প্রিমিয়াম ডিজাইন লাইব্রেরি) ---
def get_premium_css(theme):
    # সব থিমের জন্য কমন আধুনিক সিএসএস
    base_style = """
    <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; background: #000; }
        .app-wrapper { 
            font-family: 'Poppins', sans-serif !important; 
            max-width: 800px !important; 
            background: #0f1014 !important; 
            border: none !important; 
            box-shadow: 0 20px 50px rgba(0,0,0,0.9) !important;
            border-radius: 20px !important;
            position: relative;
            overflow: visible !important;
        }
        
        /* 🔥 মুভি টাইটেল অ্যানিমেশন */
        .movie-title { 
            font-family: 'Oswald', sans-serif !important;
            font-size: 35px !important; 
            background: linear-gradient(to right, #fff 20%, #777 80%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
            margin-bottom: 30px !important;
        }

        /* 🖼️ পোস্টার গ্লো ইফেক্ট */
        .info-poster img { 
            width: 180px !important;
            border-radius: 15px !important; 
            box-shadow: 0 10px 30px rgba(229, 9, 20, 0.4) !important;
            border: 2px solid rgba(255,255,255,0.1) !important;
            transition: 0.5s;
        }
        .info-poster img:hover { transform: scale(1.05) translateY(-10px); }

        /* 📊 ইনফো বক্স গ্রিড */
        .info-box { 
            background: rgba(255,255,255,0.03) !important;
            border-radius: 20px !important;
            padding: 25px !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.05) !important;
        }
        .info-text div { margin-bottom: 8px !important; font-size: 15px !important; }
        .info-text span { color: #E50914 !important; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; }

        /* 📥 প্রিমিয়াম সার্ভার কার্ডস (বাটন নয়, কার্ড) */
        .quality-title { 
            background: linear-gradient(90deg, #E50914, transparent) !important;
            border: none !important;
            border-radius: 5px !important;
            padding: 10px 20px !important;
            font-size: 14px !important;
            color: #fff !important;
        }
        .server-grid { gap: 15px !important; margin-top: 15px !important; }
        .final-server-btn { 
            background: #1a1c22 !important; 
            border: 1px solid #333 !important; 
            border-radius: 12px !important;
            padding: 15px !important;
            font-size: 13px !important;
            transition: 0.3s !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            height: auto !important;
        }
        .final-server-btn:hover { 
            background: #E50914 !important; 
            border-color: #E50914 !important; 
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(229, 9, 20, 0.3) !important;
        }
    </style>
    """
    
    # থিম অনুযায়ী বাড়তি কালার যোগ করা
    if theme == "prime":
        return base_style + "<style>.info-poster img{box-shadow: 0 10px 30px rgba(0, 168, 225, 0.4) !important;} .info-text span, .quality-title, .final-server-btn:hover{background:#00A8E1 !important; color:#fff !important;}</style>"
    elif theme == "light": # এটি এখন 'Glow Pink' থিম হবে
        return base_style + "<style>.info-poster img{box-shadow: 0 10px 30px rgba(255, 121, 198, 0.4) !important;} .info-text span, .quality-title, .final-server-btn:hover{background:#ff79c6 !important; color:#fff !important;}</style>"
    
    return base_style

# ==========================================================
# 🔥 MONKEY PATCH: HTML GENERATOR (অ্যাডভান্সড লেভেল)
# ==========================================================

# মেইন জেনারেটর ফাংশনটিকে হাইজ্যাক করা
original_html_func = __main__.generate_html_code

def premium_html_generator(data, links, user_ads, owner_ads, share):
    # বেসিক HTML নেওয়া (মেইন কোড থেকে)
    html = original_html_func(data, links, user_ads, owner_ads, share)
    
    # প্রিমিয়াম সিএসএস এবং এসইও ডাটা তৈরি
    theme = data.get("theme", "netflix")
    premium_css = get_premium_css(theme)
    
    # এসইও স্কিমা (গুগল র‍্যাঙ্কিং এর জন্য)
    title = data.get("title") or data.get("name")
    poster = data.get('manual_poster_url') or f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}"
    schema = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "name": title,
        "image": poster,
        "description": data.get("overview", "Download now")[:160]
    }
    schema_code = f'<script type="application/ld+json">{json.dumps(schema)}</script>'
    
    # মেইন HTML এর ভেতরে প্রিমিয়াম সিএসএস এবং স্কিমা ইনজেক্ট করা
    # এটি আপনার ওয়েবসাইটের সাধারণ লুককে পুরোপুরি বদলে দেবে
    return f"{schema_code}\n{premium_css}\n{html}"

# মেইন স্ক্রিপ্টের জেনারেটর রিপ্লেস করা
__main__.generate_html_code = premium_html_generator

async def register(bot):
    print("💎 Premium Templates (Advanced UX): Activated!")

print("✅ Premium Template Plugin Loaded!")
