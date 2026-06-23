import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone(os.environ.get('TIMEZONE', 'Asia/Bangkok'))
_scheduler = BackgroundScheduler(timezone=TZ)


def start_scheduler(line_bot_api):
    from linebot.models import TextSendMessage
    from database import get_pending_scheduled_messages, mark_message_sent, get_stats, get_group_settings
    from handlers.email_sender import send_daily_summary
    import os

    STORAGE_PATH = os.environ.get('STORAGE_PATH', './storage')

    def send_pending_messages():
        msgs = get_pending_scheduled_messages()
        for msg in msgs:
            try:
                line_bot_api.push_message(
                    msg['group_id'],
                    TextSendMessage(text=msg['message'])
                )
                mark_message_sent(msg['id'])
                logger.info(f'Sent scheduled message #{msg["id"]} to {msg["group_id"]}')
            except Exception as e:
                logger.error(f'Failed to send scheduled message #{msg["id"]}: {e}')

    def send_daily_summaries():
        import sqlite3
        from database import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT * FROM group_settings WHERE email != "" AND daily_summary_enabled = 1'
        ).fetchall()
        conn.close()

        for row in rows:
            group_id = row['group_id']
            email = row['email']
            group_name = row['group_name'] or group_id
            stats_rows = get_stats(group_id, days=1)
            stats = stats_rows[0] if stats_rows else {}
            chat_log = os.path.join(STORAGE_PATH, group_id, 'chat_history.txt')
            send_daily_summary(
                email, group_name, stats,
                chat_log if os.path.isfile(chat_log) else None
            )
            logger.info(f'Daily summary sent to {email} for group {group_id}')

    # Check scheduled messages every minute
    _scheduler.add_job(
        send_pending_messages,
        'interval',
        minutes=1,
        id='check_scheduled_messages',
        replace_existing=True
    )

    # Daily summary at 20:00 Bangkok time
    _scheduler.add_job(
        send_daily_summaries,
        CronTrigger(hour=20, minute=0, timezone=TZ),
        id='daily_summary',
        replace_existing=True
    )

    _scheduler.start()
    logger.info('Scheduler started')


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info('Scheduler stopped')
