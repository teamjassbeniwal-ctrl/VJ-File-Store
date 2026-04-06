# clone_plugins/commands.py – copy exactly
# (I'm providing the full file again to ensure no missing parts)

import os, logging, random, asyncio, base64, json, re
from datetime import datetime
from Script import script
from validators import domain
from clone_plugins.dbusers import clonedb
from clone_plugins.users_api import get_user, update_user_info
from pyrogram import Client, filters, enums
from config import PICS, CUSTOM_FILE_CAPTION, AUTO_DELETE_TIME, AUTO_DELETE, URL, STREAM_MODE, CLONE_DB_URI
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, CallbackQuery
from urllib.parse import quote_plus
from pymongo import MongoClient
from TechVJ.utils.file_properties import get_name, get_hash

logger = logging.getLogger(__name__)

# Must match the database name used in plugins/clone.py
CLONE_DB_NAME = "cloned_vjbotz"

mongo_client = MongoClient(CLONE_DB_URI)
mongo_db = mongo_client[CLONE_DB_NAME]
temp_custom_data = {}

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    i = 0
    while size >= 1024 and i < len(units)-1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    me = await client.get_me()
    bot_data = mongo_db.bots.find_one({'bot_id': me.id})
    if not await clonedb.is_user_exist(me.id, message.from_user.id):
        await clonedb.add_user(me.id, message.from_user.id)
    if len(message.command) != 2:
        custom_txt = bot_data.get("custom_start_text") if bot_data else None
        custom_pic = bot_data.get("custom_start_pic") if bot_data else None
        custom_btns = bot_data.get("custom_buttons") if bot_data else None
        force_ch = bot_data.get("force_subscribe_channel") if bot_data else None
        if force_ch:
            try:
                member = await client.get_chat_member(f"@{force_ch}", message.from_user.id)
                if member.status in ["left","kicked"]:
                    await message.reply_text(f"⚠️ Please join @{force_ch}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join", url=f"https://t.me/{force_ch}")]]))
                    return
            except: pass
        buttons = [[InlineKeyboardButton("💝 YouTube", url="https://youtube.com/@Tech_VJ")],
                   [InlineKeyboardButton("🔍 Support", url="https://t.me/vj_bot_disscussion"), InlineKeyboardButton("📢 Updates", url="https://t.me/vj_bots")],
                   [InlineKeyboardButton("💁 Help", callback_data="help"), InlineKeyboardButton("😊 About", callback_data="about")]]
        if custom_btns:
            try:
                for row in json.loads(custom_btns):
                    buttons.append([InlineKeyboardButton(btn['text'], url=btn['url']) for btn in row])
            except: pass
        reply_markup = InlineKeyboardMarkup(buttons)
        start_text = custom_txt.replace("{mention}",message.from_user.mention).replace("{bot_name}",me.mention) if custom_txt else script.CLONE_START_TXT.format(message.from_user.mention, me.mention)
        if custom_pic:
            try: await message.reply_photo(custom_pic, caption=start_text, reply_markup=reply_markup)
            except: await message.reply_photo(random.choice(PICS), caption=start_text, reply_markup=reply_markup)
        else:
            await message.reply_photo(random.choice(PICS), caption=start_text, reply_markup=reply_markup)
        return
    data = message.command[1]
    try:
        file_id = base64.urlsafe_b64decode(data + "="*(-len(data)%4)).decode().split('_',1)[1]
        msg = await client.send_cached_media(message.from_user.id, file_id)
        if msg.media:
            file = getattr(msg, msg.media.value)
            title = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), str(getattr(file,'file_name','file')).split()))
            size = get_size(getattr(file,'file_size',0))
            cap = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try: cap = CUSTOM_FILE_CAPTION.format(file_name=title, file_size=size, file_caption='')
                except: pass
            await msg.edit_caption(cap)
            if STREAM_MODE and (msg.video or msg.document):
                stream = f"{URL}watch/{msg.id}/{quote_plus(get_name(msg))}?hash={get_hash(msg)}"
                down = f"{URL}{msg.id}/{quote_plus(get_name(msg))}?hash={get_hash(msg)}"
                await msg.edit_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download",url=down), InlineKeyboardButton("🎬 Watch",url=stream)]]))
        k = await msg.reply(f"⚠️ File deleted in {AUTO_DELETE} min", quote=True)
        await asyncio.sleep(AUTO_DELETE_TIME)
        await msg.delete()
        await k.edit_text("✅ Deleted")
    except Exception as e:
        logger.error(e)

