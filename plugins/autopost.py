import __main__
import asyncio
import re
import aiohttp
import logging
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError, FloodWait, ChatAdminRequired, PeerIdInvalid, UsernameNotOccupied

# মেইন ফাইল থেকে ডাটাবেস কালেকশন নেওয়া
db = __main__.db
user_setup_col = db["user_autopost_configs"]
logger = logging.getLogger(__name__)

# --- হেল্পার ফাংশনস ---

def is_valid_url(url):
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])

def extract_info_from_blog(content):
    if not content:
        return {'rating': 'N/A', 'genres': 'Movie', 'lang': 'Dual Audio', 'runtime': 'N/A', 'year': 'N/A'}
    text = re.sub(r'<[^>]+>', ' ', content)
    info = {}
    rating = re.search(r'RATING:\s*([\d\./]+)', text, re.I)
    genre = re.search(r'GENRE:\s*([^📅🗣⏱]+)', text, re.I)
    lang = re.search(r'LANGUAGE:\s*([^📅🎭⏱]+)', text, re.I)
    runtime = re.search(r'RUNTIME:\s*([\d\s\w]+)', text, re.I)
    year = re.search(r'RELEASE:\s*(\d{4})', text, re.I)
    info['rating'] = rating.group(1).strip() if rating else "N/A"
    info['genres'] = genre.group(1).strip() if genre else "Movie"
    info['lang'] = lang.group(1).strip() if lang else "Dual Audio"
    info['runtime'] = runtime.group(1).strip() if runtime else "N/A"
    info['year'] = year.group(1).strip() if year else "N/A"
    return info

def get_caption(title, info):
    return (
        f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
        f"🎬 **NEW UPDATE: {title}**\n"
        f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"⭐️ **Rating:** {info['rating']}\n"
        f"🎭 **Genres:** {info['genres']}\n"
        f"📅 **Year:** {info['year']}\n"
        f"⏱ **Runtime:** {info['runtime']}\n"
        f"🗣 **Language:** {info['lang']}\n"
        f"💎 **Quality:** 480p | 720p | 1080p\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **ডাউনলোড করতে নিচের লিংকে ক্লিক করুন 👇**"
    )

# --- মূল প্লাগইন রেজিস্টার ---

