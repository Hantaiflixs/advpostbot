# -*- coding: utf-8 -*-
import os
import io
import time
import logging
import importlib
import pkgutil
import asyncio
from threading import Thread

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, Message,
    CallbackQuery
)
from flask import Flask

# মডুলার সিস্টেম থেকে ইমপোর্ট
from config import *
from database import *
from core_logic import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

worker_client = None
user_conversations = {}
upload_semaphore = asyncio.Semaphore(2)

# ---- KOYEB FLASK SERVER ----
app = Flask(__name__)

@app.route('/')
def home(): 
    return "🤖 Ultimate SPA Bot Running on Koyeb (With Telegram Direct Forwarding)"

def run_flask(): 
    # Koyeb এর জন্য ডাইনামিক পোর্ট সেটআপ
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

setup_resources()

try: 
    bot = Client("moviebot", api_id=int(API_ID), api_hash=API_HASH, bot_token=BOT_TOKEN)
except Exception as e: 
    logger.critical(f"Bot Init Error: {e}")
    exit(1)

def generate_file_caption(details):
    title = details.get("title") or details.get("name") or "Unknown"
    year = (details.get("release_date") or details.get("first_air_date") or "----")[:4]
    rating = f"{details.get('vote_average', 0):.1f}/10"
    
    if details.get('is_manual'): 
        genres, lang = "Movie/Series", details.get("custom_language") or "N/A"
    else:
        genres = ", ".join([g['name'] for g in details.get('genres', [])][:3])
        lang = details.get("custom_language") or "Dual Audio"
        
    return f"🎬 **{title} ({year})**\n━━━━━━━━━━━━━━━━━━━━━━━\n⭐ Rating: {rating}\n🎭 Genre: {genres}\n🔊 Language: {lang}\n\n🤖 Join: @{(bot.me).username}"

async def start_worker():
    global worker_client
    session = await get_worker_session()
    if session:
        try:
            worker_client = Client("worker_session", session_string=session, api_id=int(API_ID), api_hash=API_HASH)
            await worker_client.start()
            logger.info("✅ Worker Session Started!")
        except Exception as e:
            logger.error(f"❌ Worker Error: {e}")
            worker_client = None

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    uid = message.from_user.id
    name = message.from_user.first_name
    await add_user(uid, name) 
    
    if len(message.command) > 1:
        payload = message.command[1]
        
        if payload.startswith("batch-"):
            if await is_banned(uid): return await message.reply_text("🚫 **Access Denied:** You are banned.")
            try:
                pid = payload.split("-")[1]
                temp_msg = await message.reply_text("🔍 **Searching Batch Files...**")
                
                post = await posts_col.find_one({"_id": pid})
                if not post or not post.get("links"):
                    return await temp_msg.edit_text("❌ **Batch Not Found!**")
                    
                await temp_msg.edit_text("⏳ **Sending Files... Please wait**")
                
                final_caption = generate_file_caption(post["details"]) if "details" in post else f"🎥 **Here are your files!**\n\n🤖 Powered by {client.me.mention}"
                
                msg_ids = []
                for link in post["links"]:
                    if link.get("tg_url") and "get-" in link["tg_url"]:
                        try:
                            msg_id = int(link["tg_url"].split("get-")[1])
                            file_msg = await client.copy_message(
                                chat_id=uid, 
                                from_chat_id=DB_CHANNEL_ID, 
                                message_id=msg_id, 
                                caption=final_caption, 
                                protect_content=False
                            )
                            msg_ids.append(file_msg.id)
                            await asyncio.sleep(0.5)
                        except: pass
                            
                await temp_msg.delete()

                timer = await get_auto_delete_timer()
                if timer > 0 and msg_ids:
                    time_str = f"{timer//60} মিনিট" if timer >= 60 else f"{timer} সেকেন্ড"
                    warning_msg = await message.reply_text(f"⚠️ **সতর্কবার্তা:** কপিরাইট এড়াতে এই ফাইলগুলো **{time_str}** পর ডিলিট হয়ে যাবে!\n\n📥 দয়া করে এখনই ফাইলগুলো Save করে রাখুন।", quote=True)
                    msg_ids.append(warning_msg.id)
                    asyncio.create_task(auto_delete_task(client, uid, msg_ids, timer))
                return
            except Exception as e:
                return await message.reply_text("❌ **Error fetching batch files!**")
                
        elif payload.startswith("get-"):
            if await is_banned(uid): return await message.reply_text("🚫 **Access Denied:** You are banned.")
            try:
                msg_id = int(payload.split("-")[1])
                temp_msg = await message.reply_text("🔍 **Searching File...**")
                
                post = await posts_col.find_one({"links.tg_url": {"$regex": f"get-{msg_id}"}})
                if not post: post = await posts_col.find_one({"links.url": {"$regex": f"get-{msg_id}"}})
                    
                final_caption = generate_file_caption(post["details"]) if post and "details" in post else f"🎥 **Here is your file!**\n\n🤖 Powered by {client.me.mention}"
                file_msg = await client.copy_message(chat_id=uid, from_chat_id=DB_CHANNEL_ID, message_id=msg_id, caption=final_caption, protect_content=False)
                await temp_msg.delete()

                timer = await get_auto_delete_timer()
                if timer > 0:
                    time_str = f"{timer//60} মিনিট" if timer >= 60 else f"{timer} সেকেন্ড"
                    warning_msg = await message.reply_text(f"⚠️ **সতর্কবার্তা:** কপিরাইট এড়াতে এই ফাইলটি **{time_str}** পর ডিলিট হয়ে যাবে!\n\n📥 দয়া করে এখনই ফাইলটি Save করে রাখুন।", quote=True)
                    asyncio.create_task(auto_delete_task(client, uid,[file_msg.id, warning_msg.id], timer))
                return 
            except Exception as e: return await message.reply_text("❌ **File Not Found!**")

    user_conversations.pop(uid, None)
    if not await is_authorized(uid): return await message.reply_text("⚠️ **অ্যাক্সেস নেই**\n\nএই বটটি ব্যবহার করতে এডমিনের অনুমতির প্রয়োজন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{OWNER_USERNAME}")]]))

    welcome_text = (
        f"👋 **স্বাগতম {name}!**\n\n"
        "🎬 **Movie & Series Bot (v42 Advanced)**-এ আপনাকে স্বাগতম।\n"
        "📌 **কিভাবে ব্যবহার করবেন?**\n"
        "👉 `/post <নাম>` - অটোমেটিক পোস্ট করতে\n"
        "👉 `/manual` - ম্যানুয়াল পোস্ট করতে\n"
        "👉 `/setapi <server> <key>` - আর্নিং সাইট সেট করতে (Only Admin)\n"
        "👉 `/setadlink <লিংক>` - নিজের অ্যাড লিংক সেট করতে\n"
        "👉 `/mysettings` - নিজের সেটিংস ও লিংক দেখতে\n"
        "👉 `/cancel` - কোনো কাজ বাতিল করতে\n"
        "👉 `/edit <নাম বা ID>` - পোস্ট এডিট করতে"
    )
    await message.reply_text(welcome_text)