@Client.on_message(filters.command(['link']) & filters.private)
async def gen_link(client, message):
    me = await client.get_me()
    bot_data = mongo_db.bots.find_one({'bot_id': me.id})
    if bot_data and bot_data.get("bot_mode") == "Private":
        owner = bot_data.get("user_id")
        admins = bot_data.get("bot_admins", [])
        if message.from_user.id != owner and message.from_user.id not in admins:
            return await message.reply("❌ Private mode: only owner/admins")
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply("⚠️ Reply to a media file")
    media = message.reply_to_message
    file_id = media.document.file_id if media.document else media.video.file_id if media.video else media.audio.file_id if media.audio else media.photo.file_id
    out = base64.urlsafe_b64encode(f"file_{file_id}".encode()).decode().strip("=")
    link = f"https://t.me/{client.me.username}?start={out}"
    user = await get_user(message.from_user.id)
    if user.get("shortener_api") and user.get("base_site"):
        try:
            from shortzy import Shortzy
            short = await Shortzy(user.get("shortener_api"), user.get("base_site")).convert(link)
            await message.reply(f"✅ Short Link: {short}")
        except:
            await message.reply(f"✅ Link: {link}")
    else:
        await message.reply(f"✅ Link: {link}")

@Client.on_message(filters.command('api') & filters.private)
async def set_api(client, m):
    user = await get_user(m.from_user.id)
    if len(m.command)==1:
        return await m.reply(script.SHORTENER_API_MESSAGE.format(base_site=user.get("base_site","None"), shortener_api=user.get("shortener_api","None")))
    api = m.command[1].strip()
    await update_user_info(m.from_user.id, {"shortener_api": None if api.lower()=='none' else api})
    await m.reply("✅ API updated")

@Client.on_message(filters.command("base_site") & filters.private)
async def set_base(client, m):
    user = await get_user(m.from_user.id)
    if len(m.command)==1:
        return await m.reply(f"Current base: {user.get('base_site','None')}\n/base_site domain.com\n/base_site None")
    site = m.command[1].strip()
    if site.lower()=='none':
        site = None
    elif site and not domain(site):
        return await m.reply("❌ Invalid domain")
    await update_user_info(m.from_user.id, {"base_site": site})
    await m.reply("✅ Base site updated")

