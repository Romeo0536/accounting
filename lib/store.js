/**
 * ชั้นเก็บข้อมูลข้อความติดต่อ (Contact message store)
 * -------------------------------------------------------------
 * รองรับ 2 โหมดอัตโนมัติ ไม่ต้องมี dependency ภายนอก:
 *
 *  1) โหมดคลาวด์ (แนะนำสำหรับใช้งานจริงบน Vercel)
 *     ตั้ง ENV: KV_REST_API_URL + KV_REST_API_TOKEN
 *     (สร้างฟรีได้จาก Vercel → Storage → KV / Upstash Redis)
 *     ข้อมูลถาวร เข้าถึงข้ามเครื่อง/ข้าม cold start ได้
 *
 *  2) โหมดไฟล์ (สำหรับรันในเครื่อง / self-host)
 *     เก็บเป็น JSON ไฟล์ที่ data/messages.json
 *     บน Vercel (อ่านอย่างเดียว) จะเขียนที่ /tmp แทน — เป็นข้อมูลชั่วคราว
 *     จึงควรตั้ง KV หรือใช้การแจ้งเตือน (email/webhook) ควบคู่กัน
 *
 * ทุกเมธอดเป็น async และคืนข้อมูลรูปแบบเดียวกันทั้งสองโหมด
 */

const fs = require('fs');
const path = require('path');

const KV_URL = process.env.KV_REST_API_URL || '';
const KV_TOKEN = process.env.KV_REST_API_TOKEN || '';
const useKV = Boolean(KV_URL && KV_TOKEN);

const INDEX_KEY = 'bunchee:contact:index'; // Redis list เก็บ id เรียงจากใหม่ไปเก่า
const msgKey = (id) => `bunchee:contact:msg:${id}`;

/* ---------------- Redis REST (Upstash / Vercel KV) ---------------- */

async function kv(command) {
  const res = await fetch(KV_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${KV_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(command),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`KV error ${res.status}: ${text}`);
  }
  const data = await res.json();
  return data.result;
}

const kvStore = {
  async add(msg) {
    await kv(['SET', msgKey(msg.id), JSON.stringify(msg)]);
    await kv(['LPUSH', INDEX_KEY, msg.id]);
    return msg;
  },
  async list() {
    const ids = (await kv(['LRANGE', INDEX_KEY, 0, -1])) || [];
    if (!ids.length) return [];
    const results = await kv(['MGET', ...ids.map(msgKey)]);
    return (results || [])
      .filter(Boolean)
      .map((s) => {
        try { return JSON.parse(s); } catch (_) { return null; }
      })
      .filter(Boolean);
  },
  async get(id) {
    const s = await kv(['GET', msgKey(id)]);
    if (!s) return null;
    try { return JSON.parse(s); } catch (_) { return null; }
  },
  async update(id, patch) {
    const cur = await this.get(id);
    if (!cur) return null;
    const next = { ...cur, ...patch };
    await kv(['SET', msgKey(id), JSON.stringify(next)]);
    return next;
  },
  async remove(id) {
    await kv(['DEL', msgKey(id)]);
    await kv(['LREM', INDEX_KEY, 0, id]);
    return true;
  },
};

/* ---------------- File store (local / self-host) ---------------- */

function fileLocation() {
  // บน Vercel ระบบไฟล์เป็น read-only ยกเว้น /tmp
  const onVercel = Boolean(process.env.VERCEL);
  const dir = onVercel ? '/tmp' : path.join(process.cwd(), 'data');
  try { fs.mkdirSync(dir, { recursive: true }); } catch (_) {}
  return path.join(dir, 'messages.json');
}

function readFile() {
  try {
    const raw = fs.readFileSync(fileLocation(), 'utf8');
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch (_) {
    return [];
  }
}

function writeFile(arr) {
  fs.writeFileSync(fileLocation(), JSON.stringify(arr, null, 2), 'utf8');
}

const fileStore = {
  async add(msg) {
    const arr = readFile();
    arr.unshift(msg); // ใหม่สุดอยู่บน
    writeFile(arr);
    return msg;
  },
  async list() {
    return readFile();
  },
  async get(id) {
    return readFile().find((m) => m.id === id) || null;
  },
  async update(id, patch) {
    const arr = readFile();
    const i = arr.findIndex((m) => m.id === id);
    if (i === -1) return null;
    arr[i] = { ...arr[i], ...patch };
    writeFile(arr);
    return arr[i];
  },
  async remove(id) {
    const arr = readFile();
    writeFile(arr.filter((m) => m.id !== id));
    return true;
  },
};

const store = useKV ? kvStore : fileStore;

module.exports = {
  store,
  storageMode: useKV ? 'kv' : 'file',
};
