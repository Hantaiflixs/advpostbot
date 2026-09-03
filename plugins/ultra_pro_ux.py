# plugins/ultra_pro_ux.py
import __main__
import base64
import json

# --- 🎭 CLEAN ULTRA UX (NO FLOATING BUTTONS) ---
async def register(bot):
    print("🚀 Ultra UX Clean Version Activated (Floating Buttons Removed)!")

def get_ux_footer_code(data):
    backdrop = data.get('backdrop_path')
    bg_url = f"https://image.tmdb.org/t/p/original{backdrop}" if backdrop else ""
    
    return f"""
    <style>
        /* 🌌 ইমারসিভ সিনেমাটিক ব্যাকগ্রাউন্ড */
        body {{ 
            background: #05060a !important; 
            background-image: linear-gradient(to bottom, rgba(5,6,10,0.8), #05060a), url('{bg_url}') !important;
            background-attachment: fixed !important;
            background-size: cover !important;
            background-position: center !important;
        }}
        
        /* 🏷️ মিডিয়া ব্যাজ ডিজাইন */
        .media-badges {{ display: flex; gap: 8px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }}
        .badge {{ background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; font-size: 11px; padding: 3px 10px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
        .badge-4k {{ color: #ffd700; border-color: #ffd700; }}
        .badge-hdr {{ color: #00d1b2; border-color: #00d1b2; }}
        
        /* ⏳ গ্লোয়িং প্রগ্রেস বার (বাটনের নিচে) */
        #unlock-timer {{ 
            width: 0%; height: 4px; background: linear-gradient(90deg, #E50914, #ff5252); 
            position: absolute; bottom: 0; left: 0; transition: width 5s linear; 
            box-shadow: 0 0 10px #E50914; 
        }}
    </style>
    
    <script>
    /* আনলক করার স্মার্ট টাইমার লজিক */
    function startUnlock(btn, type) {{
        let randomAd = AD_LINKS[Math.floor(Math.random() * AD_LINKS.length)];
        window.open(randomAd, '_blank'); 
        btn.style.position = 'relative';
        btn.innerHTML += '<div id="unlock-timer"></div>';
        btn.disabled = true;
        let timeLeft = 5;
        let timer = setInterval(function() {{
            btn.innerHTML = "⏳ UNLOCKING " + timeLeft + "s";
            if (timeLeft < 0) {{
                clearInterval(timer);
                document.getElementById('view-details').style.display = 'none';
                document.getElementById('view-links').style.display = 'block';
                window.scrollTo({{top: 0, behavior: 'smooth'}});
            }}
            timeLeft--;
        }}, 1000);
        setTimeout(() => {{ document.getElementById('unlock-timer').style.width = '100%'; }}, 10);
    }}
    </script>
    """

def blogger_friendly_generator(data, links, user_ads, owner_ads, share):
    # অরিজিনাল জেনারেটর কল করা
    html = original_html_generator(data, links, user_ads, owner_ads, share)
    
    title = data.get("title") or data.get("name")
    plot = data.get("overview", "")[:150]
    poster = data.get('manual_poster_url') or f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}"
    
    # ১. 🖼️ থাম্বনেইল ফিক্স (ব্লগার ড্যাশবোর্ডের জন্য)
    thumbnail_html = f'<div style="height:0px;width:0px;overflow:hidden;visibility:hidden;display:none;float:left;"><img src="{poster}" alt="{title} Thumbnail" /></div>'
    
    # ২. 📝 ইনভিজিবল স্নিপেট (সার্চ প্রিভিউ এর জন্য)
    preview_snippet = f'<div style="display:none;font-size:1px;color:rgba(0,0,0,0);line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">🎬 {title} - {plot}... Download now in High Quality.</div>'
    
    # ৩. 🏷️ মিডিয়া ব্যাজ (4K, HDR ইত্যাদি)
    quality = data.get('custom_quality', '').upper()
    badges_html = '<div class="media-badges">'
    badges_html += '<div class="badge">Dual Audio</div>'
    if '1080P' in quality: badges_html += '<div class="badge badge-hdr">1080p Full HD</div>'
    if '4K' in quality or '2160P' in quality: badges_html += '<div class="badge badge-4k">4K UHD</div>'
    badges_html += '<div class="badge">Dolby 5.1</div><div class="badge">HEVC</div></div>'
    
    # ৪. 💎 এসইও স্কিমা (গুগল র‍্যাঙ্কিং)
    schema_code = f'<script type="application/ld+json">{json.dumps({"@context": "https://schema.org","@type": "Movie","name": title,"image": poster,"description": plot})}</script>'
    
    # ৫. 🎨 সিএসএস এবং জেএস (যা নিচে থাকবে)
    footer_code = get_ux_footer_code(data)
    
    # ব্যাজগুলো মুভি টাইটেলের ঠিক নিচে বসানো
    html = html.replace('<div class="movie-title">', badges_html + '<div class="movie-title">')
    
    # বাটনগুলো সরিয়ে ক্লিন আউটপুট রিটার্ন করা
    return f"{thumbnail_html}\n{preview_snippet}\n{schema_code}\n{html}\n{footer_code}"

# মেইন জেনারেটর রিপ্লেস করা
original_html_generator = __main__.generate_html_code
__main__.generate_html_code = blogger_friendly_generator