@Client.on_callback_query()
async def cb_handler(client, query):
    print(f"🔔 CALLBACK: {query.data} from {query.from_user.id}")
    me = await client.get_me()
    bot_data = mongo_db.bots.find_one({'bot_id': me.id})
    owner_id = bot_data.get('user_id') if bot_data else 0
    print(f"Owner ID: {owner_id}, Bot ID: {me.id}")

    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "start":
        buttons = [[InlineKeyboardButton("💝 YouTube", url="https://youtube.com/@Tech_VJ")],
                   [InlineKeyboardButton("🔍 Support", url="https://t.me/vj_bot_disscussion"), InlineKeyboardButton("📢 Updates", url="https://t.me/vj_bots")],
                   [InlineKeyboardButton("💁 Help", callback_data="help"), InlineKeyboardButton("😊 About", callback_data="about")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(script.CLONE_START_TXT.format(query.from_user.mention, me.mention), reply_markup=InlineKeyboardMarkup(buttons))
    elif query.data == "help":
        btns = [[InlineKeyboardButton("🏠 Home", callback_data="start"), InlineKeyboardButton("🔒 Close", callback_data="close_data")]]
        await query.message.edit_text(script.CHELP_TXT, reply_markup=InlineKeyboardMarkup(btns))
    elif query.data == "about":
        btns = [[InlineKeyboardButton("🏠 Home", callback_data="start"), InlineKeyboardButton("🔒 Close", callback_data="close_data")]]
        await query.message.edit_text(script.CABOUT_TXT.format(me.mention, owner_id), reply_markup=InlineKeyboardMarkup(btns))
    elif query.data.startswith("customize_"):
        if query.from_user.id != owner_id:
            await query.answer("⚠️ Only the bot owner can customize!", show_alert=True)
            return
        bot_id = int(query.data.split("_")[1])
        s = mongo_db.bots.find_one({'bot_id': bot_id}) or {}
        btns = [[InlineKeyboardButton("📝 Start Text", callback_data=f"set_start_text_{bot_id}"), InlineKeyboardButton("🖼️ Start Pic", callback_data=f"set_start_pic_{bot_id}")],
                [InlineKeyboardButton("🔘 Buttons", callback_data=f"set_start_button_{bot_id}"), InlineKeyboardButton("🔒 Force Sub", callback_data=f"set_fsub_{bot_id}")],
                [InlineKeyboardButton("👑 Admins", callback_data=f"set_admins_{bot_id}"), InlineKeyboardButton("⚙️ Mode", callback_data=f"set_mode_{bot_id}")],
                [InlineKeyboardButton("📊 Status", callback_data=f"bot_status_{bot_id}"), InlineKeyboardButton("🏠 Back", callback_data="start")]]
        txt = f"<b>Customize</b>\n📝 Text: {'✅' if s.get('custom_start_text') else '❌'}\n🖼️ Pic: {'✅' if s.get('custom_start_pic') else '❌'}\n🔘 Buttons: {'✅' if s.get('custom_buttons') else '❌'}\n🔒 Force: {'✅' if s.get('force_subscribe_channel') else '❌'}\n⚙️ Mode: {s.get('bot_mode','Public')}\n👑 Admins: {len(s.get('bot_admins',[]))}"
        await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(btns))
        await query.answer()
    elif query.data.startswith("set_start_text_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action":"start_text","bot_id":bot_id}
        await query.message.edit_text("Send new start text (use {mention} {bot_name})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]))
    elif query.data.startswith("default_start_text_"):
        bot_id = int(query.data.split("_")[3])
        mongo_db.bots.update_one({'bot_id':bot_id},{'$unset':{'custom_start_text':""}})
        await query.answer("Reset to default", show_alert=True)
        await cb_handler(client, type('obj',(object,),{'data':f"customize_{bot_id}",'message':query.message,'from_user':query.from_user})())
    elif query.data.startswith("set_start_pic_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action":"start_pic","bot_id":bot_id}
        await query.message.edit_text("Send a photo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]))
    elif query.data.startswith("default_start_pic_"):
        bot_id = int(query.data.split("_")[3])
        mongo_db.bots.update_one({'bot_id':bot_id},{'$unset':{'custom_start_pic':""}})
        await query.answer("Reset default pic", show_alert=True)
        await cb_handler(client, type('obj',(object,),{'data':f"customize_{bot_id}",'message':query.message,'from_user':query.from_user})())
    elif query.data.startswith("set_start_button_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action":"start_button","bot_id":bot_id}
        await query.message.edit_text("Send buttons: [Text][buttonurl:url] or [A][url1][B][url2:same]", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Remove", callback_data=f"remove_buttons_{bot_id}"), InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]))
    elif query.data.startswith("remove_buttons_"):
        bot_id = int(query.data.split("_")[2])
        mongo_db.bots.update_one({'bot_id':bot_id},{'$unset':{'custom_buttons':""}})
        await query.answer("Buttons removed", show_alert=True)
        await cb_handler(client, type('obj',(object,),{'data':f"customize_{bot_id}",'message':query.message,'from_user':query.from_user})())
    elif query.data.startswith("set_fsub_"):
        bot_id = int(query.data.split("_")[3])
        temp_custom_data[query.from_user.id] = {"action":"fsub","bot_id":bot_id}
        await query.message.edit_text("Send channel username (without @) or 'none'", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]))
    elif query.data.startswith("set_admins_"):
        bot_id = int(query.data.split("_")[3])
        s = mongo_db.bots.find_one({'bot_id':bot_id}) or {}
        admins = s.get("bot_admins",[])
        txt = "Admins:\n"+"\n".join([f"`{a}`" for a in admins]) if admins else "No admins"
        btns = [[InlineKeyboardButton("➕ Add", callback_data=f"add_admin_{bot_id}"), InlineKeyboardButton("🗑️ Remove", callback_data=f"remove_admin_{bot_id}")],[InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]
        await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(btns))
    elif query.data.startswith("add_admin_"):
        bot_id = int(query.data.split("_")[2])
        temp_custom_data[query.from_user.id] = {"action":"add_admin","bot_id":bot_id}
        await query.message.edit_text("Send user ID", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"set_admins_{bot_id}")]]))
    elif query.data.startswith("remove_admin_"):
        bot_id = int(query.data.split("_")[2])
        temp_custom_data[query.from_user.id] = {"action":"remove_admin","bot_id":bot_id}
        await query.message.edit_text("Send user ID to remove", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"set_admins_{bot_id}")]]))
    elif query.data.startswith("set_mode_"):
        bot_id = int(query.data.split("_")[3])
        s = mongo_db.bots.find_one({'bot_id':bot_id}) or {}
        mode = s.get("bot_mode","Public")
        btns = [[InlineKeyboardButton("🌍 Public", callback_data=f"mode_public_{bot_id}"), InlineKeyboardButton("🔒 Private", callback_data=f"mode_private_{bot_id}")],[InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]
        await query.message.edit_text(f"Current: {mode}", reply_markup=InlineKeyboardMarkup(btns))
    elif query.data.startswith("mode_public_"):
        bot_id = int(query.data.split("_")[2])
        mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'bot_mode':'Public'}})
        await query.answer("Public mode", show_alert=True)
        await cb_handler(client, type('obj',(object,),{'data':f"customize_{bot_id}",'message':query.message,'from_user':query.from_user})())
    elif query.data.startswith("mode_private_"):
        bot_id = int(query.data.split("_")[2])
        mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'bot_mode':'Private'}})
        await query.answer("Private mode", show_alert=True)
        await cb_handler(client, type('obj',(object,),{'data':f"customize_{bot_id}",'message':query.message,'from_user':query.from_user})())
    elif query.data.startswith("bot_status_"):
        bot_id = int(query.data.split("_")[2])
        s = mongo_db.bots.find_one({'bot_id':bot_id}) or {}
        users = await clonedb.total_users_count(me.id)
        txt = f"<b>Status</b>\nUsers: {users}\nMode: {s.get('bot_mode','Public')}\nAdmins: {len(s.get('bot_admins',[]))}\nStart Text: {'✅' if s.get('custom_start_text') else '❌'}\nStart Pic: {'✅' if s.get('custom_start_pic') else '❌'}\nButtons: {'✅' if s.get('custom_buttons') else '❌'}\nForce: {'✅' if s.get('force_subscribe_channel') else '❌'}"
        await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"customize_{bot_id}")]]))