@bot.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(client, message):
    uid = message.from_user.id
    if uid in user_conversations:
        user_conversations.pop(uid, None)
        await message.reply_text("✅ সব চলমান প্রসেস বাতিল করা হয়েছে। নতুন কমান্ড দিন।")
    else: await message.reply_text("⚠️ বাতিল করার মতো কোনো কাজ চলমান নেই।")

@bot.on_message(filters.command("auth") & filters.user(OWNER_ID))
async def auth_user(client, message):
    try: await users_col.update_one({"_id": int(message.command[1])}, {"$set": {"authorized": True, "banned": False}}, upsert=True); await message.reply_text(f"✅ User {message.command[1]} is now AUTHORIZED.")
    except: await message.reply_text("❌ Usage: `/auth 123456789`")

@bot.on_message(filters.command("ban") & filters.user(OWNER_ID))
async def ban_user(client, message):
    try: await users_col.update_one({"_id": int(message.command[1])}, {"$set": {"banned": True}}); await message.reply_text(f"🚫 User {message.command[1]} is now BANNED.")
    except: await message.reply_text("❌ Usage: `/ban 123456789`")

@bot.on_message(filters.command("setownerads") & filters.user(OWNER_ID))
async def set_owner_ads_cmd(client, message):
    if len(message.command) > 1:
        raw_links = message.text.split(None, 1)[1].split()
        valid =[l if l.startswith("http") else "https://" + l for l in raw_links]
        if valid: await set_owner_ads_db(valid); await message.reply_text(f"✅ Owner Ads Updated! ({len(valid)} links)")
        else: await message.reply_text("❌ No valid links found.")
    else: await message.reply_text("⚠️ Usage: `/setownerads link1 link2`")

@bot.on_message(filters.command("setshare") & filters.user(OWNER_ID))
async def set_share_cmd(client, message):
    try:
        percent = int(message.command[1])
        if 0 <= percent <= 100: await set_admin_share_db(percent); await message.reply_text(f"✅ Share Updated: Admin **{percent}%**")
    except: await message.reply_text("⚠️ Usage: `/setshare 20`")

