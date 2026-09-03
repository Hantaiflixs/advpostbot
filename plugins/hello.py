from pyrogram import filters

# এই register ফাংশনটি মেইন কোড থেকে কল হবে
async def register(bot):
    
    @bot.on_message(filters.command("test_plugin"))
    async def test_plugin(client, message):
        await message.reply_text("✅ প্লাগইন সিস্টেম কাজ করছে!")
