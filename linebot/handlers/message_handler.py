import os
import logging
import re
from datetime import datetime
import pytz
from linebot.models import TextSendMessage

from database import (
    get_group_settings, upsert_group_settings,
    add_scheduled_message, get_upcoming_scheduled_messages, delete_scheduled_message,
    is_admin, add_admin, remove_admin, get_stats
)
from handlers.media_handler import append_chat_log, get_group_storage_summary
from handlers.email_sender import send_daily_summary

logger = logging.getLogger(__name__)
TZ = pytz.timezone(os.environ.get('TIMEZONE', 'Asia/Bangkok'))
BOT_NAME = os.environ.get('BOT_NAME', 'น้องโมจิ')
STORAGE_PATH = os.environ.get('STORAGE_PATH', './storage')

HELP_TEXT = f'''🍡 {BOT_NAME} — คำสั่งที่ใช้ได้

📧 ตั้งค่าอีเมล
!ตั้งค่าอีเมล email@example.com

🔔 แจ้งเตือนไฟล์ใหม่
!เปิดแจ้งเตือน / !ปิดแจ้งเตือน

📅 สรุปรายวันอัตโนมัติ (20:00 น.)
!เปิดสรุปรายวัน / !ปิดสรุปรายวัน

📊 สถิติกลุ่ม
!เปิดสถิติ / !ปิดสถิติ

📂 บันทึก
!เปิดบันทึก / !ปิดบันทึก

⏰ ตั้งเวลาส่งข้อความ
!ตั้งเวลา HH:MM ข้อความ
!ตั้งเวลา YYYY-MM-DD HH:MM ข้อความ

📋 รายการนัดหมาย
!นัดหมาย

❌ ยกเลิกนัดหมาย
!ยกเลิก [ID]

📊 สถิติกลุ่ม
!สถิติ

📤 ส่งสรุปอีเมล
!ส่งสรุป

⚙️ ดูการตั้งค่า
!สถานะ

👑 เพิ่ม/ลบแอดมิน (แอดมินเท่านั้น)
!เพิ่มแอดมิน [USER_ID]
!ลบแอดมิน [USER_ID]'''


def _reply(line_bot_api, reply_token: str, text: str):
    try:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=text))
    except Exception as e:
        logger.error(f'Reply failed: {e}')


def _get_group_id(event) -> str:
    return getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', 'direct')


def _get_sender_name(line_bot_api, event) -> str:
    try:
        group_id = _get_group_id(event)
        user_id = event.source.user_id
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except Exception:
        return 'Unknown'


def handle_text_message(line_bot_api, event):
    text = event.message.text.strip()
    group_id = _get_group_id(event)
    user_id = getattr(event.source, 'user_id', '')
    reply_token = event.reply_token

    settings = get_group_settings(group_id)

    # Log to chat history
    if settings.get('archiving_enabled', 1):
        sender = _get_sender_name(line_bot_api, event)
        append_chat_log(group_id, sender, 'text', text)

    # ─── Commands ───────────────────────────────────────────────────────────────
    if text.startswith('!'):
        _handle_command(line_bot_api, event, text, group_id, user_id, reply_token, settings)


