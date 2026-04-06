# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import logging
import random
import asyncio
import re
import json
import base64
from urllib.parse import quote_plus
from Script import script
from validators import domain
from plugins.dbusers import db
from pyrogram import Client, filters, enums
from plugins.users_api import get_user, update_user_info
from pyrogram.errors import FloodWait
from pyrogram.types import *
from utils import verify_user, check_token, check_verification, get_token, get_short_link
from config import *
from TechVJ.utils.file_properties import get_name, get_hash

logger = logging.getLogger(__name__)
BATCH_FILES = {}

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def formate_file_name(file_name):
    return ' '.join(filter(lambda x: not x.startswith('http') and not x.startswith('@') and not x.startswith('www.'), file_name.split()))

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    username = client.me.username
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(message.from_user.id, message.from_user.mention))
    
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('💝 Subscribe YouTube', url='https://youtube.com/@Tech_VJ')
        ],[
            InlineKeyboardButton('🔍 Support Group', url='https://t.me/vj_bot_disscussion'),
            InlineKeyboardButton('🤖 Update Channel', url='https://t.me/vj_bots')
        ],[
            InlineKeyboardButton('💁‍♀️ Help', callback_data='help'),
            InlineKeyboardButton('😊 About', callback_data='about')
        ]]
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('🤖 Create Your Own Clone Bot', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        me = client.me
        await message.reply_photo(photo=random.choice(PICS), caption=script.START_TXT.format(message.from_user.mention, me.mention), reply_markup=reply_markup)
        return
    
    data = message.command[1]
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
    
    if data.split("-", 1)[0] == "verify":
        userid = data.split("-", 2)[1]
        token = data.split("-", 3)[2]
        if str(message.from_user.id) != str(userid):
            return await message.reply_text(text="<b>Invalid link or Expired link !</b>", protect_content=True)
        is_valid = await check_token(client, userid, token)
        if is_valid == True:
            await message.reply_text(text=f"<b>Hey {message.from_user.mention}, You are successfully verified !</b>", protect_content=True)
            await verify_user(client, userid, token)
        else:
            return await message.reply_text(text="<b>Invalid link or Expired link !</b>", protect_content=True)
    
    elif data.split("-", 1)[0] == "BATCH":
        if not await check_verification(client, message.from_user.id) and VERIFY_MODE == True:
            btn = [[InlineKeyboardButton("Verify", url=await get_token(client, message.from_user.id, f"https://telegram.me/{username}?start="))]]
            if VERIFY_TUTORIAL:
                btn.append([InlineKeyboardButton("How To Open Link & Verify", url=VERIFY_TUTORIAL)])
            await message.reply_text(text="<b>You are not verified ! Kindly verify to continue !</b>", protect_content=True, reply_markup=InlineKeyboardMarkup(btn))
            return
        
        sts = await message.reply("**Please wait...**")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            decode_file_id = base64.urlsafe_b64decode(file_id + "=" * (-len(file_id) % 4)).decode("ascii")
            msg = await client.get_messages(LOG_CHANNEL, int(decode_file_id))
            media = getattr(msg, msg.media.value)
            file_id_download = media.file_id
            file = await client.download_media(file_id_download)
            try:
                with open(file, 'r') as file_data:
                    msgs = json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        
        filesarr = []
        for msg in msgs:
            channel_id = int(msg.get("channel_id"))
            msgid = msg.get("msg_id")
            info = await client.get_messages(channel_id, int(msgid))
            if info.media:
                file_type = info.media
                file = getattr(info, file_type.value)
                f_caption = getattr(info, 'caption', '')
                if f_caption:
                    f_caption = f"@VJ_Bots {f_caption.html}"
                old_title = getattr(file, "file_name", "")
                title = formate_file_name(old_title)
                size = get_size(int(file.file_size))
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption = BATCH_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                    except:
                        pass
                if f_caption is None:
                    f_caption = f"@VJ_Bots {title}"
                if STREAM_MODE == True:
                    if info.video or info.document:
                        log_msg = info
                        stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                        download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                        button = [[InlineKeyboardButton("📥 Download", url=download), InlineKeyboardButton('🎬 Watch', url=stream)]]
                        reply_markup = InlineKeyboardMarkup(button)
                else:
                    reply_markup = None
                try:
                    msg_copy = await info.copy(chat_id=message.from_user.id, caption=f_caption, protect_content=False, reply_markup=reply_markup)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    msg_copy = await info.copy(chat_id=message.from_user.id, caption=f_caption, protect_content=False, reply_markup=reply_markup)
                except:
                    continue
            else:
                try:
                    msg_copy = await info.copy(chat_id=message.from_user.id, protect_content=False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    msg_copy = await info.copy(chat_id=message.from_user.id, protect_content=False)
                except:
                    continue
            filesarr.append(msg_copy)
            await asyncio.sleep(1)
        await sts.delete()
        if AUTO_DELETE_MODE == True:
            k = await client.send_message(chat_id=message.from_user.id, text=f"<b>⚠️ This File will be deleted in {AUTO_DELETE} minutes (Due to Copyright Issues).\n\n📌 Please forward this File to your Saved Messages and Start Download there</b>")
            await asyncio.sleep(AUTO_DELETE_TIME)
            for x in filesarr:
                try:
                    await x.delete()
                except:
                    pass
            await k.edit_text("<b>✅ Your Files have been successfully deleted!</b>")
        return

    if not await check_verification(client, message.from_user.id) and VERIFY_MODE == True:
        btn = [[InlineKeyboardButton("Verify", url=await get_token(client, message.from_user.id, f"https://telegram.me/{username}?start="))]]
        if VERIFY_TUTORIAL:
            btn.append([InlineKeyboardButton("How To Open Link & Verify", url=VERIFY_TUTORIAL)])
        await message.reply_text(text="<b>You are not verified ! Kindly verify to continue !</b>", protect_content=True, reply_markup=InlineKeyboardMarkup(btn))
        return
    
    try:
        decode_file_id = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("ascii")
        if '_' in decode_file_id:
            pre, decode_file_id = decode_file_id.split("_", 1)
        msg = await client.get_messages(LOG_CHANNEL, int(decode_file_id))
        if msg.media:
            media = getattr(msg, msg.media.value)
            title = formate_file_name(media.file_name)
            size = get_size(media.file_size)
            f_caption = f"@VJ_Bots <code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    pass
            if STREAM_MODE == True:
                if msg.video or msg.document:
                    log_msg = msg
                    stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    button = [[InlineKeyboardButton("📥 Download", url=download), InlineKeyboardButton('🎬 Watch', url=stream)]]
                    reply_markup = InlineKeyboardMarkup(button)
            else:
                reply_markup = None
            del_msg = await msg.copy(chat_id=message.from_user.id, caption=f_caption, reply_markup=reply_markup, protect_content=False)
        else:
            del_msg = await msg.copy(chat_id=message.from_user.id, protect_content=False)
        if AUTO_DELETE_MODE == True:
            k = await client.send_message(chat_id=message.from_user.id, text=f"<b>⚠️ This File will be deleted in {AUTO_DELETE} minutes (Due to Copyright Issues).\n\n📌 Please forward this File to your Saved Messages and Start Download there</b>")
            await asyncio.sleep(AUTO_DELETE_TIME)
            try:
                await del_msg.delete()
            except:
                pass
            await k.edit_text("<b>✅ Your File has been successfully deleted!</b>")
        return
    except Exception as e:
        logger.error(f"Error in start: {e}")

@Client.on_message(filters.command(['link']) & filters.private)
async def gen_link(client, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply('⚠️ Reply to a message to get a shareable link.')
    
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO]:
        return await message.reply("❌ Reply to a supported media (Video, Audio, Document, Photo)")
    
    post = await replied.copy(LOG_CHANNEL)
    file_id = str(post.id)
    string = f"file_{file_id}"
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if WEBSITE_URL_MODE == True:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{client.me.username}?start={outstr}"
    
    if user.get("base_site") and user.get("shortener_api"):
        short_link = await get_short_link(user, share_link)
        await message.reply(f"<b>✅ Here is your link:\n\n🔗 Short Link: {short_link}</b>")
    else:
        await message.reply(f"<b>✅ Here is your link:\n\n🔗 Original Link: {share_link}</b>")

@Client.on_message(filters.command(['batch']) & filters.private)
async def gen_batch(client, message):
    user_id = message.from_user.id
    
    # Ask for first message
    first_prompt = await client.ask(
        chat_id=user_id,
        text="<b>📌 Forward The First Message From Your Batch Channel (With Forward Tag).. Or Give Me First Message Link From Your Batch Channel\n\n⚠️ Note: Make sure this bot is admin in your channel with full rights</b>",
        timeout=60
    )
    
    if first_prompt.text and first_prompt.text.lower() == '/cancel':
        return await first_prompt.reply("<b>❌ Cancelled!</b>")
    
    # Get first message info
    if first_prompt.forward_from_chat:
        f_chat_id = first_prompt.forward_from_chat.id
        f_msg_id = first_prompt.forward_from_message_id
    elif first_prompt.text and 't.me/' in first_prompt.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(first_prompt.text.strip())
        if match:
            f_chat_id = match.group(4)
            f_msg_id = int(match.group(5))
            if str(f_chat_id).isnumeric():
                f_chat_id = int("-100" + str(f_chat_id))
        else:
            return await first_prompt.reply("❌ Invalid input. Please forward a message or send a valid link.")
    else:
        return await first_prompt.reply("❌ Invalid input. Please forward a message or send a valid link.")
    
    # Ask for last message
    last_prompt = await client.ask(
        chat_id=user_id,
        text="<b>📌 Forward The Last Message From Your Batch Channel (With Forward Tag).. Or Give Me Last Message Link From Your Batch Channel\n\n⚠️ Note: Make sure this bot is admin in your channel with full rights</b>",
        timeout=60
    )
    
    if last_prompt.text and last_prompt.text.lower() == '/cancel':
        return await last_prompt.reply("<b>❌ Cancelled!</b>")
    
    # Get last message info
    if last_prompt.forward_from_chat:
        l_chat_id = last_prompt.forward_from_chat.id
        l_msg_id = last_prompt.forward_from_message_id
    elif last_prompt.text and 't.me/' in last_prompt.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(last_prompt.text.strip())
        if match:
            l_chat_id = match.group(4)
            l_msg_id = int(match.group(5))
            if str(l_chat_id).isnumeric():
                l_chat_id = int("-100" + str(l_chat_id))
        else:
            return await last_prompt.reply("❌ Invalid input. Please forward a message or send a valid link.")
    else:
        return await last_prompt.reply("❌ Invalid input. Please forward a message or send a valid link.")
    
    if f_chat_id != l_chat_id:
        return await last_prompt.reply("❌ Chat ids not matched. First and last message must be from same channel.")
    
    sts = await message.reply("**🔄 Generating batch link...**")
    
    outlist = []
    og_msg = 0
    
    try:
        async for msg in client.iter_messages(f_chat_id, l_msg_id, f_msg_id):
            if msg.empty or msg.service:
                continue
            file = {"channel_id": f_chat_id, "msg_id": msg.id}
            og_msg += 1
            outlist.append(file)
    except Exception as e:
        return await sts.edit(f"❌ Error: {e}")
    
    with open(f"batchmode_{user_id}.json", "w") as out:
        json.dump(outlist, out)
    
    post = await client.send_document(LOG_CHANNEL, f"batchmode_{user_id}.json", file_name="Batch.json", caption="📦 Batch Generated For Filestore.")
    os.remove(f"batchmode_{user_id}.json")
    
    string = str(post.id)
    file_id = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user = await get_user(user_id)
    
    if WEBSITE_URL_MODE == True:
        share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}"
    else:
        share_link = f"https://t.me/{client.me.username}?start=BATCH-{file_id}"
    
    if user.get("base_site") and user.get("shortener_api"):
        short_link = await get_short_link(user, share_link)
        await sts.edit(f"<b>✅ Here is your batch link:\n\n🔗 Short Link: {short_link}\n\n📁 Total Files: {og_msg}</b>")
    else:
        await sts.edit(f"<b>✅ Here is your batch link:\n\n🔗 Original Link: {share_link}\n\n📁 Total Files: {og_msg}</b>")

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
        await m.reply("<b>✅ Shortener API updated successfully</b>")

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
        await m.reply("<b>✅ Base Site updated successfully</b>")

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "about":
        buttons = [[InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        me2 = (await client.get_me()).mention
        await query.message.edit_text(text=script.ABOUT_TXT.format(me2), reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
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
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('🤖 Create Your Own Clone Bot', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        me2 = (await client.get_me()).mention
        await query.message.edit_text(text=script.START_TXT.format(query.from_user.mention, me2), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "clone":
        buttons = [[InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.CLONE_TXT.format(query.from_user.mention), reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
    elif query.data == "help":
        buttons = [[InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.HELP_TXT, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
