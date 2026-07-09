/**
 * /api/messages  (สำหรับแอดมิน — ต้องใส่กุญแจ)
 * -------------------------------------------------------------
 * ยืนยันตัวตนด้วย ENV `ADMIN_KEY` ส่งมาทาง header `x-admin-key`
 * หรือ query `?key=` (ค่าเริ่มต้นถ้าไม่ตั้ง ENV คือ "buncheepro-admin")
 *
 *   GET    /api/messages            → รายการข้อความทั้งหมด (+ สรุปจำนวน)
 *   PATCH  /api/messages?id=xxx     → อัปเดตสถานะ { status: 'new'|'read'|'done' }
 *   DELETE /api/messages?id=xxx     → ลบข้อความ
 */

const { store, storageMode } = require('../lib/store');

const ADMIN_KEY = process.env.ADMIN_KEY || 'buncheepro-admin';

function authorized(req) {
  const url = new URL(req.url, 'http://localhost');
  const key = req.headers['x-admin-key'] || url.searchParams.get('key') || '';
  return key === ADMIN_KEY;
}

async function readJson(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw) return {};
  try { return JSON.parse(raw); } catch (_) { return {}; }
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-admin-key');

  if (req.method === 'OPTIONS') { res.status(204).end(); return; }

  if (!authorized(req)) {
    res.status(401).json({ ok: false, error: 'ไม่ได้รับอนุญาต (กุญแจแอดมินไม่ถูกต้อง)' });
    return;
  }

  const url = new URL(req.url, 'http://localhost');
  const id = url.searchParams.get('id');

  try {
    if (req.method === 'GET') {
      const items = await store.list();
      const summary = items.reduce(
        (acc, m) => { acc[m.status] = (acc[m.status] || 0) + 1; return acc; },
        { new: 0, read: 0, done: 0 }
      );
      res.status(200).json({ ok: true, storage: storageMode, count: items.length, summary, items });
      return;
    }

    if (req.method === 'PATCH') {
      if (!id) { res.status(400).json({ ok: false, error: 'ต้องระบุ id' }); return; }
      const body = await readJson(req);
      const allowed = ['new', 'read', 'done'];
      if (!allowed.includes(body.status)) {
        res.status(400).json({ ok: false, error: 'สถานะไม่ถูกต้อง' });
        return;
      }
      const updated = await store.update(id, { status: body.status });
      if (!updated) { res.status(404).json({ ok: false, error: 'ไม่พบข้อความ' }); return; }
      res.status(200).json({ ok: true, item: updated });
      return;
    }

    if (req.method === 'DELETE') {
      if (!id) { res.status(400).json({ ok: false, error: 'ต้องระบุ id' }); return; }
      await store.remove(id);
      res.status(200).json({ ok: true });
      return;
    }

    res.status(405).json({ ok: false, error: 'เมธอดไม่รองรับ' });
  } catch (err) {
    res.status(500).json({ ok: false, error: 'เกิดข้อผิดพลาด', detail: String(err && err.message || err) });
  }
};
