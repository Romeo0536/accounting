import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone(os.environ.get('TIMEZONE', 'Asia/Bangkok'))


def _smtp_config():
    return {
        'host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
        'port': int(os.environ.get('SMTP_PORT', 587)),
        'user': os.environ.get('SMTP_USER', ''),
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'from_name': os.environ.get('SMTP_FROM_NAME', 'น้องโมจิ Bot'),
    }


def send_email(to: str, subject: str, body: str, attachments: list = None) -> bool:
    cfg = _smtp_config()
    if not cfg['user'] or not cfg['password']:
        logger.warning('SMTP credentials not configured')
        return False
    if not to:
        logger.warning('No recipient email configured for this group')
        return False

    msg = MIMEMultipart()
    msg['From'] = f"{cfg['from_name']} <{cfg['user']}>"
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    for path in (attachments or []):
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(path)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

    try:
        with smtplib.SMTP(cfg['host'], cfg['port']) as server:
            server.starttls()
            server.login(cfg['user'], cfg['password'])
            server.sendmail(cfg['user'], to, msg.as_string())
        logger.info(f'Email sent to {to}: {subject}')
        return True
    except Exception as e:
        logger.error(f'Email send failed: {e}')
        return False


def send_media_notification(to: str, group_name: str, media_type: str, filename: str, file_path: str = None):
    now = datetime.now(TZ)
    date_str = now.strftime('%d/%m/%Y %H:%M น.')
    icon = {'image': '🖼️', 'video': '🎬', 'file': '📄', 'audio': '🎵'}.get(media_type, '📎')
    type_th = {'image': 'รูปภาพ', 'video': 'วิดีโอ', 'file': 'ไฟล์', 'audio': 'เสียง'}.get(media_type, 'สื่อ')

    subject = f'{icon} [{group_name}] มี{type_th}ใหม่ - {date_str}'
    body = f'''
    <div style="font-family: 'Sarabun', sans-serif; max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 12px;">
      <div style="background: linear-gradient(135deg, #FF6B9D, #C44DFF); padding: 20px; border-radius: 10px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🍡 น้องโมจิ</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0;">ระบบบันทึกข้อมูลกลุ่ม LINE</p>
      </div>
      <div style="background: white; margin-top: 15px; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <p style="font-size: 16px; color: #333;">
          {icon} มี<strong>{type_th}</strong>ใหม่ในกลุ่ม <strong>{group_name}</strong>
        </p>
        <table style="width:100%; border-collapse:collapse;">
          <tr><td style="padding:6px 0; color:#666; width:120px;">ชื่อไฟล์:</td><td style="color:#333;"><strong>{filename}</strong></td></tr>
          <tr><td style="padding:6px 0; color:#666;">วันที่/เวลา:</td><td style="color:#333;">{date_str}</td></tr>
          <tr><td style="padding:6px 0; color:#666;">กลุ่ม:</td><td style="color:#333;">{group_name}</td></tr>
        </table>
      </div>
      <p style="text-align:center; color:#aaa; font-size:12px; margin-top:15px;">ส่งโดย น้องโมจิ 🍡 • ระบบบันทึกข้อมูลอัตโนมัติ</p>
    </div>
    '''
    attachments = [file_path] if file_path and os.path.isfile(file_path) else []
    return send_email(to, subject, body, attachments)


def send_daily_summary(to: str, group_name: str, stats: dict, chat_log_path: str = None,
                       bill_summary: dict = None):
    now = datetime.now(TZ)
    date_str = now.strftime('%d/%m/%Y')
    subject = f'📊 [{group_name}] สรุปประจำวัน {date_str}'

    bill_section = ''
    if bill_summary and (bill_summary.get('count') or 0) > 0:
        b_count = bill_summary.get('count', 0)
        b_total = bill_summary.get('total_amount') or 0
        bill_section = f'''
        <div style="background:#FFFBF0; border-radius:8px; padding:15px; margin-top:10px; border-left:4px solid #FFB800;">
          <h3 style="color:#B8860B; margin:0 0 8px;">🧾 บิล/ใบเสร็จวันนี้</h3>
          <p style="margin:4px 0; color:#555;">จำนวน: <strong>{b_count} ใบ</strong></p>
          <p style="margin:4px 0; color:#555;">ยอดรวม: <strong>{b_total:,.2f} ฿</strong></p>
        </div>'''

    body = f'''
    <div style="font-family: 'Sarabun', sans-serif; max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 12px;">
      <div style="background: linear-gradient(135deg, #FF6B9D, #C44DFF); padding: 20px; border-radius: 10px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🍡 น้องโมจิ</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0;">สรุปประจำวัน</p>
      </div>
      <div style="background: white; margin-top: 15px; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h2 style="color: #C44DFF; margin-top:0;">📊 สรุปกลุ่ม {group_name}</h2>
        <p style="color:#666;">วันที่ {date_str}</p>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:15px;">
          <div style="background:#FFF0F5; border-radius:8px; padding:15px; text-align:center;">
            <div style="font-size:28px;">💬</div>
            <div style="font-size:24px; font-weight:bold; color:#FF6B9D;">{stats.get('messages_count',0)}</div>
            <div style="color:#666; font-size:13px;">ข้อความ</div>
          </div>
          <div style="background:#F5F0FF; border-radius:8px; padding:15px; text-align:center;">
            <div style="font-size:28px;">🖼️</div>
            <div style="font-size:24px; font-weight:bold; color:#C44DFF;">{stats.get('images_count',0)}</div>
            <div style="color:#666; font-size:13px;">รูปภาพ</div>
          </div>
          <div style="background:#F0F5FF; border-radius:8px; padding:15px; text-align:center;">
            <div style="font-size:28px;">🎬</div>
            <div style="font-size:24px; font-weight:bold; color:#5B7AFF;">{stats.get('videos_count',0)}</div>
            <div style="color:#666; font-size:13px;">วิดีโอ</div>
          </div>
          <div style="background:#F0FFF5; border-radius:8px; padding:15px; text-align:center;">
            <div style="font-size:28px;">📄</div>
            <div style="font-size:24px; font-weight:bold; color:#00C070;">{stats.get('files_count',0)}</div>
            <div style="color:#666; font-size:13px;">ไฟล์</div>
          </div>
        </div>
        {bill_section}
      </div>
      <p style="text-align:center; color:#aaa; font-size:12px; margin-top:15px;">ส่งโดย น้องโมจิ 🍡 • ระบบบันทึกข้อมูลอัตโนมัติ</p>
    </div>
    '''
    attachments = [chat_log_path] if chat_log_path and os.path.isfile(chat_log_path) else []
    return send_email(to, subject, body, attachments)