@Client.on_message(filters.text & filters.private)
async def handle_text(client, message):
    uid = message.from_user.id
    if uid not in temp_custom_data: return
    data = temp_custom_data[uid]
    action, bot_id = data["action"], data["bot_id"]
    if action == "start_text":
        mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'custom_start_text':message.text}})
        await message.reply("✅ Start text updated")
    elif action == "add_admin":
        try:
            aid = int(message.text.strip())
            b = mongo_db.bots.find_one({'bot_id':bot_id}) or {}
            admins = b.get("bot_admins",[])
            if aid not in admins:
                admins.append(aid)
                mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'bot_admins':admins}})
                await message.reply(f"✅ Admin {aid} added")
            else:
                await message.reply("Already admin")
        except:
            await message.reply("Invalid ID")
    elif action == "remove_admin":
        try:
            aid = int(message.text.strip())
            b = mongo_db.bots.find_one({'bot_id':bot_id}) or {}
            admins = b.get("bot_admins",[])
            if aid in admins:
                admins.remove(aid)
                mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'bot_admins':admins}})
                await message.reply(f"✅ Admin {aid} removed")
            else:
                await message.reply("Not an admin")
        except:
            await message.reply("Invalid ID")
    elif action == "fsub":
        ch = message.text.strip().lower()
        if ch == "none":
            mongo_db.bots.update_one({'bot_id':bot_id},{'$unset':{'force_subscribe_channel':""}})
            await message.reply("Force subscribe disabled")
        else:
            mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'force_subscribe_channel':ch}})
            await message.reply(f"Force subscribe @{ch}")
    elif action == "start_button":
        pat = r'\[(.*?)\]\[buttonurl:(.*?)(?::same)?\]'
        matches = re.findall(pat, message.text)
        if matches:
            btns = []
            row = []
            for i, (txt, url) in enumerate(matches):
                row.append({"text":txt,"url":url})
                if i+1 < len(matches) and ":same" not in message.text.split(f"[{matches[i+1][0]}]")[0]:
                    btns.append(row)
                    row = []
            if row: btns.append(row)
            mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'custom_buttons':json.dumps(btns)}})
            await message.reply(f"✅ {len(btns)} row(s) added")
        else:
            await message.reply("Invalid format")
    del temp_custom_data[uid]
    fake_cb = type('obj',(object,),{'data':f"customize_{bot_id}",'message':message,'from_user':message.from_user})()
    await cb_handler(client, fake_cb)

@Client.on_message(filters.photo & filters.private)
async def handle_photo(client, message):
    uid = message.from_user.id
    if uid not in temp_custom_data: return
    data = temp_custom_data[uid]
    if data.get("action") == "start_pic":
        bot_id = data["bot_id"]
        mongo_db.bots.update_one({'bot_id':bot_id},{'$set':{'custom_start_pic':message.photo.file_id}})
        await message.reply("✅ Start picture updated")
        del temp_custom_data[uid]
        fake_cb = type('obj',(object,),{'data':f"customize_{bot_id}",'message':message,'from_user':message.from_user})()
        await cb_handler(client, fake_cb)

print("✅ clone_plugins/commands.py loaded successfully")
