import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mochi.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, VideoMessage,
    FileMessage, AudioMessage, StickerMessage, JoinEvent,
    MemberJoinedEvent, FollowEvent
)
from linebot.models import TextSendMessage

from database import init_db, get_group_settings, upsert_group_settings, is_admin
from handlers.message_handler import handle_text_message
from handlers.media_handler import (
    save_image, save_video, save_file, save_audio, append_chat_log
)
from handlers.email_sender import send_media_notification
from handlers.bill_reader import process_bill_async
from scheduler import start_scheduler, stop_scheduler
from admin.blueprint import admin_bp

# ─── Init ──────────────────────────────────────────────────────────────────────
init_db()

ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
BOT_NAME = os.environ.get('BOT_NAME', 'น้องโมจิ')
STORAGE_PATH = os.environ.get('STORAGE_PATH', './storage')
os.makedirs(STORAGE_PATH, exist_ok=True)

line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'mochi-secret-key-change-me')
app.register_blueprint(admin_bp)
start_scheduler(line_bot_api)

# ─── Webhook ───────────────────────────────────────────────────────────────────

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        # Always 200 on processing errors — a 500 makes LINE retry the same
        # event, which would duplicate saved files / bills. Log and move on.
        logger.error(f'Webhook handler error: {e}', exc_info=True)
    return 'OK'


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'bot': BOT_NAME})


# ─── Event Handlers ────────────────────────────────────────────────────────────

@handler.add(JoinEvent)
def on_join(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', '')
    if group_id:
        upsert_group_settings(group_id)
        try:
            profile = line_bot_api.get_group_summary(group_id)
            upsert_group_settings(group_id, group_name=profile.group_name)
        except Exception:
            pass
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=(
            f'สวัสดีค่ะ! 🍡 หนูชื่อ{BOT_NAME}นะคะ\n\n'
            '📂 หน้าที่ของหนู:\n'
            '• บันทึกรูป/วิดีโอ/ไฟล์ แยกตามวันที่\n'
            '• เก็บประวัติแชทเป็นไฟล์ .txt\n'
            '• ส่งสรุปผ่านอีเมล\n'
            '• ตั้งเวลาส่งข้อความ\n\n'
            '⚙️ เริ่มต้นใช้งาน:\n'
            '1. พิมพ์ !ตั้งค่าอีเมล email@example.com\n'
            '2. พิมพ์ !ช่วยเหลือ เพื่อดูคำสั่งทั้งหมด\n\n'
            'ยินดีรับใช้ค่ะ 🍡'
        ))
    )


@handler.add(MessageEvent, message=TextMessage)
def on_text_message(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')
    settings = get_group_settings(group_id)

    # Count message for stats
    from database import increment_stat
    import pytz
    from datetime import datetime
    tz = pytz.timezone(os.environ.get('TIMEZONE', 'Asia/Bangkok'))
    today = datetime.now(tz).strftime('%Y-%m-%d')
    increment_stat(group_id, today, 'messages_count')

    handle_text_message(line_bot_api, event)


@handler.add(MessageEvent, message=ImageMessage)
def on_image(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return

    filepath, filename = save_image(line_bot_api, event)
    sender = _get_sender(event, group_id)
    append_chat_log(group_id, sender, 'image', filename)

    if settings.get('notifications_enabled', 1) and settings.get('email') and filepath:
        group_name = settings.get('group_name', group_id)
        send_media_notification(settings['email'], group_name, 'image', filename, filepath)

    # Async bill detection — fires and forgets, replies via push_message
    if filepath:
        process_bill_async(line_bot_api, group_id, filepath, filename, file_type='image')


@handler.add(MessageEvent, message=VideoMessage)
def on_video(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return

    filepath, filename = save_video(line_bot_api, event)
    sender = _get_sender(event, group_id)
    append_chat_log(group_id, sender, 'video', filename)

    if settings.get('notifications_enabled', 1) and settings.get('email') and filepath:
        group_name = settings.get('group_name', group_id)
        send_media_notification(settings['email'], group_name, 'video', filename, filepath)


@handler.add(MessageEvent, message=FileMessage)
def on_file(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return

    filepath, filename = save_file(line_bot_api, event)
    sender = _get_sender(event, group_id)
    append_chat_log(group_id, sender, 'file', filename)

    if settings.get('notifications_enabled', 1) and settings.get('email') and filepath:
        group_name = settings.get('group_name', group_id)
        send_media_notification(settings['email'], group_name, 'file', filename, filepath)

    # Async bill detection for PDF files
    if filepath and filename.lower().endswith('.pdf'):
        process_bill_async(line_bot_api, group_id, filepath, filename, file_type='pdf')


@handler.add(MessageEvent, message=AudioMessage)
def on_audio(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return

    filepath, filename = save_audio(line_bot_api, event)
    sender = _get_sender(event, group_id)
    append_chat_log(group_id, sender, 'audio', filename)


@handler.add(MessageEvent, message=StickerMessage)
def on_sticker(event):
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return
    sender = _get_sender(event, group_id)
    sticker_id = event.message.sticker_id
    append_chat_log(group_id, sender, 'sticker', f'sticker_id={sticker_id}')


# ─── Helper ────────────────────────────────────────────────────────────────────

def _get_sender(event, group_id: str) -> str:
    try:
        user_id = event.source.user_id
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except Exception:
        return 'Unknown'


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    logger.info(f'Starting {BOT_NAME} on port {port}')
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    finally:
        stop_scheduler()
