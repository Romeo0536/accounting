/**
 * POST /api/contact
 * -------------------------------------------------------------
 * รับข้อความจากฟอร์มติดต่อ → ตรวจสอบ → บันทึกลงคลัง → แจ้งเตือนทีมงาน
 *
 * รับข้อมูล (JSON หรือ form): name*, phone*, message*, email, topic
 * คืนค่า: { ok: true, id } เมื่อสำเร็จ
 *
 * การแจ้งเตือน (ตั้งค่าได้ทั้งคู่ ไม่ตั้งก็ได้ ข้อความยังถูกบันทึกไว้):
 *   - RESEND_API_KEY + CONTACT_TO_EMAIL (+ CONTACT_FROM_EMAIL) → ส่งอีเมล
 *   - NOTIFY_WEBHOOK_URL → POST JSON (ใช้ได้กับ Slack / Discord / Google Chat / Apps Script)
 */

const { store, storageMode } = require('../lib/store');

function makeId() {
  const t = Date.now().toString(36);
  const r = Math.random().toString(36).slice(2, 8);
  return `${t}${r}`;
}

function clean(v, max) {
  return String(v == null ? '' : v).trim().slice(0, max);
}

function validate(body) {
  const errors = {};
  const name = clean(body.name, 120);
  const phone = clean(body.phone, 40);
  const email = clean(body.email, 160);
  const topic = clean(body.topic, 120) || 'ทั่วไป';
  const message = clean(body.message, 4000);

  if (!name) errors.name = 'กรุณากรอกชื่อ';
  const phoneDigits = phone.replace(/\D/g, '');
  if (phoneDigits.length < 9 || phoneDigits.length > 10) errors.phone = 'เบอร์โทรไม่ถูกต้อง';
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'อีเมลไม่ถูกต้อง';
  if (!message) errors.message = 'กรุณากรอกข้อความ';

  return { errors, value: { name, phone, email, topic, message } };
}

async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw) return {};
  const ctype = (req.headers['content-type'] || '').toLowerCase();
  if (ctype.includes('application/json')) {
    try { return JSON.parse(raw); } catch (_) { return {}; }
  }
  // form-urlencoded
  const obj = {};
  new URLSearchParams(raw).forEach((val, key) => { obj[key] = val; });
  return obj;
}

async function notifyEmail(msg) {
  const key = process.env.RESEND_API_KEY;
  const to = process.env.CONTACT_TO_EMAIL || 'hello@buncheepro.co.th';
  const from = process.env.CONTACT_FROM_EMAIL || 'BuncheePro <onboarding@resend.dev>';
  if (!key) return { skipped: 'no RESEND_API_KEY' };

  const html = `
    <h2>มีข้อความติดต่อใหม่จากเว็บไซต์</h2>
    <table style="border-collapse:collapse;font-family:sans-serif">
      <tr><td style="padding:4px 12px;color:#64748b">ชื่อ</td><td style="padding:4px 12px"><b>${escapeHtml(msg.name)}</b></td></tr>
      <tr><td style="padding:4px 12px;color:#64748b">เบอร์โทร</td><td style="padding:4px 12px">${escapeHtml(msg.phone)}</td></tr>
      <tr><td style="padding:4px 12px;color:#64748b">อีเมล</td><td style="padding:4px 12px">${escapeHtml(msg.email || '-')}</td></tr>
      <tr><td style="padding:4px 12px;color:#64748b">เรื่อง</td><td style="padding:4px 12px">${escapeHtml(msg.topic)}</td></tr>
    </table>
    <p style="font-family:sans-serif;white-space:pre-wrap;border-left:3px solid #16a34a;padding-left:12px;margin-top:12px">${escapeHtml(msg.message)}</p>
  `;
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from,
      to: [to],
      reply_to: msg.email || undefined,
      subject: `[ติดต่อใหม่] ${msg.topic} — ${msg.name}`,
      html,
    }),
  });
  return { ok: res.ok, status: res.status };
}

async function notifyWebhook(msg) {
  const url = process.env.NOTIFY_WEBHOOK_URL;
  if (!url) return { skipped: 'no NOTIFY_WEBHOOK_URL' };
  const text =
    `📬 ข้อความติดต่อใหม่จากเว็บไซต์\n` +
    `ชื่อ: ${msg.name}\nเบอร์: ${msg.phone}\nอีเมล: ${msg.email || '-'}\n` +
    `เรื่อง: ${msg.topic}\n— — —\n${msg.message}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // ครอบคลุมทั้ง Slack/Discord/Google Chat ("text") และ payload ดิบ (message)
    body: JSON.stringify({ text, content: text, message: msg }),
  });
  return { ok: res.ok, status: res.status };
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') {
    res.status(405).json({ ok: false, error: 'ใช้ได้เฉพาะ POST' });
    return;
  }

  try {
    const body = await readBody(req);
    const { errors, value } = validate(body);
    if (Object.keys(errors).length) {
      res.status(400).json({ ok: false, error: 'ข้อมูลไม่ครบถ้วน', errors });
      return;
    }

    const msg = {
      id: makeId(),
      ...value,
      status: 'new', // new | read | done
      createdAt: new Date().toISOString(),
      ip: (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || null,
      userAgent: req.headers['user-agent'] || null,
    };

    await store.add(msg);

    // แจ้งเตือนแบบไม่ปิดกั้นผลลัพธ์ — ถ้าแจ้งเตือนล้มเหลว ข้อความก็ยังถูกบันทึกแล้ว
    const notified = await Promise.allSettled([notifyEmail(msg), notifyWebhook(msg)]);
    const notifyResult = notified.map((n) => (n.status === 'fulfilled' ? n.value : { error: String(n.reason) }));

    res.status(200).json({ ok: true, id: msg.id, storage: storageMode, notify: notifyResult });
  } catch (err) {
    res.status(500).json({ ok: false, error: 'เกิดข้อผิดพลาดฝั่งเซิร์ฟเวอร์', detail: String(err && err.message || err) });
  }
};
