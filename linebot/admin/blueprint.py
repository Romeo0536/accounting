"""
Admin Panel as a Flask Blueprint — mounted at /admin in the main app.
This lets both the LINE bot and admin share the same process, disk, and DB.
"""
import os
import logging
from math import ceil
from flask import Blueprint, render_template_string, request, redirect, url_for, session, jsonify

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

PER_PAGE = 25
_ADMIN_PW = lambda: os.environ.get('ADMIN_PASSWORD', 'mochi2024')
_BOT_NAME = lambda: os.environ.get('BOT_NAME', 'น้องโมจิ')


def _ok():
    return session.get('admin_ok') is True


# ─── Auth ──────────────────────────────────────────────────────────────────────

@admin_bp.route('/')
def index():
    return redirect(url_for('admin.groups') if _ok() else url_for('admin.login'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == _ADMIN_PW():
            session['admin_ok'] = True
            return redirect(url_for('admin.groups'))
        error = 'รหัสผ่านไม่ถูกต้อง'
    return render_template_string(_LOGIN, error=error, bot_name=_BOT_NAME())


@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


# ─── Groups ────────────────────────────────────────────────────────────────────

@admin_bp.route('/groups')
def groups():
    if not _ok():
        return redirect(url_for('admin.login'))

    from database import get_all_groups, count_groups, get_all_group_stats

    search = request.args.get('q', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    total = count_groups(search)
    total_pages = max(1, ceil(total / PER_PAGE))
    page = min(page, total_pages)

    rows = get_all_groups(search=search, page=page, per_page=PER_PAGE)
    stats = get_all_group_stats()

    return render_template_string(
        _GROUPS,
        groups=rows,
        search=search,
        page=page,
        total=total,
        total_pages=total_pages,
        stats=stats,
        bot_name=_BOT_NAME(),
        per_page=PER_PAGE,
    )


# ─── AJAX API ──────────────────────────────────────────────────────────────────

@admin_bp.route('/api/group/<group_id>/toggle', methods=['POST'])
def api_toggle(group_id):
    if not _ok():
        return jsonify({'ok': False}), 401
    from database import get_group_settings, upsert_group_settings
    field = request.json.get('field')
    if field not in {'notifications_enabled', 'archiving_enabled', 'daily_summary_enabled', 'stats_enabled'}:
        return jsonify({'ok': False}), 400
    cur = get_group_settings(group_id).get(field, 1)
    new_val = 0 if cur else 1
    upsert_group_settings(group_id, **{field: new_val})
    return jsonify({'ok': True, 'value': new_val})


@admin_bp.route('/api/group/<group_id>/email', methods=['POST'])
def api_email(group_id):
    if not _ok():
        return jsonify({'ok': False}), 401
    from database import upsert_group_settings
    email = (request.json.get('email') or '').strip()
    upsert_group_settings(group_id, email=email)
    return jsonify({'ok': True})


@admin_bp.route('/api/group/<group_id>/name', methods=['POST'])
def api_name(group_id):
    if not _ok():
        return jsonify({'ok': False}), 401
    from database import upsert_group_settings
    name = (request.json.get('name') or '').strip()
    upsert_group_settings(group_id, group_name=name)
    return jsonify({'ok': True})


@admin_bp.route('/api/bulk', methods=['POST'])
def api_bulk():
    if not _ok():
        return jsonify({'ok': False}), 401
    from database import upsert_group_settings
    data = request.json or {}
    ids = data.get('group_ids', [])
    field = data.get('field')
    value = data.get('value')
    allowed = {'notifications_enabled', 'archiving_enabled', 'daily_summary_enabled', 'stats_enabled', 'email'}
    if field not in allowed or not ids:
        return jsonify({'ok': False}), 400
    updated = 0
    for gid in ids:
        try:
            upsert_group_settings(gid, **{field: value})
            updated += 1
        except Exception as e:
            logger.error(f'Bulk update {gid}: {e}')
    return jsonify({'ok': True, 'updated': updated})


# ─── Templates ─────────────────────────────────────────────────────────────────

_LOGIN = '''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ bot_name }} Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:linear-gradient(135deg,#FF6B9D,#C44DFF);min-height:100vh;display:flex;align-items:center;justify-content:center;}
.card{border:none;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.2);max-width:380px;width:100%;}
</style>
</head>
<body>
<div class="card p-4">
  <div style="font-size:48px;text-align:center;">🍡</div>
  <h2 style="text-align:center;color:#C44DFF;font-weight:700;">{{ bot_name }}</h2>
  <p style="text-align:center;color:#888;font-size:14px;margin-bottom:24px;">Admin Panel</p>
  {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
  <form method="post">
    <div class="mb-3">
      <input type="password" name="password" class="form-control form-control-lg"
             placeholder="รหัสผ่าน" autofocus required>
    </div>
    <button type="submit" class="btn btn-lg w-100"
            style="background:#C44DFF;color:#fff;border-radius:10px;">เข้าสู่ระบบ</button>
  </form>
</div>
</body></html>'''


_GROUPS = '''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ bot_name }} Admin — จัดการกลุ่ม</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
:root{--purple:#C44DFF;--pink:#FF6B9D;}
body{background:#F8F7FF;}
.navbar{background:linear-gradient(90deg,var(--pink),var(--purple));}
.navbar-brand{color:#fff!important;font-size:20px;font-weight:700;}
.stat-card{border:none;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);}
.stat-val{font-size:30px;font-weight:700;}
.tbl-wrap{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.07);overflow:hidden;}
.table thead th{background:var(--purple);color:#fff;border:none;white-space:nowrap;}
.table td{vertical-align:middle;}
.tog{border:none;border-radius:20px;padding:3px 12px;font-size:12px;cursor:pointer;transition:.15s;}
.tog.on{background:#d4f5e2;color:#1a8c4e;}
.tog.off{background:#ffe0e0;color:#c0392b;}
.ei{border:1px solid #ddd;border-radius:8px;padding:3px 7px;font-size:12px;}
.eb{border:none;border-radius:7px;padding:3px 9px;font-size:11px;cursor:pointer;}
.gid{font-family:monospace;font-size:11px;color:#999;}
.srch{border-radius:10px;border:1px solid #ddd;padding:7px 14px;}
.bulk-bar{background:#fff8e1;border-radius:10px;padding:10px 14px;display:none;flex-wrap:wrap;gap:8px;align-items:center;}
.page-link{color:var(--purple);}
.page-item.active .page-link{background:var(--purple);border-color:var(--purple);}
</style>
</head>
<body>
<nav class="navbar px-4 py-2 d-flex justify-content-between align-items-center">
  <span class="navbar-brand">🍡 {{ bot_name }} Admin</span>
  <a href="/admin/logout" class="btn btn-sm btn-outline-light">ออก</a>
</nav>

<div class="container-fluid py-3 px-4">

  <!-- Stats -->
  <div class="row g-3 mb-3">
    <div class="col-6 col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:24px;">👥</div>
        <div class="stat-val" style="color:var(--purple);">{{ stats.groups }}</div>
        <div class="text-muted small">กลุ่มทั้งหมด</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:24px;">🧾</div>
        <div class="stat-val" style="color:var(--pink);">{{ stats.bills }}</div>
        <div class="text-muted small">บิลทั้งหมด</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:24px;">💰</div>
        <div class="stat-val" style="color:#00C070;">{{ "%.0f"|format(stats.bill_total) }}</div>
        <div class="text-muted small">ยอดบิลรวม (฿)</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:24px;">🔍</div>
        <div class="stat-val" style="color:#5B7AFF;">{{ total }}</div>
        <div class="text-muted small">กลุ่มที่ค้นพบ</div>
      </div>
    </div>
  </div>

  <!-- Search -->
  <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
    <form method="get" class="d-flex gap-2 align-items-center">
      <input class="srch" type="text" name="q" value="{{ search }}"
             placeholder="🔍 ค้นหาชื่อกลุ่ม หรือ Group ID…" style="width:260px;">
      <button type="submit" class="btn btn-sm"
              style="background:var(--purple);color:#fff;border-radius:8px;">ค้นหา</button>
      {% if search %}
      <a href="/admin/groups" class="btn btn-sm btn-outline-secondary" style="border-radius:8px;">ล้าง</a>
      {% endif %}
    </form>
    <small class="text-muted">
      แสดง {{ (page-1)*per_page+1 }}–{{ [page*per_page, total]|min }} จาก {{ total }} กลุ่ม
    </small>
  </div>

  <!-- Bulk bar -->
  <div class="bulk-bar mb-2" id="bulkBar">
    <strong id="bulkCnt"></strong> กลุ่มที่เลือก —
    <button class="btn btn-sm btn-success" onclick="bkTog('notifications_enabled',1)">🔔 เปิดแจ้งเตือน</button>
    <button class="btn btn-sm btn-secondary" onclick="bkTog('notifications_enabled',0)">🔕 ปิดแจ้งเตือน</button>
    <button class="btn btn-sm btn-success" onclick="bkTog('archiving_enabled',1)">📂 เปิดบันทึก</button>
    <button class="btn btn-sm btn-secondary" onclick="bkTog('archiving_enabled',0)">📵 ปิดบันทึก</button>
    <button class="btn btn-sm btn-success" onclick="bkTog('daily_summary_enabled',1)">📅 เปิดสรุป</button>
    <button class="btn btn-sm btn-secondary" onclick="bkTog('daily_summary_enabled',0)">📵 ปิดสรุป</button>
    <span class="d-flex gap-1 ms-1">
      <input type="email" id="bkEmail" placeholder="ตั้งอีเมลให้ทุกกลุ่ม" class="ei" style="width:200px;">
      <button class="btn btn-sm btn-primary eb" onclick="bkEmail()">ตั้งอีเมล</button>
    </span>
  </div>

  <!-- Table -->
  <div class="tbl-wrap">
    <div class="table-responsive">
      <table class="table table-hover mb-0" style="font-size:13px;">
        <thead>
          <tr>
            <th style="width:32px;"><input type="checkbox" id="chkAll"></th>
            <th>ชื่อกลุ่ม</th>
            <th>Group ID</th>
            <th>อีเมล</th>
            <th>แจ้งเตือน</th>
            <th>บันทึก</th>
            <th>สรุปรายวัน</th>
            <th>สถิติ</th>
            <th>บิล 30 วัน</th>
            <th>อัปเดต</th>
          </tr>
        </thead>
        <tbody>
        {% for g in groups %}
        <tr>
          <td><input type="checkbox" class="rc" value="{{ g.group_id }}"></td>
          <td>
            <div class="d-flex gap-1 align-items-center">
              <input class="ei ni" value="{{ g.group_name or '' }}"
                     placeholder="(ไม่มีชื่อ)" data-gid="{{ g.group_id }}" style="width:120px;">
              <button class="eb" style="background:#5B7AFF;color:#fff;"
                      onclick="saveName('{{ g.group_id }}',this)">บันทึก</button>
            </div>
          </td>
          <td><span class="gid">{{ g.group_id }}</span></td>
          <td>
            <div class="d-flex gap-1 align-items-center">
              <input type="email" class="ei" value="{{ g.email or '' }}"
                     placeholder="email@…" data-gid="{{ g.group_id }}" style="width:170px;">
              <button class="eb" style="background:var(--purple);color:#fff;"
                      onclick="saveEmail('{{ g.group_id }}',this)">บันทึก</button>
            </div>
          </td>
          <td>
            <button class="tog {{ 'on' if g.notifications_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="notifications_enabled" onclick="tog(this)">
              {{ '🔔 เปิด' if g.notifications_enabled else '🔕 ปิด' }}
            </button>
          </td>
          <td>
            <button class="tog {{ 'on' if g.archiving_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="archiving_enabled" onclick="tog(this)">
              {{ '📂 เปิด' if g.archiving_enabled else '📵 ปิด' }}
            </button>
          </td>
          <td>
            <button class="tog {{ 'on' if g.daily_summary_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="daily_summary_enabled" onclick="tog(this)">
              {{ '📅 เปิด' if g.daily_summary_enabled else '📵 ปิด' }}
            </button>
          </td>
          <td>
            <button class="tog {{ 'on' if g.stats_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="stats_enabled" onclick="tog(this)">
              {{ '📊 เปิด' if g.stats_enabled else '📵 ปิด' }}
            </button>
          </td>
          <td class="text-end">
            {% if g.bill_count_30d %}
            <span style="color:#B8860B;font-weight:600;">{{ g.bill_count_30d }}</span>
            <small class="d-block text-muted">{{ "%.0f"|format(g.bill_total_30d or 0) }} ฿</small>
            {% else %}<span class="text-muted">—</span>{% endif %}
          </td>
          <td style="color:#bbb;white-space:nowrap;">{{ g.updated_at[:16] if g.updated_at else '—' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="10" class="text-center py-5 text-muted">ไม่พบกลุ่ม</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Pagination -->
  {% if total_pages > 1 %}
  <nav class="mt-3">
    <ul class="pagination justify-content-center mb-0">
      <li class="page-item {{ 'disabled' if page==1 }}">
        <a class="page-link" href="?q={{ search }}&page={{ page-1 }}">‹</a>
      </li>
      {% for p in range([1,page-3]|max, [total_pages+1,page+4]|min) %}
      <li class="page-item {{ 'active' if p==page }}">
        <a class="page-link" href="?q={{ search }}&page={{ p }}">{{ p }}</a>
      </li>
      {% endfor %}
      <li class="page-item {{ 'disabled' if page==total_pages }}">
        <a class="page-link" href="?q={{ search }}&page={{ page+1 }}">›</a>
      </li>
    </ul>
  </nav>
  {% endif %}

</div>

<div id="toast" style="position:fixed;bottom:20px;right:20px;background:#333;color:#fff;
     padding:9px 18px;border-radius:10px;display:none;z-index:9999;font-size:13px;"></div>

<script>
const BASE = '/admin';
function toast(msg,ok=true){
  const t=document.getElementById('toast');
  t.textContent=msg; t.style.background=ok?'#1a8c4e':'#c0392b';
  t.style.display='block'; setTimeout(()=>t.style.display='none',2500);
}
async function tog(btn){
  const r=await fetch(`${BASE}/api/group/${btn.dataset.gid}/toggle`,
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({field:btn.dataset.field})});
  const d=await r.json();
  if(!d.ok){toast('❌ เกิดข้อผิดพลาด',false);return;}
  const on=d.value===1;
  const L={notifications_enabled:['🔔 เปิด','🔕 ปิด'],archiving_enabled:['📂 เปิด','📵 ปิด'],
            daily_summary_enabled:['📅 เปิด','📵 ปิด'],stats_enabled:['📊 เปิด','📵 ปิด']};
  btn.textContent=on?L[btn.dataset.field][0]:L[btn.dataset.field][1];
  btn.className='tog '+(on?'on':'off');
  toast(on?'✅ เปิดแล้ว':'✅ ปิดแล้ว');
}
async function saveEmail(gid,btn){
  const v=btn.previousElementSibling.value.trim();
  const r=await fetch(`${BASE}/api/group/${gid}/email`,
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:v})});
  const d=await r.json(); toast(d.ok?'✅ บันทึกอีเมลแล้ว':'❌ เกิดข้อผิดพลาด',d.ok);
}
async function saveName(gid,btn){
  const v=document.querySelector(`.ni[data-gid="${gid}"]`).value.trim();
  const r=await fetch(`${BASE}/api/group/${gid}/name`,
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:v})});
  const d=await r.json(); toast(d.ok?'✅ บันทึกชื่อแล้ว':'❌ เกิดข้อผิดพลาด',d.ok);
}
// Checkbox / bulk
const chkAll=document.getElementById('chkAll');
chkAll.addEventListener('change',()=>{
  document.querySelectorAll('.rc').forEach(c=>c.checked=chkAll.checked); upd();
});
document.querySelectorAll('.rc').forEach(c=>c.addEventListener('change',upd));
function getSel(){return Array.from(document.querySelectorAll('.rc:checked')).map(c=>c.value);}
function upd(){
  const s=getSel(); document.getElementById('bulkCnt').textContent=s.length;
  document.getElementById('bulkBar').style.display=s.length?'flex':'none';
}
async function bkTog(field,value){
  const ids=getSel(); if(!ids.length)return;
  const r=await fetch(`${BASE}/api/bulk`,
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({group_ids:ids,field,value})});
  const d=await r.json();
  if(d.ok){toast(`✅ อัปเดต ${d.updated} กลุ่มแล้ว`);setTimeout(()=>location.reload(),1200);}
  else toast('❌ เกิดข้อผิดพลาด',false);
}
async function bkEmail(){
  const ids=getSel(); const email=document.getElementById('bkEmail').value.trim();
  if(!ids.length||!email){toast('กรุณาเลือกกลุ่มและระบุอีเมล',false);return;}
  const r=await fetch(`${BASE}/api/bulk`,
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({group_ids:ids,field:'email',value:email})});
  const d=await r.json();
  toast(d.ok?`✅ ตั้งอีเมลให้ ${d.updated} กลุ่มแล้ว`:'❌ เกิดข้อผิดพลาด',d.ok);
  if(d.ok)setTimeout(()=>location.reload(),1200);
}
// Enter to save
document.querySelectorAll('.ei').forEach(el=>{
  el.addEventListener('keydown',e=>{ if(e.key==='Enter') el.nextElementSibling.click(); });
});
</script>
</body></html>'''
