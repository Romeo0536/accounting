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
    from database import (
        get_pending_scheduled_messages, mark_message_sent,
        get_stats, get_bill_summary, get_db,
    )
    from handlers.email_sender import send_daily_summary

    STORAGE_PATH = os.environ.get('STORAGE_PATH', './storage')

    # Guard: never start twice (e.g. if the module is re-imported)
    if _scheduler.running:
        logger.info('Scheduler already running, skipping start')
        return

    def send_pending_messages():
        try:
            msgs = get_pending_scheduled_messages()
        except Exception as e:
            logger.error(f'Failed to load pending messages: {e}')
            return
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
        try:
            conn = get_db()
            rows = conn.execute(
                "SELECT * FROM group_settings WHERE email != '' AND daily_summary_enabled = 1"
            ).fetchall()
            conn.close()
        except Exception as e:
            logger.error(f'Failed to load groups for daily summary: {e}')
            return

        for row in rows:
            group_id = row['group_id']
            email = row['email']
            group_name = row['group_name'] or group_id
            # Per-group try/except: one bad email must not abort the whole run
            try:
                stats_rows = get_stats(group_id, days=1)
                stats = stats_rows[0] if stats_rows else {}
                bill_summary = get_bill_summary(group_id, days=1)
                chat_log = os.path.join(STORAGE_PATH, group_id, 'chat_history.txt')
                send_daily_summary(
                    email, group_name, stats,
                    chat_log if os.path.isfile(chat_log) else None,
                    bill_summary=bill_summary,
                )
                logger.info(f'Daily summary sent to {email} for group {group_id}')
            except Exception as e:
                logger.error(f'Daily summary failed for group {group_id}: {e}')

    # Check scheduled messages every minute.
    # max_instances=1 + coalesce: if a run overruns (many groups), don't pile up.
    _scheduler.add_job(
        send_pending_messages,
        'interval',
        minutes=1,
        id='check_scheduled_messages',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )

    # Daily summary at 20:00 Bangkok time
    _scheduler.add_job(
        send_daily_summaries,
        CronTrigger(hour=20, minute=0, timezone=TZ),
        id='daily_summary',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info('Scheduler started')


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info('Scheduler stopped')
