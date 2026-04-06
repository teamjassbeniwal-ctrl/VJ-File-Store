# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import logging
import random
import asyncio
import base64
import json
import re
from datetime import datetime
from Script import script
from validators import domain
from clone_plugins.dbusers import clonedb
from clone_plugins.users_api import get_user, update_user_info
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from config import PICS, CUSTOM_FILE_CAPTION, AUTO_DELETE_TIME, AUTO_DELETE, URL, STREAM_MODE, CLONE_DB_URI, CDB_NAME
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, CallbackQuery, Message
from TechVJ.utils.file_properties import get_name, get_hash
from urllib.parse import quote_plus
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# MongoDB connection for clone bots
mongo_client = MongoClient(CLONE_DB_URI)
mongo_db = mongo_client[CDB_NAME]

# Store temporary data for customization
temp_custom_data = {}

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    me = await client.get_me()
    bot_data = mongo_db.bots.find_one({'bot_id': me.id})
    
    if not await clonedb.is_user_exist(me.id, message.from_user.id):
        await clonedb.add_user(me.id, message.from_user.id)
    
    if len(message.command) != 2:
        # Get custom settings from database
        custom_start_text = bot_data.get("custom_start_text") if bot_data else None
        custom_start_pic = bot_data.get("custom_start_pic") if bot_data else None
        custom_buttons = bot_data.get("custom_buttons") if bot_data else None
        force_channel = bot_data.get("force_subscribe_channel") if bot_data else None
        
        # Force subscribe check
        if force_channel:
            try:
                member = await client.get_chat_member(f"@{force_channel}", message.from_user.id)
                if member.status in ["left", "kicked"]:
                    force_buttons = [[InlineKeyboardButton("🔓 Join Channel", url=f"https://t.me/{force_channel}")]]
                    await message.reply_text(
                        f"<b>⚠️ Please join @{force_channel} to use this bot!</b>",
                        reply_markup=InlineKeyboardMarkup(force_buttons)
                    )
                    return
            except Exception as e:
                print(f"Force subscribe error: {e}")
        
        # Default buttons
        buttons = [[
            InlineKeyboardButton('💝 Subscribe YouTube', url='https://youtube.com/@Tech_VJ')
        ],[
            InlineKeyboardButton('🔍 Support Group', url='https://t.me/vj_bot_disscussion'),
            InlineKeyboardButton('🤖 Update Channel', url='https://t.me/vj_bots')
        ],[
            InlineKeyboardButton('💁‍♀️ Help', callback_data='help'),
            InlineKeyboardButton('😊 About', callback_data='about')
        ]]
        
        # Add custom buttons if exists
        if custom_buttons:
            try:
                custom_btn_list = json.loads(custom_buttons)
                for btn_row in custom_btn_list:
                    row = []
                    for btn in btn_row:
                        row.append(InlineKeyboardButton(btn['text'], url=btn['url']))
                    buttons.append(row)
            except Exception as e:
                print(f"Custom buttons error: {e}")
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        # Use custom start text or default
        if custom_start_text:
            start_text = custom_start_text.replace("{mention}", message.from_user.mention).replace("{bot_name}", me.mention)
        else:
            start_text = script.CLONE_START_TXT.format(message.from_user.mention, me.mention)
        
        # Use custom start picture or random default
        if custom_start_pic:
            try:
                await message.reply_photo(photo=custom_start_pic, caption=start_text, reply_markup=reply_markup)
            except Exception as e:
                print(f"Custom picture error: {e}")
                await message.reply_photo(photo=random.choice(PICS), caption=start_text, reply_markup=reply_markup)
        else:
            await message.reply_photo(photo=random.choice(PICS), caption=start_text, reply_markup=reply_markup)
        return
    
    # Handle file sharing
    data = message.command[1]
    try:
        decode_file_id = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("ascii")
        if '_' in decode_file_id:
            pre, file_id = decode_file_id.split('_', 1)
        else:
            file_id = decode_file_id
            pre = ""
    except Exception as e:
        print(f"Decode error: {e}")
        return
    
    try:
        msg = await client.send_cached_media(chat_id=message.from_user.id, file_id=file_id, protect_content=True if pre == 'filep' else False)
        if msg.media:
            filetype = msg.media
            file = getattr(msg, filetype.value)
            title = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), str(getattr(file, 'file_name', 'file')).split()))
            size = get_size(getattr(file, 'file_size', 0))
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(file_name=title, file_size=size, file_caption='')
                except:
                    pass
            await msg.edit_caption(f_caption)
            
            if STREAM_MODE and (msg.video or msg.document):
                stream = f"{URL}watch/{str(msg.id)}/{quote_plus(get_name(msg))}?hash={get_hash(msg)}"
                download = f"{URL}{str(msg.id)}/{quote_plus(get_name(msg))}?hash={get_hash(msg)}"
                button = [[InlineKeyboardButton("📥 Download", url=download), InlineKeyboardButton('🎬 Watch', url=stream)]]
                await msg.edit_reply_markup(InlineKeyboardMarkup(button))
        
        k = await msg.reply(f"<b>⚠️ This File will be deleted in {AUTO_DELETE} minutes.\n\n📌 Please forward this File to your Saved Messages.</b>", quote=True)
        await asyncio.sleep(AUTO_DELETE_TIME)
        await msg.delete()
        await k.edit_text("<b>✅ Your File has been deleted!</b>")
        return
    except Exception as e:
        logger.error(f"Error sending file: {e}")

