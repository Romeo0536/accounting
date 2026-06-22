"""
APScheduler - กำหนดเวลารันงาน Automation อัตโนมัติ
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import automation
import line_bot

scheduler = AsyncIOScheduler(timezone="Asia/Bangkok")


def setup_scheduler():
    # ────────────────────────────────────────────────────────────
    # รันทุกวัน 08:00 — ตรวจสอบ Overdue
    # ────────────────────────────────────────────────────────────
    scheduler.add_job(
        automation.auto_mark_overdue,
        CronTrigger(hour=8, minute=0),
        id="daily_overdue_check",
        name="ตรวจสอบ Overdue ทุกวัน",
        replace_existing=True,
    )

    # ────────────────────────────────────────────────────────────
    # รันวันที่ 1 ของทุกเดือน 06:00 — ตั้งต้นเดือน
    # (สร้างงาน + ภาษี + ใบแจ้งหนี้)
    # ────────────────────────────────────────────────────────────
    scheduler.add_job(
        automation.auto_monthly_setup,
        CronTrigger(day=1, hour=6, minute=0),
        id="monthly_setup",
        name="ตั้งต้นเดือนใหม่ (วันที่ 1)",
        replace_existing=True,
    )

    # ────────────────────────────────────────────────────────────
    # รันทุกวัน 08:30 — ส่งสรุปประจำวันเข้า LINE
    # (ส่งจริงเฉพาะเมื่อตั้งค่า token + ผู้รับแล้ว มิฉะนั้นข้ามเงียบๆ)
    # ────────────────────────────────────────────────────────────
    scheduler.add_job(
        line_bot.push_daily_digest,
        CronTrigger(hour=8, minute=30),
        id="line_daily_digest",
        name="แจ้งเตือนสรุปประจำวันผ่าน LINE",
        replace_existing=True,
    )

    scheduler.start()
    return scheduler