@bot.on_message(filters.command("setdel") & filters.user(OWNER_ID))
async def set_auto_delete_cmd(client, message):
    try: await set_auto_delete_timer_db(int(message.command[1])); await message.reply_text(f"✅ Timer Updated: **{message.command[1]} seconds**")
    except: await message.reply_text("⚠️ Usage: `/setdel 600`")

@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_msg(client, message):
    if not message.reply_to_message: return await message.reply_text("⚠️ Reply to a message.")
    msg = await message.reply_text("⏳ Broadcasting...")
    count = 0
    async for user in users_col.find({}):
        try: await message.reply_to_message.copy(user["_id"]); count += 1; await asyncio.sleep(0.1) 
        except: pass
    await msg.edit_text(f"✅ Broadcast Sent to **{count}** users.")

@bot.on_message(filters.command("setapi") & filters.user(OWNER_ID))
async def set_api_command(client, message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3: return await message.reply_text("⚠️ **Format:** `/setapi <server_name> <api_key>`\n**Supported Servers:** `doodstream`, `streamtape`, `filemoon`, `mixdrop`\nFor Streamtape & MixDrop use format: `email:api_key`")
        server_name, api_key = parts[1].lower(), parts[2].strip()
        if server_name not in["doodstream", "streamtape", "filemoon", "mixdrop"]: return await message.reply_text("❌ Unsupported server.")
        await set_server_api(server_name, api_key)
        await message.reply_text(f"✅ **{server_name.title()}** API Key Saved successfully!")
    except Exception as e: await message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.command("setworker") & filters.user(OWNER_ID))
async def set_worker_cmd(client, message):
    global worker_client
    if len(message.command) < 2: return await message.reply_text("⚠️ **Format:** `/setworker SESSION_STRING`")
    session_string = message.text.split(None, 1)[1]
    await set_worker_session_db(session_string)
    await message.reply_text("⏳ সেশন সেভ হয়েছে, ওয়ার্কার রিস্টার্ট হচ্ছে...")
    if worker_client:
        try: await worker_client.stop()
        except: pass
    try:
        worker_client = Client("worker_session", session_string=session_string, api_id=int(API_ID), api_hash=API_HASH)
        await worker_client.start()
        await message.reply_text("✅ **Worker Session** সফলভাবে কানেক্ট হয়েছে!")
    except Exception as e: await message.reply_text(f"❌ কানেকশন ফেইলড: {e}")

@bot.on_message(filters.command("workerinfo") & filters.user(OWNER_ID))
async def worker_info(client, message):
    if worker_client and worker_client.is_connected:
        me = await worker_client.get_me()
        await message.reply_text(f"🤖 **Worker Status:** Active\n👤 **Name:** {me.first_name}\n🆔 **ID:** `{me.id}`")
    else: await message.reply_text("❌ Worker Session কানেক্টেড নেই।")

@bot.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def bot_stats(client, message):
    total, total_posts, admin_share = await get_all_users_count(), await posts_col.count_documents({}), await get_admin_share()
    await message.reply_text(f"📊 **BOT STATS**\n👥 Users: {total}\n📁 Posts: {total_posts}\n💰 Admin Share: {admin_share}%")

@bot.on_message(filters.command("mysettings") & filters.private)
async def my_settings_cmd(client, message):
    uid = message.from_user.id
    if not await is_authorized(uid): return await message.reply_text("🚫 **অ্যাক্সেস নেই**")
    user_ads = await get_user_ads(uid)
    ads_text = "\n".join([f"🔗 {ad}" for ad in user_ads]) if user_ads else "❌ কোনো লিংক সেট করা নেই। (Owner Ads ব্যবহার হচ্ছে)"
    await message.reply_text(f"⚙️ **Your Settings**\n\n👤 **Name:** {message.from_user.first_name}\n🆔 **ID:** `{uid}`\n\n📢 **Your Ad Links:**\n{ads_text}\n\n💡 _Use /setadlink to update your ads._", disable_web_page_preview=True)

@bot.on_message(filters.command("setadlink") & filters.private)
async def set_ad(client, message):
    uid = message.from_user.id
    if not await is_authorized(uid): return
    if len(message.command) > 1:
        raw_links = message.text.split(None, 1)[1].split()
        valid_links =[l if l.startswith("http") else "https://" + l for l in raw_links]
        if valid_links: await save_user_ads(uid, valid_links); await message.reply_text("✅ Ad Links Saved!")
    else: await message.reply_text("⚠️ Usage: `/setadlink site.com`")

