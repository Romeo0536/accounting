# คู่มือตั้งค่า HR System + Google Drive

โปรแกรม HR (`index.html`) ใช้งานได้ 2 โหมด:

- **โหมดออฟไลน์** (ค่าเริ่มต้น) — เปิดไฟล์ด้วยเบราว์เซอร์ได้ทันที ข้อมูลเก็บในเครื่อง
- **โหมดคลาวด์** — ล็อกอิน Google แล้วเก็บข้อมูลบน Google Drive ของคุณ เข้าจากเครื่องไหนก็ได้

ถ้าต้องการเฉพาะโหมดออฟไลน์ ไม่ต้องทำอะไรเพิ่ม — ดับเบิลคลิก `index.html` ได้เลย

---

## เปิดใช้โหมด Google Drive

ต้องทำ 3 ขั้นตอน: (1) โฮสต์แอปบนเว็บ → (2) สร้าง OAuth Client ID → (3) ใส่ Client ID ในแอป

### ⚠️ ทำไมต้องโฮสต์บนเว็บ
Google บังคับให้แอปที่เชื่อม Drive ต้องรันผ่าน `https://` หรือ `http://localhost`
— **เปิดไฟล์ตรง ๆ (`file://...`) จะล็อกอินไม่ได้**

---

### ขั้นที่ 1 — เปิด GitHub Pages (ฟรี)

1. ไปที่ repo บน GitHub → **Settings** → **Pages**
2. หัวข้อ **Source** เลือก **Deploy from a branch**
3. เลือก **branch** ที่มีไฟล์ `index.html` และโฟลเดอร์ **/ (root)** แล้วกด **Save**
4. รอสักครู่ GitHub จะให้ URL มา เช่น:

   ```
   https://romeo0536.github.io/accounting/
   ```

   จำ **origin** ไว้ (ส่วนหน้าเท่านั้น ไม่รวม path):
   ```
   https://romeo0536.github.io
   ```

---

### ขั้นที่ 2 — สร้าง OAuth Client ID บน Google Cloud

1. เข้า https://console.cloud.google.com/ แล้วสร้าง **โปรเจกต์ใหม่** (หรือใช้อันเดิม)
2. เปิดใช้ **Google Drive API**
   `APIs & Services` → `Library` → ค้นหา **Google Drive API** → **Enable**
3. ตั้งค่าหน้าจอยินยอม `APIs & Services` → **OAuth consent screen**
   - User Type: **External** → สร้าง
   - กรอกชื่อแอป, อีเมล (ใส่เท่าที่จำเป็น)
   - หัวข้อ **Test users** เพิ่มอีเมล Google ที่คุณจะใช้ล็อกอิน
4. สร้าง Client ID `APIs & Services` → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - **Authorized JavaScript origins** → **ADD URI** → ใส่ origin จากขั้นที่ 1:
     ```
     https://romeo0536.github.io
     ```
     (ถ้าจะทดสอบบนเครื่องด้วย ให้เพิ่ม `http://localhost:8000` อีกอัน)
   - กด **Create** → คัดลอก **Client ID** ที่ได้ (ลงท้ายด้วย `.apps.googleusercontent.com`)

---

### ขั้นที่ 3 — ใส่ Client ID ในแอป

เปิดไฟล์ `index.html` หาบรรทัด:

```js
const GOOGLE_CLIENT_ID = '';
```

ใส่ Client ID ของคุณลงไป:

```js
const GOOGLE_CLIENT_ID = '1234567890-abcxyz.apps.googleusercontent.com';
```

commit + push แล้ว GitHub Pages จะอัปเดตให้อัตโนมัติ

---

## การใช้งาน

1. เปิดแอปผ่าน URL ของ GitHub Pages
2. กดปุ่ม **☁️ ล็อกอิน Google Drive** ที่แถบซ้ายล่าง
3. ครั้งแรกจะสร้างไฟล์ `hr_data.json` ใน Drive ของคุณ
4. ทุกการแก้ไขจะบันทึกขึ้น Drive อัตโนมัติ
5. เปิดเครื่องอื่นแล้วล็อกอินบัญชีเดิม → เห็นข้อมูลชุดเดียวกัน

---

## หมายเหตุ

- **สิทธิ์ที่ขอ:** `drive.file` — แอปเข้าถึงได้เฉพาะไฟล์ที่ตัวเองสร้าง (อ่าน/แก้ไฟล์อื่นใน Drive ไม่ได้) ปลอดภัย
- **Client ID เปิดเผยในโค้ดได้:** เป็นค่าสาธารณะ ความปลอดภัยมาจากรายการ origin ที่อนุญาต
- **ข้อมูลชนกัน:** ถ้าแก้พร้อมกันหลายเครื่อง ใช้หลักการ "บันทึกล่าสุดชนะ" (last-write-wins)
- ยังมี localStorage เป็น cache ออฟไลน์ — เน็ตหลุดก็ยังใช้งานต่อได้ แล้วค่อยซิงค์เมื่อกลับมา