@Client.on_message(filters.command(['link']) & filters.private)
async def gen_link(client, message):
    me = await client.get_me()
    bot_data = mongo_db.bots.find_one({'bot_id': me.id})
    
    # Check bot mode (Public/Private)
    if bot_data and bot_data.get("bot_mode") == "Private":
        owner_id = bot_data.get("user_id")
        admins = bot_data.get("bot_admins", [])
        if message.from_user.id != owner_id and message.from_user.id not in admins:
            return await message.reply("❌ This bot is in Private mode. Only owner and admins can generate links.")
    
    replied = message.reply_to_message
    if not replied:
        return await message.reply('⚠️ Reply to a message to get a shareable link.')
    
    file_type = replied.media
    if not file_type:
        return await message.reply("❌ Reply to a supported media (Video, Audio, Document, Photo)")
    
    file_id = getattr(replied, str(file_type).split('.')[-1].replace('>', '').strip()).file_id
    string = f'file_{file_id}'
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user_id = message.from_user.id
    user = await get_user(user_id)
    share_link = f"https://t.me/{client.me.username}?start={outstr}"
    
    if user.get("shortener_api") and user.get("base_site"):
        try:
            from shortzy import Shortzy
            shortzy = Shortzy(api_key=user.get("shortener_api"), base_site=user.get("base_site"))
            short_link = await shortzy.convert(share_link)
            await message.reply(f"<b>✅ Here is your link:\n\n🔗 Short Link: {short_link}</b>")
        except Exception as e:
            await message.reply(f"<b>✅ Here is your link:\n\n🔗 Original Link: {share_link}</b>")
    else:
        await message.reply(f"<b>✅ Here is your link:\n\n🔗 Original Link: {share_link}</b>")

@Client.on_message(filters.command('api') & filters.private)
async def shortener_api_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command

    if len(cmd) == 1:
        s = script.SHORTENER_API_MESSAGE.format(base_site=user.get("base_site", "None"), shortener_api=user.get("shortener_api", "None"))
        return await m.reply(s)
    elif len(cmd) == 2:
        api = cmd[1].strip()
        if api.lower() == 'none':
            api = None
        await update_user_info(user_id, {"shortener_api": api})
        await m.reply("✅ Shortener API updated successfully")