@bot.on_message(filters.command("manual") & filters.private)
async def manual_post_cmd(client, message):
    uid = message.from_user.id
    if not await is_authorized(uid): return
    user_conversations[uid] = {"details": {"is_manual": True, "manual_screenshots":[]}, "links":[], "state": "manual_title"}
    await message.reply_text("✍️ **Manual Post Started**\n\nপ্রথমে **টাইটেল (Title)** লিখুন:\n_(যেকোনো মুহূর্তে বাতিল করতে /cancel কমান্ড দিন)_")

@bot.on_message(filters.command("history") & filters.private)
async def history_cmd(client, message):
    uid = message.from_user.id
    if not await is_authorized(uid): return
    posts = await posts_col.find({}).sort("updated_at", -1).limit(10).to_list(10)
    if not posts: return await message.reply_text("❌ No history found.")
    text = "📜 **Last 10 Posts:**\n\n"
    for p in posts: text += f"🎬 {p['details'].get('title', 'Unknown')} (ID: `{p['_id']}`)\n"
    await message.reply_text(text)

@bot.on_message(filters.command("edit") & filters.private)
async def edit_post_cmd(client, message):
    uid = message.from_user.id
    if not await is_authorized(uid): return
    if len(message.command) < 2: return await message.reply_text("⚠️ Usage: `/edit <Name OR ID>`")
    
    query = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text("🔍 Searching...")
    post = await posts_col.find_one({"_id": query})
    if not post:
        results = await posts_col.find({"details.title": {"$regex": query, "$options": "i"}}).to_list(10)
        if not results: results = await posts_col.find({"details.name": {"$regex": query, "$options": "i"}}).to_list(10)
        if not results: return await msg.edit_text("❌ Not found.")
        if len(results) > 1:
            btns = [[InlineKeyboardButton(f"{r['details'].get('title')} ({r['_id']})", callback_data=f"forcedit_{r['_id']}_{uid}")] for r in results]
            return await msg.edit_text("👇 **Select Post:**", reply_markup=InlineKeyboardMarkup(btns))
        post = results[0] 
        
    await msg.delete() 
    await start_edit_session(uid, post, message)

async def start_edit_session(uid, post, message):
    user_conversations[uid] = {"details": post["details"], "links": post.get("links",[]), "state": "edit_mode", "post_id": post["_id"]}
    btns = [[InlineKeyboardButton("➕ Add New Link", callback_data=f"add_lnk_edit_{uid}")],[InlineKeyboardButton("✅ Generate New Code", callback_data=f"gen_edit_{uid}")]]
    txt = f"📝 **Editing:** {post['details'].get('title')}\n🆔 `{post['_id']}`\n\n👇 **What to do?**"
    if isinstance(message, Message): await message.reply_text(txt, reply_markup=InlineKeyboardMarkup(btns))
    else: await message.edit_text(txt, reply_markup=InlineKeyboardMarkup(btns))

@bot.on_callback_query(filters.regex("^forcedit_"))
async def force_edit_cb(client, cb):
    try: _, pid, uid = cb.data.split("_"); post = await posts_col.find_one({"_id": pid})
    except: return
    if post: await start_edit_session(int(uid), post, cb.message)