def _handle_command(line_bot_api, event, text: str, group_id: str, user_id: str, reply_token: str, settings: dict):
    lower = text.lower()

    # Help
    if lower in ('!ช่วยเหลือ', '!help', '!คำสั่ง'):
        _reply(line_bot_api, reply_token, HELP_TEXT)
        return

    # Set email
    m = re.match(r'^!ตั้งค่าอีเมล\s+(\S+@\S+\.\S+)$', text)
    if m:
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้นที่ตั้งค่าได้')
            return
        email = m.group(1)
        upsert_group_settings(group_id, email=email)
        _reply(line_bot_api, reply_token, f'✅ ตั้งค่าอีเมลสำเร็จ!\n📧 {email}\nน้องโมจิจะส่งไฟล์และสรุปไปที่อีเมลนี้นะคะ 🍡')
        return

    # Toggle notifications
    if lower == '!เปิดแจ้งเตือน':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, notifications_enabled=1)
        _reply(line_bot_api, reply_token, '🔔 เปิดการแจ้งเตือนแล้วค่ะ!')
        return

    if lower == '!ปิดแจ้งเตือน':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, notifications_enabled=0)
        _reply(line_bot_api, reply_token, '🔕 ปิดการแจ้งเตือนแล้วค่ะ')
        return

    # Toggle archiving
    if lower == '!เปิดบันทึก':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, archiving_enabled=1)
        _reply(line_bot_api, reply_token, '📂 เปิดการบันทึกแล้วค่ะ! น้องโมจิจะเก็บไฟล์และประวัติแชทให้นะคะ 🍡')
        return

    if lower == '!ปิดบันทึก':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, archiving_enabled=0)
        _reply(line_bot_api, reply_token, '📵 ปิดการบันทึกแล้วค่ะ')
        return

    # Toggle daily summary
    if lower == '!เปิดสรุปรายวัน':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, daily_summary_enabled=1)
        _reply(line_bot_api, reply_token, '📅 เปิดสรุปรายวันอัตโนมัติแล้วค่ะ!\nน้องโมจิจะส่งสรุปทุก 20:00 น. นะคะ 🍡')
        return

    if lower == '!ปิดสรุปรายวัน':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, daily_summary_enabled=0)
        _reply(line_bot_api, reply_token, '📵 ปิดสรุปรายวันอัตโนมัติแล้วค่ะ\n(ยังส่งได้ด้วยตนเองผ่าน !ส่งสรุป)')
        return

    # Toggle stats
    if lower == '!เปิดสถิติ':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, stats_enabled=1)
        _reply(line_bot_api, reply_token, '📊 เปิดระบบสถิติแล้วค่ะ! ใช้คำสั่ง !สถิติ เพื่อดูยอด 7 วันย้อนหลัง 🍡')
        return

    if lower == '!ปิดสถิติ':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        upsert_group_settings(group_id, stats_enabled=0)
        _reply(line_bot_api, reply_token, '📵 ปิดระบบสถิติแล้วค่ะ')
        return

    # Schedule message
    if lower.startswith('!ตั้งเวลา '):
        _handle_schedule(line_bot_api, reply_token, text, group_id, user_id)
        return

    # List scheduled messages
    if lower in ('!นัดหมาย', '!รายการนัดหมาย'):
        msgs = get_upcoming_scheduled_messages(group_id)
        if not msgs:
            _reply(line_bot_api, reply_token, '📋 ไม่มีข้อความที่ตั้งเวลาไว้ค่ะ')
            return
        lines = [f'📋 รายการนัดหมาย ({len(msgs)} รายการ)\n']
        for m in msgs:
            dt = datetime.fromisoformat(m['scheduled_time'])
            dt_th = dt.astimezone(TZ).strftime('%d/%m/%Y %H:%M')
            lines.append(f'[{m["id"]}] {dt_th}\n💬 {m["message"][:50]}{"..." if len(m["message"])>50 else ""}')
        _reply(line_bot_api, reply_token, '\n'.join(lines))
        return

    # Cancel scheduled message
    m = re.match(r'^!ยกเลิก\s+(\d+)$', text)
    if m:
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        msg_id = int(m.group(1))
        if delete_scheduled_message(msg_id, group_id):
            _reply(line_bot_api, reply_token, f'✅ ยกเลิกนัดหมาย #{msg_id} สำเร็จค่ะ')
        else:
            _reply(line_bot_api, reply_token, f'❌ ไม่พบนัดหมาย #{msg_id} ในกลุ่มนี้ค่ะ')
        return

    # Stats
    if lower == '!สถิติ':
        if not settings.get('stats_enabled', 1):
            _reply(line_bot_api, reply_token, '📵 ระบบสถิติถูกปิดอยู่ค่ะ\nแอดมินสามารถเปิดได้ด้วย !เปิดสถิติ')
            return
        _handle_stats(line_bot_api, reply_token, group_id)
        return

    # Send summary
    if lower == '!ส่งสรุป':
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        _handle_send_summary(line_bot_api, reply_token, group_id, settings)
        return

    # Status
    if lower == '!สถานะ':
        _handle_status(line_bot_api, reply_token, group_id, settings)
        return

    # Add admin
    m = re.match(r'^!เพิ่มแอดมิน\s+(U[a-f0-9]+)$', text)
    if m:
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        new_admin_id = m.group(1)
        add_admin(new_admin_id, added_by=user_id)
        _reply(line_bot_api, reply_token, f'✅ เพิ่มแอดมินสำเร็จค่ะ\n🆔 {new_admin_id}')
        return

    # Remove admin
    m = re.match(r'^!ลบแอดมิน\s+(U[a-f0-9]+)$', text)
    if m:
        if not is_admin(user_id):
            _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
            return
        rem_id = m.group(1)
        remove_admin(rem_id)
        _reply(line_bot_api, reply_token, f'✅ ลบแอดมินสำเร็จค่ะ\n🆔 {rem_id}')
        return

    # Unknown command
    _reply(line_bot_api, reply_token, f'❓ ไม่รู้จักคำสั่งนี้ค่ะ\nพิมพ์ !ช่วยเหลือ เพื่อดูคำสั่งทั้งหมด 🍡')


