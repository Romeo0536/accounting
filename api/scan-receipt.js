/**
 * POST /api/scan-receipt
 * -------------------------------------------------------------
 * "สแกนใบเสร็จด้วย AI" — รับรูปใบเสร็จ (base64) แล้วให้ Claude อ่านค่า
 * ผู้ขาย / เลขผู้เสียภาษี / วันที่ / ยอดก่อน VAT / VAT / ยอดรวม / หมวดหมู่
 *
 * ต้องตั้ง ENV: ANTHROPIC_API_KEY (ที่ Vercel → Settings → Environment Variables)
 * หากยังไม่ตั้งค่า จะตอบ 503 และหน้าเว็บจะเปิดฟอร์มกรอกมือแทนอัตโนมัติ
 */

const _sdk = require('@anthropic-ai/sdk');
const Anthropic = _sdk.Anthropic || _sdk.default || _sdk;

const CATEGORIES = ['ค่าสินค้า/วัตถุดิบ','ค่าเช่า','ค่าน้ำ-ไฟ-อินเทอร์เน็ต','ค่าเดินทาง/ขนส่ง','การตลาด/โฆษณา','ค่าบริการวิชาชีพ','อุปกรณ์สำนักงาน','เงินเดือน/ค่าจ้าง','อื่น ๆ'];

const SCHEMA = {
  type: 'object',
  properties: {
    vendor: { type: 'string', description: 'ชื่อร้านค้า/ผู้ขายตามที่ปรากฏบนใบเสร็จ' },
    tax_id: { type: 'string', description: 'เลขประจำตัวผู้เสียภาษี 13 หลักของผู้ขาย (ว่างถ้าไม่มี)' },
    date: { type: 'string', description: 'วันที่บนใบเสร็จ รูปแบบ YYYY-MM-DD (ค.ศ.) — ถ้าใบเสร็จเป็น พ.ศ. ให้ลบ 543' },
    subtotal: { type: 'number', description: 'มูลค่าก่อน VAT (ถ้าใบเสร็จไม่มี VAT ให้เท่ากับยอดรวม)' },
    vat: { type: 'number', description: 'จำนวนเงิน VAT (0 ถ้าไม่มี)' },
    total: { type: 'number', description: 'ยอดรวมสุทธิที่จ่ายจริง' },
    category: { type: 'string', enum: CATEGORIES, description: 'หมวดหมู่ค่าใช้จ่ายที่เหมาะสมที่สุด' },
  },
  required: ['vendor', 'tax_id', 'date', 'subtotal', 'vat', 'total', 'category'],
  additionalProperties: false,
};

const PROMPT =
  'อ่านใบเสร็จ/ใบกำกับภาษีในรูปนี้ แล้วสกัดข้อมูลตาม schema ที่กำหนด ' +
  'ระวังเรื่องปี พ.ศ. (ให้แปลงเป็น ค.ศ.) และตัวเลขที่มีจุลภาคคั่นหลักพัน ' +
  'ถ้าใบเสร็จแสดงเฉพาะยอดรวม ให้ vat=0 และ subtotal=total';

async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString('utf8');
  try { return JSON.parse(raw); } catch (_) { return {}; }
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ ok: false, error: 'ใช้ได้เฉพาะ POST' }); return; }

  if (!process.env.ANTHROPIC_API_KEY) {
    res.status(503).json({ ok: false, error: 'ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY บนเซิร์ฟเวอร์ (ดู SETUP.md)' });
    return;
  }

  try {
    const body = await readBody(req);
    let data = String(body.image_base64 || '');
    // เผื่อกรณีส่งมาเป็น data URL เต็ม
    if (data.startsWith('data:')) data = data.split(',')[1] || '';
    if (!data) { res.status(400).json({ ok: false, error: 'ไม่พบข้อมูลรูปภาพ (image_base64)' }); return; }
    const mediaType = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(body.media_type)
      ? body.media_type : 'image/jpeg';

    const client = new Anthropic();
    const response = await client.messages.create({
      model: 'claude-opus-4-8',
      max_tokens: 2048,
      thinking: { type: 'adaptive' },
      output_config: { format: { type: 'json_schema', schema: SCHEMA } },
      messages: [{
        role: 'user',
        content: [
          { type: 'image', source: { type: 'base64', media_type: mediaType, data } },
          { type: 'text', text: PROMPT },
        ],
      }],
    });

    if (response.stop_reason === 'refusal') {
      res.status(422).json({ ok: false, error: 'AI ไม่สามารถประมวลผลรูปนี้ได้ กรุณากรอกข้อมูลเอง' });
      return;
    }

    const textBlock = response.content.find((b) => b.type === 'text');
    if (!textBlock) throw new Error('ไม่พบผลลัพธ์จาก AI');
    const parsed = JSON.parse(textBlock.text);

    res.status(200).json({ ok: true, data: parsed });
  } catch (err) {
    res.status(500).json({
      ok: false,
      error: 'สแกนไม่สำเร็จ: ' + String((err && err.message) || err).slice(0, 200),
    });
  }
};