@bot.on_message(filters.command("post") & filters.private)
async def post_cmd(client, message):
    uid = message.from_user.id
    if not await is_authorized(uid): return
    if len(message.command) < 2: return await message.reply_text("⚠️ Usage:\n`/post Avatar`")
    
    query = message.text.split(" ", 1)[1].strip()
    msg = await message.reply_text(f"🔎 Processing `{query}`...")
    m_type, m_id = extract_tmdb_id(query)

    if m_type and m_id:
        if m_type == "imdb":
            data = await fetch_url(f"https://api.themoviedb.org/3/find/{m_id}?api_key={TMDB_API_KEY}&external_source=imdb_id")
            res = data.get("movie_results",[]) + data.get("tv_results",[])
            if res: m_type, m_id = res[0]['media_type'], res[0]['id']
            else: return await msg.edit_text("❌ IMDb ID not found.")
                
        details = await get_tmdb_details(m_type, m_id)
        if not details: return await msg.edit_text("❌ Details not found.")
        user_conversations[uid] = { "details": details, "links":[], "state": "wait_lang" }
        return await msg.edit_text(f"✅ Found: **{details.get('title') or details.get('name')}**\n\n🗣️ Enter **Language** (e.g. Hindi):")

    results = await search_tmdb(query)
    if not results: return await msg.edit_text("❌ No results found.")
    buttons = [[InlineKeyboardButton(f"{r.get('title') or r.get('name')} ({str(r.get('release_date','----'))[:4]})", callback_data=f"sel_{r['media_type']}_{r['id']}")] for r in results]
    await msg.edit_text("👇 **Select Content:**", reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_callback_query(filters.regex("^sel_"))
async def on_select(client, cb):
    try:
        _, m_type, m_id = cb.data.split("_")
        details = await get_tmdb_details(m_type, m_id)
        if not details: return await cb.message.edit_text("❌ Details not found.")
        user_conversations[cb.from_user.id] = { "details": details, "links":[], "state": "wait_lang" }
        await cb.message.edit_text(f"✅ Selected: **{details.get('title') or details.get('name')}**\n\n🗣️ Enter **Language**:")
    except Exception as e: logger.error(f"Select error: {e}")

async def process_file_upload(client, message, uid, temp_name):
    convo = user_conversations.get(uid)
    if not convo: return
    
    convo["pending_uploads"] = convo.get("pending_uploads", 0) + 1
    status_msg = await message.reply_text(f"🕒 **সারির অপেক্ষায়...**\n({temp_name})", quote=True)
    
    try:
        async with upload_semaphore:
            await status_msg.edit_text(f"⏳ **টেলিগ্রাম ডাটাবেসে সেভ হচ্ছে...**")
            
            copied_msg = await message.copy(chat_id=DB_CHANNEL_ID)
            bot_username = client.me.username if client.me else (await client.get_me()).username
            tg_link = f"https://t.me/{bot_username}?start=get-{copied_msg.id}"
            
            # 🔥 ডেটাবেস ব্লোট (খালি None ইউআরএল) রিমুভ করে স্টোরেজ বাঁচানো হলো
            convo["links"].append({"label": temp_name, "tg_url": tg_link, "is_grouped": True})
            await status_msg.edit_text(f"✅ **আপলোড সম্পন্ন:** {temp_name}")
            
            try: await message.delete()
            except: pass
                
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        await status_msg.edit_text(f"❌ **আপলোড ফেইল হয়েছে!**\nকারণ: `{e}`\n\n⚠️ **দয়া করে চেক করুন বটকে ডাটাবেস চ্যানেলে Admin করা হয়েছে কিনা।**")
    finally:
        convo["pending_uploads"] = max(0, convo.get("pending_uploads", 0) - 1)

@bot.on_message(filters.private & (filters.text | filters.video | filters.document | filters.photo) & ~filters.command(["start", "post", "manual", "edit", "history", "setadlink", "mysettings", "auth", "ban", "stats", "broadcast", "setownerads", "setshare", "setdel", "setapi", "cancel", "repost", "setup", "myconfig", "delsetup"]))
async def text_handler(client, message):
    uid = message.from_user.id
    if uid not in user_conversations: return
    
    convo = user_conversations[uid]
    state = convo.get("state")
    text = message.text.strip() if message.text else ""
    
    if state == "manual_title":
        convo["details"]["title"] = text
        convo["state"] = "manual_plot"
        await message.reply_text("📝 এবার মুভির **গল্প/Plot** লিখুন:")
        
    elif state == "manual_plot":
        convo["details"]["overview"] = text
        convo["state"] = "manual_poster"
        await message.reply_text("🖼️ এবার একটি **পোস্টার (Photo)** সেন্ড করুন:")
        
    elif state == "manual_poster":
        if not message.photo: return await message.reply_text("⚠️ দয়া করে ছবি পাঠান।")
            
        msg = await message.reply_text("⏳ Processing Poster...")
        try:
            photo_path = await message.download()
            img_url = upload_to_catbox(photo_path) 
            os.remove(photo_path)
            
            if img_url:
                convo["details"]["manual_poster_url"] = img_url
                convo["state"] = "ask_screenshots"
                await msg.edit_text("✅ Poster Uploaded!\n\n📸 **Add Custom Screenshots?**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📸 Add", callback_data=f"ss_yes_{uid}"), InlineKeyboardButton("⏭️ Skip", callback_data=f"ss_no_{uid}")]]))
            else: await msg.edit_text("❌ Upload Failed.")
        except: await msg.edit_text("❌ Error uploading.")

    elif state == "wait_screenshots":
        if not message.photo: return await message.reply_text("⚠️ Please send PHOTO.")
            
        msg = await message.reply_text("⏳ Uploading SS...")
        try:
            photo_path = await message.download()
            ss_url = upload_to_catbox(photo_path)
            os.remove(photo_path)
            
            if ss_url:
                if "manual_screenshots" not in convo["details"]: convo["details"]["manual_screenshots"] =[]
                convo["details"]["manual_screenshots"].append(ss_url)
                await msg.edit_text(f"✅ Screenshot Added!\nSend another or click DONE.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ DONE", callback_data=f"ss_done_{uid}")]]))
        except: pass

    elif state == "wait_lang":
        convo["details"]["custom_language"] = text
        convo["state"] = "wait_quality"
        await message.reply_text("💿 Enter **Quality**:")
        
    elif state == "wait_quality":
        convo["details"]["custom_quality"] = text
        convo["state"] = "ask_links"
        await message.reply_text("🔗 Add Download Links?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Links", callback_data=f"lnk_yes_{uid}"), InlineKeyboardButton("🏁 Finish", callback_data=f"lnk_no_{uid}")]]))
        
    elif state == "wait_link_name_custom":
        convo["temp_name"] = text
        convo["state"] = "wait_link_url"
        await message.reply_text(f"✅ নাম সেট: **{text}**\n\n🔗 এবার **URL** দিন অথবা **ভিডিও ফাইলটি** ফরোয়ার্ড করুন:")
        
    elif state == "wait_link_url":
        if message.video or message.document:
            asyncio.create_task(process_file_upload(client, message, uid, convo["temp_name"]))
            if convo.get("post_id"):
                 convo["state"] = "edit_mode"
                 await message.reply_text(f"✅ **{convo['temp_name']}** ব্যাকগ্রাউন্ডে আপলোড শুরু হয়েছে!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Another Link", callback_data=f"add_lnk_edit_{uid}"), InlineKeyboardButton("✅ Finish", callback_data=f"gen_edit_{uid}")]]))
            else:
                convo["state"] = "ask_links"
                await message.reply_text(f"✅ **{convo['temp_name']}** ব্যাকগ্রাউন্ডে আপলোড শুরু হয়েছে!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Another", callback_data=f"lnk_yes_{uid}"), InlineKeyboardButton("🏁 Finish", callback_data=f"lnk_no_{uid}")]]))

        elif text.startswith("http"):
            # 🔥 ডেটাবেস ব্লোট ক্লিন করা হয়েছে 
            convo["links"].append({"label": convo["temp_name"], "url": text, "is_grouped": False})
            if convo.get("post_id"):
                 convo["state"] = "edit_mode"
                 await message.reply_text(f"✅ Saved! Link: `{text}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Link", callback_data=f"add_lnk_edit_{uid}"), InlineKeyboardButton("✅ Finish", callback_data=f"gen_edit_{uid}")]]))
            else:
                convo["state"] = "ask_links"
                await message.reply_text(f"✅ Saved! Total: {len(convo['links'])}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Another", callback_data=f"lnk_yes_{uid}"), InlineKeyboardButton("🏁 Finish", callback_data=f"lnk_no_{uid}")]]))
        else: await message.reply_text("⚠️ Invalid Input. URL or File required.")

    elif state == "wait_batch_files":
        if text.lower() == "/done":
            if convo.get("post_id"):
                 convo["state"] = "edit_mode"
                 await message.reply_text(f"✅ **Batch Files Accepted!**\nঅপেক্ষা করুন, আপলোড শেষ হলে Finish এ ক্লিক করবেন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Link", callback_data=f"add_lnk_edit_{uid}"), InlineKeyboardButton("✅ Finish", callback_data=f"gen_edit_{uid}")]]))
            else:
                convo["state"] = "ask_links"
                await message.reply_text(f"✅ **Batch Files Accepted!**\nঅপেক্ষা করুন, আপলোড শেষ হলে Finish এ ক্লিক করবেন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Another", callback_data=f"lnk_yes_{uid}"), InlineKeyboardButton("🏁 Finish", callback_data=f"lnk_no_{uid}")]]))
        elif message.video or message.document:
            file_name = getattr(message.video, "file_name", None) or getattr(message.document, "file_name", None)
            if not file_name: file_name = f"Episode {len(convo.get('links',[])) + convo.get('pending_uploads', 0) + 1}"
            asyncio.create_task(process_file_upload(client, message, uid, file_name))
        else: await message.reply_text("⚠️ দয়া করে ভিডিও/ফাইল দিন অথবা শেষ হলে /done লিখুন।")

    elif state == "wait_badge_text":
        convo["details"]["badge_text"] = text
        await message.reply_text("🛡️ **Safety Check:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Safe", callback_data=f"safe_yes_{uid}"), InlineKeyboardButton("🔞 18+", callback_data=f"safe_no_{uid}")]]))

