# plugins/seo_and_timer.py
import __main__
import json

# --- 🏷️ SEO KEYWORDS GENERATOR ---
def generate_seo_tags(data):
    title = data.get("title") or data.get("name")
    year = (data.get("release_date") or data.get("first_air_date") or "----")[:4]
    lang = data.get('custom_language', 'Dual Audio')
    
    tags = [
        f"{title} Full Movie Download", f"{title} {year} Dual Audio", 
        f"{title} {lang} Download", f"{title} HD 1080p", 
        f"Download {title} Movie", "CineZoneBD1", "Banglaflix4k"
    ]
    return ", ".join(tags)

# --- ⏳ GLOWING ANIMATED TIMER SCRIPT ---
def get_animated_timer_js():
    return """
    <style>
    /* টাইমার গ্লোয়িং বার ডিজাইন */
    #glow-bar {
        position: absolute; bottom: 0; left: 0; height: 100%; width: 0%; 
        background: rgba(255, 255, 255, 0.2); 
        box-shadow: inset 0 0 20px rgba(255,255,255,0.5);
        transition: width 5s linear; z-index: 1;
    }
    .main-btn:disabled { filter: brightness(0.8); cursor: not-allowed; }
    </style>
    
    <script>
    /* অরিজিনাল ফাংশনকে ওভাররাইড করা (নিরাপদ পদ্ধতি) */
    function startUnlock(btn, type) {
        let randomAd = AD_LINKS[Math.floor(Math.random() * AD_LINKS.length)];
        window.open(randomAd, '_blank'); 
        
        btn.disabled = true;
        btn.style.position = 'relative';
        btn.style.overflow = 'hidden';
        
        btn.innerHTML = `
            <span style="position:relative; z-index:2;">⏳ SECURING LINK...</span>
            <div id="glow-bar"></div>
        `;

        let timeLeft = 5;
        let timer = setInterval(function() {
            timeLeft--;
            if (timeLeft < 0) {
                clearInterval(timer);
                document.getElementById('view-details').style.display = 'none';
                document.getElementById('view-links').style.display = 'block';
                window.scrollTo({top: 0, behavior: 'smooth'});
            }
        }, 1000);

        setTimeout(() => { 
            let bar = document.getElementById('glow-bar');
            if(bar) bar.style.width = '100%'; 
        }, 50);
    }
    </script>
    """

# ==========================================================
# 🔥 SAFE PATCHING (কোনো ডাটা মুছবে না)
# ==========================================================

# ১. HTML জেনারেটর ফিক্স (শুধু শেষে কোড যোগ করবে)
if not hasattr(__main__, 'old_html_func'):
    __main__.old_html_func = __main__.generate_html_code

def safe_timer_generator(data, links, user_ads, owner_ads, share):
    # আগের সব প্লাগইন এবং মেইন কোড থেকে HTML নেওয়া
    html = __main__.old_html_func(data, links, user_ads, owner_ads, share)
    
    # এর শেষে শুধু নতুন টাইমার স্ক্রিপ্টটি যোগ করা (রিপ্লেস করবে না)
    # এতে কোনো ডাটা হারানো বা পেজ খালি হওয়ার ভয় নেই
    return f"{html}\n{get_animated_timer_js()}"

__main__.generate_html_code = safe_timer_generator


# ২. ক্যাপশন জেনারেটর ফিক্স (SEO ট্যাগ যোগ করবে)
if not hasattr(__main__, 'old_caption_func'):
    __main__.old_caption_func = __main__.generate_formatted_caption

def safe_seo_caption(data, pid=None):
    # অরিজিনাল ক্যাপশন নেওয়া
    caption = __main__.old_caption_func(data, pid)
    # ট্যাগ জেনারেট করা
    tags = generate_seo_tags(data)
    # ক্যাপশনের নিচে ট্যাগগুলো জুড়ে দেওয়া
    return f"{caption}\n\n🏷️ **SEO Labels:**\n`{tags}`"

__main__.generate_formatted_caption = safe_seo_caption

async def register(bot):
    print("✅ SEO & Timer Plugin Fixed & Activated Safely!")