@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    
    if len(cmd) == 1:
        text = f"<b>📌 Current base site: {user.get('base_site', 'None')}\n\n📝 Example: /base_site shortnerdomain.com\n\n🗑️ To remove: /base_site None</b>"
        return await m.reply(text=text, disable_web_page_preview=True)
    elif len(cmd) == 2:
        base_site = cmd[1].strip()
        if base_site.lower() == 'none':
            base_site = None
        if base_site and not domain(base_site):
            return await m.reply(text="❌ Invalid domain format!", disable_web_page_preview=True)
        await update_user_info(user_id, {"base_site": base_site})
        await m.reply("✅ Base Site updated successfully")

# ==================== CALLBACK HANDLER (FIXED) ====================

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    me = await client.get_me()
    bot_data = mongo_db.bots.find_one({'bot_id': me.id})
    owner_id = bot_data.get('user_id') if bot_data else 0
    
    print(f"Callback received: {query.data} from user {query.from_user.id}")
    
    # Close button
    if query.data == "close_data":
        await query.message.delete()
        return
    
    # Home/Start button
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('💝 Subscribe YouTube', url='https://youtube.com/@Tech_VJ')
        ],[
            InlineKeyboardButton('🔍 Support Group', url='https://t.me/vj_bot_disscussion'),
            InlineKeyboardButton('🤖 Update Channel', url='https://t.me/vj_bots')
        ],[
            InlineKeyboardButton('💁‍♀️ Help', callback_data='help'),
            InlineKeyboardButton('😊 About', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(
            text=script.CLONE_START_TXT.format(query.from_user.mention, me.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer()
        return
    
    # Help button
    elif query.data == "help":
        buttons = [[InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(
            text=script.CHELP_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer()
        return
    
    # About button
    elif query.data == "about":
        buttons = [[InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(
            text=script.CABOUT_TXT.format(me.mention, owner_id),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer()
        return
    
    # ========== CUSTOMIZATION MENU (Only for bot owner) ==========
    
    # Check if user is bot owner for customization
    if query.from_user.id != owner_id:
        await query.answer("⚠️ Only the bot owner can customize this bot!", show_alert=True)
        return
    
    # Customize menu - called from /clone command
    elif query.data.startswith("customize_"):
        bot_id = int(query.data.split("_")[1])
        bot_settings = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
        
        buttons = [[
            InlineKeyboardButton("📝 Start Text", callback_data=f"set_start_text_{bot_id}"),
            InlineKeyboardButton("🖼️ Start Picture", callback_data=f"set_start_pic_{bot_id}")
        ],[
            InlineKeyboardButton("🔘 Start Button", callback_data=f"set_start_button_{bot_id}"),
            InlineKeyboardButton("🔒 Force Subscribe", callback_data=f"set_fsub_{bot_id}")
        ],[
            InlineKeyboardButton("👑 Admins", callback_data=f"set_admins_{bot_id}"),
            InlineKeyboardButton("⚙️ Bot Mode", callback_data=f"set_mode_{bot_id}")
        ],[
            InlineKeyboardButton("📊 Bot Status", callback_data=f"bot_status_{bot_id}"),
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")
        ]]
        
        status_text = f"<b>🤖 Bot Customization Menu\n\n"
        status_text += f"📝 Start Text: {'✅ Set' if bot_settings.get('custom_start_text') else '❌ Default'}\n"
        status_text += f"🖼️ Start Picture: {'✅ Set' if bot_settings.get('custom_start_pic') else '❌ Default'}\n"
        status_text += f"🔘 Custom Buttons: {'✅ Set' if bot_settings.get('custom_buttons') else '❌ Default'}\n"
        status_text += f"🔒 Force Subscribe: {'✅ Enabled' if bot_settings.get('force_subscribe_channel') else '❌ Disabled'}\n"
        status_text += f"⚙️ Bot Mode: {bot_settings.get('bot_mode', 'Public')}\n"
        status_text += f"👑 Admins: {len(bot_settings.get('bot_admins', []))} admin(s)\n"
        status_text += f"📊 Users: {await clonedb.total_users_count(me.id)}\n</b>"
        
        await query.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()
        return
    
    # Set Start Text
    elif query.data.startswith("set_start_text_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action": "start_text", "bot_id": bot_id}
        
        buttons = [[
            InlineKeyboardButton("📝 Use Default", callback_data=f"default_start_text_{bot_id}"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data=f"customize_{bot_id}")
        ]]
        
        current = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
        current_text = current.get("custom_start_text", "Not Set")
        if len(current_text) > 100:
            current_text = current_text[:100] + "..."
        
        await query.message.edit_text(
            f"<b>📝 Customize Start Message\n\n"
            f"Current: <code>{current_text}</code>\n\n"
            f"📌 Send me the new start message text.\n"
            f"💡 Use {{mention}} for user mention\n"
            f"💡 Use {{bot_name}} for bot name</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
        return
    
    # Default Start Text
    elif query.data.startswith("default_start_text_"):
        bot_id = int(query.data.split("_")[3])
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$unset': {'custom_start_text': ""}})
        await query.answer("✅ Reset to default start text!", show_alert=True)
        # Refresh menu
        await show_customization_menu(client, query, bot_id)
        return
    
    # Set Start Picture
    elif query.data.startswith("set_start_pic_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action": "start_pic", "bot_id": bot_id}
        
        buttons = [[
            InlineKeyboardButton("🖼️ Use Default", callback_data=f"default_start_pic_{bot_id}"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data=f"customize_{bot_id}")
        ]]
        
        await query.message.edit_text(
            f"<b>🖼️ Customize Start Picture\n\n"
            f"📌 Send me a photo for start message.\n"
            f"💡 Forward a photo or send me an image URL.</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
        return
    
    # Default Start Picture
    elif query.data.startswith("default_start_pic_"):
        bot_id = int(query.data.split("_")[3])
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$unset': {'custom_start_pic': ""}})
        await query.answer("✅ Reset to default start picture!", show_alert=True)
        await show_customization_menu(client, query, bot_id)
        return
    
    # Set Start Button
    elif query.data.startswith("set_start_button_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action": "start_button", "bot_id": bot_id}
        
        buttons = [[
            InlineKeyboardButton("🗑️ Remove Buttons", callback_data=f"remove_buttons_{bot_id}"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data=f"customize_{bot_id}")
        ]]
        
        await query.message.edit_text(
            f"<b>🔘 Customize Start Buttons\n\n"
            f"📌 Format:\n"
            f"Single button: [Text][buttonurl:https://t.me/username]\n\n"
            f"Two buttons same row: [Btn1][buttonurl:url1][Btn2][buttonurl:url2:same]\n\n"
            f"Send me the button configuration.</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
        return
    
    # Remove Buttons
    elif query.data.startswith("remove_buttons_"):
        bot_id = int(query.data.split("_")[2])
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$unset': {'custom_buttons': ""}})
        await query.answer("✅ Removed custom buttons!", show_alert=True)
        await show_customization_menu(client, query, bot_id)
        return
    
    # Set Force Subscribe
    elif query.data.startswith("set_fsub_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action": "fsub", "bot_id": bot_id}
        
        await query.message.edit_text(
            f"<b>🔒 Force Subscribe Settings\n\n"
            f"📌 Send me the channel username (without @).\n"
            f"Example: vj_bots\n\n"
            f"To disable: Send 'none'</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"customize_{bot_id}")]])
        )
        await query.answer()
        return
    
    # Set Admins Menu
    elif query.data.startswith("set_admins_"):
        bot_id = int(query.data.split("_")[3])
        bot_settings = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
        current_admins = bot_settings.get("bot_admins", [])
        
        admin_text = "\n".join([f"👑 `{admin}`" for admin in current_admins]) if current_admins else "No admins set"
        
        buttons = [[
            InlineKeyboardButton("➕ Add Admin", callback_data=f"add_admin_{bot_id}"),
            InlineKeyboardButton("🗑️ Remove Admin", callback_data=f"remove_admin_{bot_id}")
        ],[
            InlineKeyboardButton("🔙 Back", callback_data=f"customize_{bot_id}")
        ]]
        
        await query.message.edit_text(
            f"<b>👑 Admin Management\n\n"
            f"Current Admins:\n{admin_text}\n\n"
            f"📌 Admins can generate links in Private mode.</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
        return
    
    # Add Admin
    elif query.data.startswith("add_admin_"):
        bot_id = int(query.data.split("_")[2])
        temp_custom_data[query.from_user.id] = {"action": "add_admin", "bot_id": bot_id}
        await query.message.edit_text(
            "<b>➕ Send me the Telegram User ID to add as admin.\n\nExample: 123456789</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"set_admins_{bot_id}")]])
        )
        await query.answer()
        return
    
    # Remove Admin
    elif query.data.startswith("remove_admin_"):
        bot_id = int(query.data.split("_")[2])
        temp_custom_data[query.from_user.id] = {"action": "remove_admin", "bot_id": bot_id}
        await query.message.edit_text(
            "<b>🗑️ Send me the Telegram User ID to remove from admins.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"set_admins_{bot_id}")]])
        )
        await query.answer()
        return
    
    # Set Bot Mode
    elif query.data.startswith("set_mode_"):
        bot_id = int(query.data.split("_")[3])
        bot_settings = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
        current_mode = bot_settings.get("bot_mode", "Public")
        
        buttons = [[
            InlineKeyboardButton("🌍 Public Mode", callback_data=f"mode_public_{bot_id}"),
            InlineKeyboardButton("🔒 Private Mode", callback_data=f"mode_private_{bot_id}")
        ],[
            InlineKeyboardButton("🔙 Back", callback_data=f"customize_{bot_id}")
        ]]
        
        await query.message.edit_text(
            f"<b>⚙️ Bot Mode Settings\n\n"
            f"Current Mode: {current_mode}\n\n"
            f"🌍 Public: Anyone can generate links\n"
            f"🔒 Private: Only Owner/Admins can generate links</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
        return
    
    # Mode Public
    elif query.data.startswith("mode_public_"):
        bot_id = int(query.data.split("_")[2])
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'bot_mode': 'Public'}})
        await query.answer("✅ Bot mode set to PUBLIC!", show_alert=True)
        await show_customization_menu(client, query, bot_id)
        return
    
    # Mode Private
    elif query.data.startswith("mode_private_"):
        bot_id = int(query.data.split("_")[2])
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'bot_mode': 'Private'}})
        await query.answer("✅ Bot mode set to PRIVATE!", show_alert=True)
        await show_customization_menu(client, query, bot_id)
        return
    
    # Bot Status
    elif query.data.startswith("bot_status_"):
        bot_id = int(query.data.split("_")[2])
        bot_settings = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
        users_count = await clonedb.total_users_count(me.id)
        
        status_text = f"<b>📊 Bot Statistics\n\n"
        status_text += f"🤖 Bot Name: {me.mention}\n"
        status_text += f"🆔 Bot ID: {me.id}\n"
        status_text += f"👥 Total Users: {users_count}\n"
        status_text += f"⚙️ Bot Mode: {bot_settings.get('bot_mode', 'Public')}\n"
        status_text += f"👑 Admins: {len(bot_settings.get('bot_admins', []))}\n"
        status_text += f"📝 Start Text: {'✅' if bot_settings.get('custom_start_text') else '❌'}\n"
        status_text += f"🖼️ Start Picture: {'✅' if bot_settings.get('custom_start_pic') else '❌'}\n"
        status_text += f"🔘 Custom Buttons: {'✅' if bot_settings.get('custom_buttons') else '❌'}\n"
        status_text += f"🔒 Force Subscribe: {'✅' if bot_settings.get('force_subscribe_channel') else '❌'}\n"
        status_text += f"📅 Created: {bot_settings.get('created_at', 'Unknown')}\n</b>"
        
        buttons = [[InlineKeyboardButton("🔙 Back to Menu", callback_data=f"customize_{bot_id}")]]
        await query.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()
        return

# ========== HELPER FUNCTIONS ==========

async def show_customization_menu(client, query, bot_id):
    """Show the customization menu"""
    buttons = [[
        InlineKeyboardButton("📝 Start Text", callback_data=f"set_start_text_{bot_id}"),
        InlineKeyboardButton("🖼️ Start Picture", callback_data=f"set_start_pic_{bot_id}")
    ],[
        InlineKeyboardButton("🔘 Start Button", callback_data=f"set_start_button_{bot_id}"),
        InlineKeyboardButton("🔒 Force Subscribe", callback_data=f"set_fsub_{bot_id}")
    ],[
        InlineKeyboardButton("👑 Admins", callback_data=f"set_admins_{bot_id}"),
        InlineKeyboardButton("⚙️ Bot Mode", callback_data=f"set_mode_{bot_id}")
    ],[
        InlineKeyboardButton("📊 Bot Status", callback_data=f"bot_status_{bot_id}"),
        InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")
    ]]
    
    bot_settings = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
    
    status_text = f"<b>🤖 Bot Customization Menu\n\n"
    status_text += f"📝 Start Text: {'✅ Set' if bot_settings.get('custom_start_text') else '❌ Default'}\n"
    status_text += f"🖼️ Start Picture: {'✅ Set' if bot_settings.get('custom_start_pic') else '❌ Default'}\n"
    status_text += f"🔘 Custom Buttons: {'✅ Set' if bot_settings.get('custom_buttons') else '❌ Default'}\n"
    status_text += f"🔒 Force Subscribe: {'✅ Enabled' if bot_settings.get('force_subscribe_channel') else '❌ Disabled'}\n"
    status_text += f"⚙️ Bot Mode: {bot_settings.get('bot_mode', 'Public')}\n"
    status_text += f"👑 Admins: {len(bot_settings.get('bot_admins', []))} admin(s)\n</b>"
    
    await query.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(buttons))

# ========== HANDLE TEXT INPUTS FOR CUSTOMIZATION ==========

@Client.on_message(filters.text & filters.private)
async def handle_customization_input(client, message):
    user_id = message.from_user.id
    
    if user_id not in temp_custom_data:
        return
    
    action_data = temp_custom_data[user_id]
    action = action_data.get("action")
    bot_id = action_data.get("bot_id")
    
    if action == "start_text":
        new_text = message.text
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'custom_start_text': new_text}})
        await message.reply("✅ Start text updated successfully!")
        del temp_custom_data[user_id]
        # Send menu
        await send_customization_menu(client, message, bot_id)
    
    elif action == "add_admin":
        try:
            admin_id = int(message.text.strip())
            bot_data = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
            current_admins = bot_data.get("bot_admins", [])
            if admin_id not in current_admins:
                current_admins.append(admin_id)
                mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'bot_admins': current_admins}})
                await message.reply(f"✅ Admin `{admin_id}` added successfully!")
            else:
                await message.reply("❌ This user is already an admin!")
            del temp_custom_data[user_id]
            await send_customization_menu(client, message, bot_id)
        except ValueError:
            await message.reply("❌ Invalid User ID! Please send a valid numeric ID.")
    
    elif action == "remove_admin":
        try:
            admin_id = int(message.text.strip())
            bot_data = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
            current_admins = bot_data.get("bot_admins", [])
            if admin_id in current_admins:
                current_admins.remove(admin_id)
                mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'bot_admins': current_admins}})
                await message.reply(f"✅ Admin `{admin_id}` removed successfully!")
            else:
                await message.reply("❌ This user is not an admin!")
            del temp_custom_data[user_id]
            await send_customization_menu(client, message, bot_id)
        except ValueError:
            await message.reply("❌ Invalid User ID! Please send a valid numeric ID.")
    
    elif action == "fsub":
        channel = message.text.strip().lower()
        if channel == "none":
            mongo_db.bots.update_one({'bot_id': bot_id}, {'$unset': {'force_subscribe_channel': ""}})
            await message.reply("✅ Force subscribe disabled!")
        else:
            mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'force_subscribe_channel': channel}})
            await message.reply(f"✅ Force subscribe set to @{channel}")
        del temp_custom_data[user_id]
        await send_customization_menu(client, message, bot_id)
    
    elif action == "start_button":
        button_text = message.text
        pattern = r'\[(.*?)\]\[buttonurl:(.*?)(?::same)?\]'
        matches = re.findall(pattern, button_text)
        
        if matches:
            buttons = []
            current_row = []
            for i, match in enumerate(matches):
                text, url = match
                current_row.append({"text": text, "url": url})
                if i + 1 < len(matches):
                    next_match = matches[i + 1]
                    if f"[{next_match[0]}][buttonurl:{next_match[1]}" in button_text and ":same" not in button_text.split(f"[{next_match[0]}]")[0]:
                        buttons.append(current_row)
                        current_row = []
            if current_row:
                buttons.append(current_row)
            
            mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'custom_buttons': json.dumps(buttons)}})
            await message.reply(f"✅ Custom buttons added! {len(buttons)} row(s)")
        else:
            await message.reply("❌ Invalid button format!")
        
        del temp_custom_data[user_id]
        await send_customization_menu(client, message, bot_id)

