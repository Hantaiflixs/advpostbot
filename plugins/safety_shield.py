# -*- coding: utf-8 -*-
import __main__
import requests
import logging

logger = logging.getLogger(__name__)

# --- API Keys ---
IMGBB_API_KEY = "1821270072482fb07921cfd72d31c37e"
FREEIMAGE_API_KEY = "6d207e02198a847aa98d0a2a901485a5" # এটি একটি পাবলিক API Key, যা ব্যাকআপ হিসেবে কাজ করবে

# ==========================================
# ১. মেইন সার্ভার: ImgBB
# ==========================================
def upload_to_imgbb(file_content):
    try:
        url = "https://api.imgbb.com/1/upload"
        data = {"key": IMGBB_API_KEY}
        files = {"image": ("image.png", file_content)}
        resp = requests.post(url, data=data, files=files, timeout=20)
        if resp.status_code == 200:
            return resp.json()['data']['url']
    except Exception as e:
        logger.warning(f"[!] ImgBB Error: {e}")
    return None

# ==========================================
# ২. ব্যাকআপ সার্ভার ১: Telegraph (No API Key)
# ==========================================
def upload_to_telegraph(file_content):
    try:
        url = "https://telegra.ph/upload"
        files = {"file": ("image.png", file_content, "image/png")}
        resp = requests.post(url, files=files, timeout=20)
        if resp.status_code == 200:
            return "https://telegra.ph" + resp.json()[0]['src']
    except Exception as e:
        logger.warning(f"[!] Telegraph Error: {e}")
    return None

# ==========================================
# ৩. ব্যাকআপ সার্ভার ২: Freeimage.host
# ==========================================
def upload_to_freeimage(file_content):
    try:
        url = "https://freeimage.host/api/1/upload"
        data = {"key": FREEIMAGE_API_KEY}
        files = {"source": ("image.png", file_content)}
        resp = requests.post(url, data=data, files=files, timeout=20)
        if resp.status_code == 200:
            return resp.json()['image']['url']
    except Exception as e:
        logger.warning(f"[!] Freeimage Error: {e}")
    return None


# ==========================================
# 🚀 ব্রেইন / ফলব্যাক কন্ট্রোলার (The Core)
# ==========================================
def smart_upload_core(file_content):
    """এটি পর্যায়ক্রমে ৩টি সার্ভারে চেষ্টা করবে"""
    
    # Step 1: ImgBB
    img_url = upload_to_imgbb(file_content)
    if img_url:
        logger.info("✅ Uploaded via ImgBB")
        return img_url
        
    # Step 2: Telegraph
    logger.info("⚠️ ImgBB Failed! Trying Telegraph...")
    img_url = upload_to_telegraph(file_content)
    if img_url:
        logger.info("✅ Uploaded via Telegraph")
        return img_url
        
    # Step 3: Freeimage
    logger.info("⚠️ Telegraph Failed! Trying Freeimage...")
    img_url = upload_to_freeimage(file_content)
    if img_url:
        logger.info("✅ Uploaded via Freeimage")
        return img_url
    
    # যদি ৩টাই ফেইল করে
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
    
    print("🚀 [PLUGIN] Triple Backup (ImgBB -> Telegraph -> Freeimage) Upload Engine Activated!")
