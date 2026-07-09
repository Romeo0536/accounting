/**
 * ทดสอบระบบติดต่อแบบ end-to-end โดยจำลอง req/res ของ Vercel
 * รันด้วย:  node test/contact.test.js
 * ใช้ที่เก็บแบบไฟล์ (ไม่ตั้ง KV) — สะอาดและไม่ต้องต่อเน็ต
 */
const { Readable } = require('stream');
const fs = require('fs');
const path = require('path');

// ให้แน่ใจว่าใช้ file store และไม่ยิงแจ้งเตือนออกเน็ต
delete process.env.KV_REST_API_URL;
delete process.env.KV_REST_API_TOKEN;
delete process.env.RESEND_API_KEY;
delete process.env.NOTIFY_WEBHOOK_URL;
delete process.env.VERCEL;
process.env.ADMIN_KEY = 'test-key-123';

const DATA_FILE = path.join(process.cwd(), 'data', 'messages.json');
try { fs.unlinkSync(DATA_FILE); } catch (_) {}

const contact = require('../api/contact.js');
const messages = require('../api/messages.js');

function mockReq({ method = 'GET', url = '/', headers = {}, body = null }) {
  const raw = body == null ? '' : (typeof body === 'string' ? body : JSON.stringify(body));
  const req = Readable.from([Buffer.from(raw, 'utf8')]);
  req.method = method;
  req.url = url;
  req.headers = Object.assign({ 'content-type': 'application/json' }, headers);
  return req;
}

function mockRes() {
  const res = {
    statusCode: 200,
    headers: {},
    payload: undefined,
    setHeader(k, v) { this.headers[k] = v; },
    status(c) { this.statusCode = c; return this; },
    json(o) { this.payload = o; this._done(); return this; },
    end() { this._done(); return this; },
  };
  res.done = new Promise((resolve) => { res._done = resolve; });
  return res;
}

async function call(handler, reqOpts) {
  const req = mockReq(reqOpts);
  const res = mockRes();
  await handler(req, res);
  await res.done;
  return res;
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓', name); }
  else { fail++; console.log('  ✗', name, extra != null ? '→ ' + JSON.stringify(extra) : ''); }
}

(async () => {
  console.log('\n== POST /api/contact ==');

  // 1) invalid: missing fields
  let r = await call(contact, { method: 'POST', body: { name: '', phone: '123', message: '' } });
  check('ข้อมูลไม่ครบ → 400', r.statusCode === 400, r.payload);
  check('คืน errors ราย field', r.payload && r.payload.errors && r.payload.errors.name && r.payload.errors.phone && r.payload.errors.message);

  // 2) invalid email
  r = await call(contact, { method: 'POST', body: { name: 'ก', phone: '0812345678', message: 'x', email: 'bad' } });
  check('อีเมลผิดรูปแบบ → 400', r.statusCode === 400, r.payload);

  // 3) valid submit
  r = await call(contact, { method: 'POST', body: {
    name: 'สมชาย ใจดี', phone: '084-552-1990', email: 'somchai@example.com',
    topic: 'สอบถามแพ็กเกจและราคา', message: 'สนใจแพ็กเกจร้านค้าเล็ก'
  }});
  check('ส่งถูกต้อง → 200 ok', r.statusCode === 200 && r.payload && r.payload.ok === true, r.payload);
  check('คืน id', r.payload && typeof r.payload.id === 'string' && r.payload.id.length > 0);
  const firstId = r.payload && r.payload.id;

  // 4) another valid submit (form-urlencoded)
  r = await call(contact, { method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: 'name=มานี&phone=0812345678&message=ทดลองใช้ฟรี&topic=ทดลองใช้ฟรี 30 วัน' });
  check('รับ form-urlencoded ได้ → 200', r.statusCode === 200 && r.payload.ok === true, r.payload);

  // 5) wrong method
  r = await call(contact, { method: 'GET' });
  check('GET /api/contact → 405', r.statusCode === 405);

  console.log('\n== /api/messages (admin) ==');

  // 6) no key → 401
  r = await call(messages, { method: 'GET', url: '/api/messages' });
  check('ไม่มีกุญแจ → 401', r.statusCode === 401, r.payload);

  // 7) with key → list
  r = await call(messages, { method: 'GET', url: '/api/messages?key=test-key-123' });
  check('มีกุญแจ → 200', r.statusCode === 200 && r.payload.ok === true, r.payload);
  check('เห็น 2 ข้อความ', r.payload.count === 2, r.payload.count);
  check('สรุปมี new=2', r.payload.summary && r.payload.summary.new === 2, r.payload.summary);

  // 8) key via header
  r = await call(messages, { method: 'GET', url: '/api/messages', headers: { 'x-admin-key': 'test-key-123' } });
  check('กุญแจผ่าน header ได้', r.statusCode === 200 && r.payload.ok === true);

  // 9) PATCH status → done
  r = await call(messages, { method: 'PATCH', url: '/api/messages?key=test-key-123&id=' + firstId, body: { status: 'done' } });
  check('อัปเดตสถานะ → done', r.statusCode === 200 && r.payload.item.status === 'done', r.payload);

  // 10) PATCH invalid status
  r = await call(messages, { method: 'PATCH', url: '/api/messages?key=test-key-123&id=' + firstId, body: { status: 'weird' } });
  check('สถานะไม่ถูกต้อง → 400', r.statusCode === 400);

  // 11) verify summary now new=1 done=1
  r = await call(messages, { method: 'GET', url: '/api/messages?key=test-key-123' });
  check('สรุปเปลี่ยนเป็น new=1 done=1', r.payload.summary.new === 1 && r.payload.summary.done === 1, r.payload.summary);

  // 12) DELETE
  r = await call(messages, { method: 'DELETE', url: '/api/messages?key=test-key-123&id=' + firstId });
  check('ลบข้อความ → ok', r.statusCode === 200 && r.payload.ok === true);
  r = await call(messages, { method: 'GET', url: '/api/messages?key=test-key-123' });
  check('เหลือ 1 ข้อความหลังลบ', r.payload.count === 1, r.payload.count);

  // cleanup
  try { fs.unlinkSync(DATA_FILE); } catch (_) {}

  console.log('\n----------------------------------------');
  console.log(`ผลทดสอบ: ผ่าน ${pass} / ล้มเหลว ${fail}`);
  console.log('----------------------------------------\n');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error('TEST CRASH:', e); process.exit(1); });