@Client.on_message(filters.photo & filters.private)
async def handle_photo_customization(client, message):
    user_id = message.from_user.id
    
    if user_id not in temp_custom_data:
        return
    
    action_data = temp_custom_data[user_id]
    action = action_data.get("action")
    bot_id = action_data.get("bot_id")
    
    if action == "start_pic":
        photo_id = message.photo.file_id
        mongo_db.bots.update_one({'bot_id': bot_id}, {'$set': {'custom_start_pic': photo_id}})
        await message.reply("✅ Start picture updated successfully!")
        del temp_custom_data[user_id]
        await send_customization_menu(client, message, bot_id)

async def send_customization_menu(client, message, bot_id):
    """Send customization menu via message"""
    buttons = [[
        InlineKeyboardButton("📝 Start Text", callback_data=f"set_start_text_{bot_id}"),
        InlineKeyboardButton("🖼️ Start Picture", callback_data=f"set_start_pic_{bot_id}")
    ],[
        InlineKeyboardButton("🔘 Start Button", callback_data=f"set_start_button_{bot_id}"),
        InlineKeyboardButton("🔒 Force Subscribe", callback_data=f"set_fsub_{bot_id}")
    ],[
        InlineKeyboardButton("👑 Admins", callback_data=f"set_admins_{bot_id}"),
        InlineKeyboardButton("⚙️ Bot Mode", callback_data=f"set_mode_{bot_id}")
    ],[
        InlineKeyboardButton("📊 Bot Status", callback_data=f"bot_status_{bot_id}"),
        InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")
    ]]
    
    bot_settings = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
    
    status_text = f"<b>🤖 Bot Customization Menu\n\n"
    status_text += f"📝 Start Text: {'✅ Set' if bot_settings.get('custom_start_text') else '❌ Default'}\n"
    status_text += f"🖼️ Start Picture: {'✅ Set' if bot_settings.get('custom_start_pic') else '❌ Default'}\n"
    status_text += f"🔘 Custom Buttons: {'✅ Set' if bot_settings.get('custom_buttons') else '❌ Default'}\n"
    status_text += f"🔒 Force Subscribe: {'✅ Enabled' if bot_settings.get('force_subscribe_channel') else '❌ Disabled'}\n"
    status_text += f"⚙️ Bot Mode: {bot_settings.get('bot_mode', 'Public')}\n"
    status_text += f"👑 Admins: {len(bot_settings.get('bot_admins', []))} admin(s)\n</b>"
    
    await message.reply_text(status_text, reply_markup=InlineKeyboardMarkup(buttons))