async def register(bot):
    print("🎬 Professional Autopost System (v5.1 Fixed) Activated!")

    # --- ১. স্মার্ট রিপোস্ট কমান্ড ---
    @bot.on_message(filters.command("repost") & filters.private)
    async def smart_repost(client, message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                return await message.reply_text("⚠️ **ব্যবহার নিয়ম:** `/repost https://link.com`")
            
            input_link = parts[1].strip()
            status_msg = await message.reply_text("🌐 প্রসেসিং...")
            
            headers = {"User-Agent": "Mozilla/5.0"}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(input_link, timeout=15) as resp:
                    html = await resp.text()
                    title_match = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
                    title = title_match.group(1).split('|')[0].strip() if title_match else "Movie Update"
                    info = extract_info_from_blog(html)
                    img_match = re.search(r'<img.*?src="(.*?)"', html)
                    poster = img_match.group(1) if img_match else None
                    caption = get_caption(title, info)
                    
                    configs = await user_setup_col.find({"user_id": message.from_user.id}).to_list(None)
                    for cfg in configs:
                        btns = [[InlineKeyboardButton("🔗 Download Now", url=input_link)]]
                        try:
                            if poster: await client.send_photo(cfg['channel'], poster, caption=caption, reply_markup=InlineKeyboardMarkup(btns))
                            else: await client.send_message(cfg['channel'], caption, reply_markup=InlineKeyboardMarkup(btns))
                        except Exception as e:
                            logger.error(f"Manual Repost Error: {e}")

            await status_msg.edit("✅ রিপোস্ট করা হয়েছে!")
        except Exception as e:
            await message.reply_text(f"❌ এরর: {e}")

    # --- ২. সেটআপ কমান্ড ---
    @bot.on_message(filters.command("setup") & filters.private)
    async def setup_handler(client, message):
        parts = message.text.split(None, 3)
        if len(parts) < 4:
            return await message.reply_text("⚠️ `/setup @channel feed_url tutorial_url`")
        
        channel, feed, tutorial = parts[1], parts[2], parts[3]
        
        # চ্যানেল ভ্যালিডেশন চেক
        try:
            chat = await client.get_chat(channel)
            channel_id = chat.id 
        except:
            return await message.reply_text("❌ চ্যানেলটি খুঁজে পাওয়া যায়নি! বটকে চ্যানেলে এডমিন করুন এবং সঠিক ইউজারনেম দিন।")

        await user_setup_col.update_one(
            {"user_id": message.from_user.id, "channel": channel}, 
            {"$set": {"feed": feed, "tutorial": tutorial, "last_post_id": None, "is_active": True}},
            upsert=True
        )
        await message.reply_text(f"✅ **সেটআপ সফল!**\nচ্যানেল: {channel}")

    # --- ৫. অটো পোস্ট মনিটর (The Heart of Plugin) ---
    async def monitor_feeds():
        while True:
            try:
                # শুধুমাত্র active সেটআপগুলো চেক করবে
                configs = await user_setup_col.find({"is_active": {"$ne": False}}).to_list(None)
                async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
                    for config in configs:
                        target_chat = config.get("channel")
                        doc_id = config.get("_id")
                        f_url = config.get("feed")
                        
                        try:
                            async with session.get(f_url, timeout=10) as resp:
                                if resp.status != 200: continue
                                xml_data = await resp.text()
                                root = ET.fromstring(xml_data)
                                entry = root.find('{http://www.w3.org/2005/Atom}entry')
                                if entry is None: continue
                                
                                p_id = entry.find('{http://www.w3.org/2005/Atom}id').text
                                if p_id != config.get("last_post_id"):
                                    title = entry.find('{http://www.w3.org/2005/Atom}title').text
                                    link = entry.find('{http://www.w3.org/2005/Atom}link[@rel="alternate"]').attrib['href']
                                    content = entry.find('{http://www.w3.org/2005/Atom}content').text or ""
                                    
                                    info = extract_info_from_blog(content)
                                    img_match = re.search(r'<img.*?src="(.*?)"', content)
                                    poster = img_match.group(1) if img_match else None
                                    caption = get_caption(title, info)
                                    
                                    btns = [[InlineKeyboardButton("🔗 Download Now", url=link)]]
                                    if is_valid_url(config.get("tutorial")):
                                        btns.append([InlineKeyboardButton("📽️ How to Download", url=config.get("tutorial"))])

                                    try:
                                        if poster: await bot.send_photo(target_chat, poster, caption=caption, reply_markup=InlineKeyboardMarkup(btns))
                                        else: await bot.send_message(target_chat, caption, reply_markup=InlineKeyboardMarkup(btns))
                                        
                                        await user_setup_col.update_one({"_id": doc_id}, {"$set": {"last_post_id": p_id}})
                                        logger.info(f"✅ Auto-posted to {target_chat}")
                                    
                                    except (UsernameNotOccupied, PeerIdInvalid, ChatAdminRequired) as e:
                                        # 🔥 গোল্ডেন ফিক্স: যদি চ্যানেল খুঁজে না পায় বা বট এডমিন না হয়, তবে এই সেটআপ ডিজেবল করে দাও
                                        logger.warning(f"❌ Disabling bad setup {target_chat}: {e}")
                                        await user_setup_col.update_one({"_id": doc_id}, {"$set": {"is_active": False}})
                                    except FloodWait as e:
                                        await asyncio.sleep(e.value)
                                    except Exception as e:
                                        logger.error(f"Post Error: {e}")
                        except: continue
            except Exception as e:
                logger.error(f"Monitor Loop Error: {e}")
            await asyncio.sleep(60) # ১ মিনিট পর পর চেক করবে

    asyncio.create_task(monitor_feeds())
