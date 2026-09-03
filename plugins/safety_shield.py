# -*- coding: utf-8 -*-
import __main__
import requests
import logging

logger = logging.getLogger(__name__)

# --- API Keys ---
IMGBB_API_KEY = "1821270072482fb07921cfd72d31c37e" # যদি নতুন Key নেন, তবে এখানে বসাবেন
FREEIMAGE_API_KEY = "6d207e02198a847aa98d0a2a901485a5" # Public Key (No Sign-up)
IMGUR_CLIENT_ID = "546c25a59c58ad7" # Public Imgur Key (No Sign-up)

# ==========================================
# ১. মেইন সার্ভার: Freeimage.host (Fastest on Koyeb)
# ==========================================
def upload_to_freeimage(file_content):
    try:
        url = "https://freeimage.host/api/1/upload"
        data = {"key": FREEIMAGE_API_KEY}
        files = {"source": ("poster.png", file_content)}
        resp = requests.post(url, data=data, files=files, timeout=15)
        if resp.status_code == 200:
            return resp.json()['image']['url']
        else:
            logger.warning(f"⚠️ Freeimage API Error: {resp.text}")
    except Exception as e:
        logger.warning(f"[!] Freeimage Error: {e}")
    return None

# ==========================================
# ২. ব্যাকআপ ১: Imgur (World's Best, No Sign-up)
# ==========================================
def upload_to_imgur(file_content):
    try:
        url = "https://api.imgur.com/3/image"
        headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
        files = {"image": ("poster.png", file_content, "image/png")}
        resp = requests.post(url, headers=headers, files=files, timeout=15)
        if resp.status_code == 200:
            return resp.json()['data']['link']
        else:
            logger.warning(f"⚠️ Imgur API Error: {resp.text}")
    except Exception as e:
        logger.warning(f"[!] Imgur Error: {e}")
    return None

# ==========================================
# ৩. ব্যাকআপ ২: Pixeldrain (Cloud Friendly)
# ==========================================
def upload_to_pixeldrain(file_content):
    try:
        url = "https://pixeldrain.com/api/file"
        files = {"file": ("poster.png", file_content, "image/png")}
        resp = requests.post(url, files=files, timeout=15)
        if resp.status_code in [200, 201]:
            data = resp.json()
            if data.get("success"):
                return f"https://pixeldrain.com/api/file/{data['id']}"
        else:
            logger.warning(f"⚠️ Pixeldrain API Error: {resp.text}")
    except Exception as e:
        logger.warning(f"[!] Pixeldrain Error: {e}")
    return None

# ==========================================
# ৪. ব্যাকআপ ৩: ImgBB (User's API Key Fallback)
# ==========================================
def upload_to_imgbb(file_content):
    try:
        url = "https://api.imgbb.com/1/upload"
        data = {"key": IMGBB_API_KEY}
        files = {"image": ("poster.png", file_content)}
        resp = requests.post(url, data=data, files=files, timeout=10)
        if resp.status_code == 200:
            return resp.json()['data']['url']
        else:
            logger.warning(f"⚠️ ImgBB API Error [{resp.status_code}]: {resp.text}")
    except Exception as e:
        logger.warning(f"[!] ImgBB Error: {e}")
    return None

# ==========================================
# 🚀 ব্রেইন / ফলব্যাক কন্ট্রোলার (The Core)
# ==========================================
def smart_upload_core(file_content):
    """এটি ক্লাউড ফ্রেন্ডলি সার্ভারগুলোতে পর্যায়ক্রমে চেষ্টা করবে"""
    
    # Step 1: Freeimage
    img_url = upload_to_freeimage(file_content)
    if img_url:
        logger.info("✅ Uploaded via Freeimage")
        return img_url
        
    # Step 2: Imgur
    logger.info("⚠️ Freeimage Failed! Trying Imgur...")
    img_url = upload_to_imgur(file_content)
    if img_url:
        logger.info("✅ Uploaded via Imgur")
        return img_url

    # Step 3: Pixeldrain
    logger.info("⚠️ Imgur Failed! Trying Pixeldrain...")
    img_url = upload_to_pixeldrain(file_content)
    if img_url:
        logger.info("✅ Uploaded via Pixeldrain")
        return img_url
        
    # Step 4: ImgBB
    logger.info("⚠️ Pixeldrain Failed! Trying ImgBB...")
    if IMGBB_API_KEY != "YOUR_NEW_IMGBB_API_KEY":
        img_url = upload_to_imgbb(file_content)
        if img_url:
            logger.info("✅ Uploaded via ImgBB")
            return img_url
    else:
        logger.warning("⚠️ ImgBB skipped (API Key is missing).")
    
    # যদি ৪টাই ফেইল করে
    logger.error("❌ All Image Servers are DOWN!")
    return None

# ==========================================
# প্লাগিন রিপ্লেসমেন্ট ফাংশন
# ==========================================
def patched_upload_to_catbox(file_path):
    with open(file_path, "rb") as f:
        return smart_upload_core(f.read())

def patched_upload_to_catbox_bytes(img_bytes):
    if hasattr(img_bytes, 'read'):
        img_bytes.seek(0)
        return smart_upload_core(img_bytes.read())
    return smart_upload_core(img_bytes)

# =======================================================
# 🚀 PLUGIN REGISTER
# =======================================================
async def register(bot):
    __main__.upload_to_catbox = patched_upload_to_catbox
    __main__.upload_to_catbox_bytes = patched_upload_to_catbox_bytes
    __main__.upload_image_core = smart_upload_core
    
    print("🚀 [PLUGIN] Ultimate 4-Layer Backup (Freeimage -> Imgur -> Pixeldrain -> ImgBB) Activated!")
