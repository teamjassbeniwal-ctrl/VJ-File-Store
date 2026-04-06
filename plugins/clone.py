# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
from datetime import datetime
from pymongo import MongoClient
from Script import script
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import API_ID, API_HASH, DB_URI, CLONE_MODE

# HARDCODED DATABASE NAME – MUST MATCH THE ONE IN clone_plugins/commands.py
CLONE_DB_NAME = "cloned_vjbotz"

mongo_client = MongoClient(DB_URI)
mongo_db = mongo_client[CLONE_DB_NAME]

@Client.on_message(filters.command("clone") & filters.private)
async def clone(client, message):
    if CLONE_MODE == False:
        return
    
    user_id = message.from_user.id
    
    existing_bot = mongo_db.bots.find_one({"user_id": user_id})
    if existing_bot:
        buttons = [[
            InlineKeyboardButton("🔧 Manage Your Bot", callback_data=f"customize_{existing_bot['bot_id']}"),
            InlineKeyboardButton("🗑️ Delete Bot", callback_data="delete_clone")
        ]]
        await message.reply_text(
            "<b>🤖 You already have a clone bot!</b>\n\n"
            f"<b>Bot:</b> @{existing_bot['username']}\n"
            f"<b>Token:</b> <code>{existing_bot['token'][:20]}...</code>\n\n"
            "<b>Use the buttons below to manage your bot.</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    techvj = await client.ask(
        message.chat.id, 
        "<b>📌 Steps to create your clone bot:\n\n"
        "1) Send /newbot to @BotFather\n"
        "2) Give a name for your bot\n"
        "3) Give a unique username\n"
        "4) Then you will get a message with your bot token\n"
        "5) Forward that message to me\n\n"
        "Type /cancel to cancel this process.</b>"
    )
    
    if techvj.text and techvj.text.lower() == '/cancel':
        await techvj.delete()
        return await message.reply('<b>❌ Cancelled this process</b>')
    
    if techvj.forward_from and techvj.forward_from.id == 93372553:
        try:
            bot_token = re.findall(r"\b(\d+:[A-Za-z0-9_-]+)\b", techvj.text)[0]
        except:
            return await message.reply('<b>❌ Something went wrong. Please forward the exact message from @BotFather</b>')
    else:
        return await message.reply('<b>❌ Please forward the message from @BotFather only!</b>')
    
    msg = await message.reply_text("**🔄 Creating your clone bot... Please wait.**")
    
    try:
        vj = Client(f"{bot_token}", API_ID, API_HASH, bot_token=bot_token, plugins={"root": "clone_plugins"})
        await vj.start()
        bot = await vj.get_me()
        
        details = {
            'bot_id': bot.id,
            'is_bot': True,
            'user_id': user_id,
            'name': bot.first_name,
            'token': bot_token,
            'username': bot.username,
            'bot_mode': 'Public',
            'bot_admins': [],
            'custom_start_text': None,
            'custom_start_pic': None,
            'custom_buttons': None,
            'force_subscribe_channel': None,
            'created_at': datetime.now()
        }
        mongo_db.bots.insert_one(details)
        
        customize_buttons = [[
            InlineKeyboardButton("🎨 Customize Your Bot", callback_data=f"customize_{bot.id}")
        ]]
        
        await msg.edit_text(
            f"<b>✅ Successfully created your clone bot!</b>\n\n"
            f"<b>🤖 Bot:</b> @{bot.username}\n"
            f"<b>🔑 Token:</b> <code>{bot_token}</code>\n\n"
            f"<b>Click below to customize your bot settings.</b>",
            reply_markup=InlineKeyboardMarkup(customize_buttons)
        )
    except BaseException as e:
        await msg.edit_text(f"<b>❌ Bot Error:</b>\n\n<code>{e}</code>\n\nPlease forward this message to @KingVJ01 for assistance.")

@Client.on_message(filters.command("deletecloned") & filters.private)
async def delete_cloned_bot(client, message):
    if CLONE_MODE == False:
        return
    
    user_id = message.from_user.id
    cloned_bot = mongo_db.bots.find_one({"user_id": user_id})
    
    if cloned_bot:
        mongo_db.bots.delete_one({"user_id": user_id})
        await message.reply_text("**✅ Your cloned bot has been removed from the database.**")
    else:
        await message.reply_text("**❌ You don't have any cloned bot.**")

@Client.on_callback_query()
async def clone_callback(client, query):
    if query.data == "delete_clone":
        user_id = query.from_user.id
        cloned_bot = mongo_db.bots.find_one({"user_id": user_id})
        if cloned_bot:
            mongo_db.bots.delete_one({"user_id": user_id})
            await query.message.edit_text("**✅ Your cloned bot has been deleted successfully!**")
        else:
            await query.answer("You don't have any clone bot!", show_alert=True)

async def restart_bots():
    bots = list(mongo_db.bots.find())
    for bot in bots:
        bot_token = bot['token']
        try:
            vj = Client(f"{bot_token}", API_ID, API_HASH, bot_token=bot_token, plugins={"root": "clone_plugins"})
            await vj.start()
            print(f"Started clone bot: @{bot['username']}")
        except Exception as e:
            print(f"Failed to start clone bot {bot['username']}: {e}")