@bot.on_callback_query(filters.regex("^ss_"))
async def ss_cb(client, cb):
    try: action, uid = cb.data.rsplit("_", 1); uid = int(uid)
    except: return
    if action == "ss_yes":
        user_conversations[uid]["state"] = "wait_screenshots"
        user_conversations[uid]["details"]["manual_screenshots"] =[]
        await cb.message.edit_text("📸 **Send Screenshots now.**")
    else:
        user_conversations[uid]["state"] = "wait_lang"
        await cb.message.edit_text("🗣️ Enter **Language** (e.g. Hindi):")

@bot.on_callback_query(filters.regex("^lnk_"))
async def link_cb(client, cb):
    try: action, uid = cb.data.rsplit("_", 1); uid = int(uid)
    except: return
    if action == "lnk_yes":
        user_conversations[uid]["state"] = "wait_link_name"
        btns = [[InlineKeyboardButton("🎬 1080p", callback_data=f"setlname_1080p_{uid}"), InlineKeyboardButton("🎬 720p", callback_data=f"setlname_720p_{uid}"), InlineKeyboardButton("🎬 480p", callback_data=f"setlname_480p_{uid}")],[InlineKeyboardButton("✍️ Custom", callback_data=f"setlname_custom_{uid}"), InlineKeyboardButton("📁 Default", callback_data=f"setlname_telegram_{uid}")],[InlineKeyboardButton("📦 Batch Upload (All Episodes)", callback_data=f"setlname_batch_{uid}")]]
        await cb.message.edit_text("👇 বাটনের ধরন বা কোয়ালিটি সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(btns))
    else:
        if user_conversations.get(uid, {}).get("pending_uploads", 0) > 0: return await cb.answer("⏳ ফাইল আপলোড শেষ হওয়া পর্যন্ত অপেক্ষা করুন...", show_alert=True)
        user_conversations[uid]["state"] = "wait_badge_text"
        await cb.message.edit_text("🖼️ **Badge Text?**\n\nলিখে পাঠান অথবা Skip করুন:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Skip", callback_data=f"skip_badge_{uid}")]]))