def _handle_schedule(line_bot_api, reply_token: str, text: str, group_id: str, user_id: str):
    if not is_admin(user_id):
        _reply(line_bot_api, reply_token, '⚠️ เฉพาะแอดมินเท่านั้น')
        return

    # Format: !ตั้งเวลา HH:MM message  OR  !ตั้งเวลา YYYY-MM-DD HH:MM message
    m = re.match(r'^!ตั้งเวลา\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(.+)$', text, re.DOTALL)
    if m:
        date_str, time_str, message = m.group(1), m.group(2), m.group(3)
    else:
        m = re.match(r'^!ตั้งเวลา\s+(\d{2}:\d{2})\s+(.+)$', text, re.DOTALL)
        if m:
            time_str, message = m.group(1), m.group(2)
            date_str = datetime.now(TZ).strftime('%Y-%m-%d')
        else:
            _reply(line_bot_api, reply_token,
                   '❌ รูปแบบไม่ถูกต้องค่ะ\nตัวอย่าง:\n!ตั้งเวลา 14:30 ข้อความที่ต้องการส่ง\n!ตั้งเวลา 2025-01-01 00:00 สวัสดีปีใหม่!')
            return

    try:
        dt_local = TZ.localize(datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M'))
        dt_utc = dt_local.astimezone(pytz.utc)
        if dt_utc <= datetime.now(pytz.utc):
            _reply(line_bot_api, reply_token, '❌ ไม่สามารถตั้งเวลาในอดีตได้ค่ะ')
            return
        msg_id = add_scheduled_message(group_id, message, dt_utc.strftime('%Y-%m-%d %H:%M:%S'), user_id)
        dt_display = dt_local.strftime('%d/%m/%Y %H:%M')
        _reply(line_bot_api, reply_token,
               f'⏰ ตั้งเวลาสำเร็จค่ะ!\n📅 {dt_display} น.\n💬 {message[:80]}{"..." if len(message)>80 else ""}\n🆔 #{msg_id}')
    except ValueError:
        _reply(line_bot_api, reply_token, '❌ รูปแบบวันที่/เวลาไม่ถูกต้องค่ะ')


def _handle_stats(line_bot_api, reply_token: str, group_id: str):
    summary = get_group_storage_summary(group_id)
    stats_rows = get_stats(group_id, days=7)
    total_msgs = sum(s.get('messages_count', 0) for s in stats_rows)

    lines = [
        '📊 สถิติกลุ่ม (7 วันล่าสุด)\n',
        f'💬 ข้อความ: {total_msgs:,} ข้อความ',
        f'🖼️ รูปภาพ: {summary["total_images"]:,} ไฟล์',
        f'🎬 วิดีโอ: {summary["total_videos"]:,} ไฟล์',
        f'📄 ไฟล์: {summary["total_files"]:,} ไฟล์',
        '',
        '📅 ตามวันที่:',
    ]
    for d in summary['dates'][:5]:
        lines.append(f'{d["date"]}: 🖼️{d["images"]} 🎬{d["videos"]} 📄{d["files"]}')

    _reply(line_bot_api, reply_token, '\n'.join(lines))


def _handle_send_summary(line_bot_api, reply_token: str, group_id: str, settings: dict):
    email = settings.get('email', '')
    if not email:
        _reply(line_bot_api, reply_token, '❌ ยังไม่ได้ตั้งค่าอีเมลค่ะ\nใช้คำสั่ง: !ตั้งค่าอีเมล email@example.com')
        return

    stats_rows = get_stats(group_id, days=1)
    stats = stats_rows[0] if stats_rows else {}
    group_name = settings.get('group_name', group_id)

    chat_log = os.path.join(STORAGE_PATH, group_id, 'chat_history.txt')
    ok = send_daily_summary(email, group_name, stats, chat_log if os.path.isfile(chat_log) else None)
    if ok:
        _reply(line_bot_api, reply_token, f'📤 ส่งสรุปไปที่ {email} แล้วค่ะ 🍡')
    else:
        _reply(line_bot_api, reply_token, '❌ ส่งอีเมลไม่สำเร็จ ตรวจสอบการตั้งค่า SMTP ด้วยนะคะ')


def _handle_status(line_bot_api, reply_token: str, group_id: str, settings: dict):
    email = settings.get('email', '') or '(ยังไม่ได้ตั้งค่า)'
    notify    = '🔔 เปิด' if settings.get('notifications_enabled', 1) else '🔕 ปิด'
    archive   = '📂 เปิด' if settings.get('archiving_enabled', 1)     else '📵 ปิด'
    daily_sum = '📅 เปิด' if settings.get('daily_summary_enabled', 1) else '📵 ปิด'
    stats_st  = '📊 เปิด' if settings.get('stats_enabled', 1)         else '📵 ปิด'
    upcoming  = get_upcoming_scheduled_messages(group_id)

    lines = [
        f'🍡 สถานะ {BOT_NAME}\n',
        f'📧 อีเมล: {email}',
        f'แจ้งเตือนไฟล์ใหม่: {notify}',
        f'สรุปรายวันอัตโนมัติ: {daily_sum}',
        f'สถิติกลุ่ม: {stats_st}',
        f'การบันทึกข้อมูล: {archive}',
        f'⏰ นัดหมายที่รอ: {len(upcoming)} รายการ',
        f'🆔 Group ID: {group_id}',
    ]
    _reply(line_bot_api, reply_token, '\n'.join(lines))