@bot.on_callback_query(filters.regex("^add_lnk_edit_"))
async def add_lnk_edit(client, cb):
    uid = int(cb.data.split("_")[-1])
    if uid in user_conversations:
        user_conversations[uid]["state"] = "wait_link_name"
        btns = [[InlineKeyboardButton("🎬 1080p", callback_data=f"setlname_1080p_{uid}"), InlineKeyboardButton("🎬 720p", callback_data=f"setlname_720p_{uid}"), InlineKeyboardButton("🎬 480p", callback_data=f"setlname_480p_{uid}")],[InlineKeyboardButton("✍️ Custom", callback_data=f"setlname_custom_{uid}"), InlineKeyboardButton("📁 Default", callback_data=f"setlname_telegram_{uid}")],[InlineKeyboardButton("📦 Batch Upload (All Episodes)", callback_data=f"setlname_batch_{uid}")]]
        await cb.message.edit_text("👇 বাটনের ধরন বা কোয়ালিটি সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(btns))

@bot.on_callback_query(filters.regex("^setlname_"))
async def set_lname_cb(client, cb):
    try: _, action, uid = cb.data.split("_"); uid = int(uid)
    except: return
    if action in["1080p", "720p", "480p"]:
        user_conversations[uid]["temp_name"] = action; user_conversations[uid]["state"] = "wait_link_url"
        await cb.message.edit_text(f"✅ কোয়ালিটি সেট: **{action}**\n\n🔗 এবার **URL** বা **ভিডিও ফাইল** দিন:")
    elif action == "custom":
        user_conversations[uid]["state"] = "wait_link_name_custom"
        await cb.message.edit_text("📝 কাস্টম বাটনের নাম লিখুন (যেমন: 4K, 1080p 60fps বা Ep-01):")
    elif action == "batch":
        user_conversations[uid]["state"] = "wait_batch_files"
        user_conversations[uid]["details"]["is_batch"] = True 
        await cb.message.edit_text("📦 **Batch Mode:**\n\nআপনার সিরিজের সব ফাইল বা এপিসোড একসাথে ফরোয়ার্ড করুন।\nফাইলের নামগুলোই এপিসোড নাম হিসেবে সেট হবে।\nসব দেওয়া হলে টাইপ করুন: `/done`")
    else:
        user_conversations[uid]["temp_name"] = "Telegram Files"; user_conversations[uid]["state"] = "wait_link_url"
        await cb.message.edit_text("✅ বাটন সেট। 🔗 এবার **URL** বা **ভিডিও ফাইল** দিন:")

@bot.on_callback_query(filters.regex("^gen_edit_"))
async def gen_edit_finish(client, cb):
    uid = int(cb.data.split("_")[-1])
    if uid in user_conversations:
        if user_conversations[uid].get("pending_uploads", 0) > 0: return await cb.answer("⏳ ফাইল আপলোড শেষ হওয়া পর্যন্ত অপেক্ষা করুন...", show_alert=True)
        await cb.answer("⏳ Generating...", show_alert=False)
        await generate_final_post(client, uid, cb.message)

@bot.on_callback_query(filters.regex("^skip_badge_"))
async def skip_badge_cb(client, cb):
    uid = int(cb.data.split("_")[-1])
    if uid in user_conversations:
        user_conversations[uid]["details"]["badge_text"] = None
        await cb.message.edit_text("🛡️ **Safety Check:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Safe", callback_data=f"safe_yes_{uid}"), InlineKeyboardButton("🔞 18+", callback_data=f"safe_no_{uid}")]]))

@bot.on_callback_query(filters.regex("^safe_"))
async def safety_cb(client, cb):
    try: action, uid = cb.data.rsplit("_", 1); uid = int(uid)
    except: return
    user_conversations[uid]["details"]["force_adult"] = True if action == "safe_no" else False
    btns = [[InlineKeyboardButton("🔴 Netflix (Dark)", callback_data=f"theme_netflix_{uid}")],[InlineKeyboardButton("🔵 Prime (Blue)", callback_data=f"theme_prime_{uid}")],[InlineKeyboardButton("⚪ Anime (Light)", callback_data=f"theme_light_{uid}")]]
    await cb.message.edit_text("🎨 **ওয়েবসাইটের থিম (Theme) সিলেক্ট করুন:**", reply_markup=InlineKeyboardMarkup(btns))

@bot.on_callback_query(filters.regex("^theme_"))
async def theme_cb(client, cb):
    try: _, theme_name, uid = cb.data.split("_"); uid = int(uid)
    except: return
    user_conversations[uid]["details"]["theme"] = theme_name
    await generate_final_post(client, uid, cb.message)

async def generate_final_post(client, uid, message):
    convo = user_conversations.get(uid)
    if not convo: return await message.edit_text("❌ Session expired.")
    status_msg = await message.edit_text("⏳ **Generating Final Post...**")

    try:
        pid = await save_post_to_db(convo["details"], convo["links"])
        convo["details"]["post_id"] = pid 
        
        loop = asyncio.get_running_loop()
        img_io, poster_bytes = await loop.run_in_executor(None, generate_image, convo["details"])

        if convo["details"].get("badge_text") and poster_bytes:
            new_poster = await loop.run_in_executor(None, upload_to_catbox_bytes, poster_bytes)
            if new_poster: convo["details"]["manual_poster_url"] = new_poster 
        
        html = generate_html_code(convo["details"], convo["links"], await get_user_ads(uid), await get_owner_ads(), await get_admin_share())
        caption = generate_formatted_caption(convo["details"], pid)
        convo["final"] = {"html": html}
        
        btns = [[InlineKeyboardButton("📄 Get Blogger Code", callback_data=f"get_code_{uid}")]]
        if img_io:
            await client.send_photo(message.chat.id, img_io, caption=caption, reply_markup=InlineKeyboardMarkup(btns))
            await status_msg.delete()
        else:
            await client.send_message(message.chat.id, caption, reply_markup=InlineKeyboardMarkup(btns))
            await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** `{e}`")

@bot.on_callback_query(filters.regex("^get_code_"))
async def get_code(client, cb):
    try: uid = int(cb.data.rsplit("_", 1)[1])
    except: return
    data = user_conversations.get(uid)
    if not data or "final" not in data: return await cb.answer("Expired.", show_alert=True)
    await cb.answer("⏳ Generating Code...", show_alert=False)
    link = await create_paste_link(data["final"]["html"])
    
    if link: await cb.message.reply_text(f"✅ **Code Ready!**\n\n👇 Copy:\n{link}", disable_web_page_preview=True)
    else:
        file = io.BytesIO(data["final"]["html"].encode())
        file.name = "post.html"
        await client.send_document(cb.message.chat.id, file, caption="⚠️ Link failed. Download File.")

async def load_plugins():
    plugins_path = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.exists(plugins_path): os.makedirs(plugins_path); return
    print("🔌 Loading plugins...")
    for loader, module_name, is_pkg in pkgutil.iter_modules([plugins_path]):
        try:
            module = importlib.import_module(f"plugins.{module_name}")
            if hasattr(module, "register"): await module.register(bot)
            print(f"✅ Plugin Loaded: {module_name}")
        except Exception as e: print(f"❌ Failed to load plugin {module_name}: {e}")

async def main():
    await bot.start()
    await load_plugins()
    await start_worker() 
    print("✅ Bot and Worker are Online with Plugin Support!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🚀 Ultimate SPA Bot is Starting with Plugin System...")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
