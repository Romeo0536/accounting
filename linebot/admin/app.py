"""
น้องโมจิ Admin Panel  —  port 5002
Standalone Flask app for managing hundreds of LINE groups.
"""
import sys
import os

# Allow importing database.py from the parent linebot/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import logging
from math import ceil
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

from database import (
    init_db, get_all_groups, count_groups, get_all_group_stats,
    upsert_group_settings, get_group_settings, get_bill_summary
)

init_db()

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'mochi2024')
BOT_NAME = os.environ.get('BOT_NAME', 'น้องโมจิ')
PER_PAGE = 25

app = Flask(__name__)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'mochi-admin-secret-key-2024')

# ─── Auth ──────────────────────────────────────────────────────────────────────

def _logged_in():
    return session.get('admin_logged_in') is True


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('groups'))
        error = 'รหัสผ่านไม่ถูกต้อง'
    return render_template_string(LOGIN_HTML, error=error, bot_name=BOT_NAME)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    if not _logged_in():
        return redirect(url_for('login'))
    return redirect(url_for('groups'))


# ─── Groups ────────────────────────────────────────────────────────────────────

@app.route('/groups')
def groups():
    if not _logged_in():
        return redirect(url_for('login'))

    search = request.args.get('q', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    total = count_groups(search)
    total_pages = max(1, ceil(total / PER_PAGE))
    page = min(page, total_pages)

    rows = get_all_groups(search=search, page=page, per_page=PER_PAGE)
    stats = get_all_group_stats()

    return render_template_string(
        GROUPS_HTML,
        groups=rows,
        search=search,
        page=page,
        total=total,
        total_pages=total_pages,
        stats=stats,
        bot_name=BOT_NAME,
        per_page=PER_PAGE,
    )


# ─── AJAX API ──────────────────────────────────────────────────────────────────

@app.route('/api/group/<group_id>/toggle', methods=['POST'])
def api_toggle(group_id):
    if not _logged_in():
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    field = request.json.get('field')
    allowed = {'notifications_enabled', 'archiving_enabled', 'daily_summary_enabled', 'stats_enabled'}
    if field not in allowed:
        return jsonify({'ok': False, 'error': 'invalid field'}), 400

    settings = get_group_settings(group_id)
    current = settings.get(field, 1)
    new_val = 0 if current else 1
    upsert_group_settings(group_id, **{field: new_val})
    return jsonify({'ok': True, 'value': new_val})


@app.route('/api/group/<group_id>/email', methods=['POST'])
def api_set_email(group_id):
    if not _logged_in():
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    email = (request.json.get('email') or '').strip()
    upsert_group_settings(group_id, email=email)
    return jsonify({'ok': True, 'email': email})


@app.route('/api/group/<group_id>/name', methods=['POST'])
def api_set_name(group_id):
    if not _logged_in():
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    name = (request.json.get('name') or '').strip()
    upsert_group_settings(group_id, group_name=name)
    return jsonify({'ok': True, 'name': name})


@app.route('/api/bulk', methods=['POST'])
def api_bulk():
    """Bulk update a field for all selected group IDs."""
    if not _logged_in():
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    data = request.json or {}
    group_ids = data.get('group_ids', [])
    field = data.get('field')
    value = data.get('value')

    allowed_fields = {'notifications_enabled', 'archiving_enabled',
                      'daily_summary_enabled', 'stats_enabled', 'email'}
    if field not in allowed_fields:
        return jsonify({'ok': False, 'error': 'invalid field'}), 400
    if not group_ids:
        return jsonify({'ok': False, 'error': 'no groups'}), 400

    updated = 0
    for gid in group_ids:
        try:
            upsert_group_settings(gid, **{field: value})
            updated += 1
        except Exception as e:
            logger.error(f'Bulk update failed for {gid}: {e}')

    return jsonify({'ok': True, 'updated': updated})


# ─── Templates ─────────────────────────────────────────────────────────────────

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ bot_name }} Admin — Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:linear-gradient(135deg,#FF6B9D,#C44DFF);min-height:100vh;display:flex;align-items:center;justify-content:center;}
.card{border:none;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.2);max-width:380px;width:100%;}
.logo{font-size:48px;text-align:center;margin-bottom:8px;}
h2{text-align:center;color:#C44DFF;font-weight:700;}
.sub{text-align:center;color:#888;font-size:14px;margin-bottom:24px;}
</style>
</head>
<body>
<div class="card p-4">
  <div class="logo">🍡</div>
  <h2>{{ bot_name }}</h2>
  <p class="sub">Admin Panel</p>
  {% if error %}
  <div class="alert alert-danger py-2">{{ error }}</div>
  {% endif %}
  <form method="post">
    <div class="mb-3">
      <input type="password" name="password" class="form-control form-control-lg"
             placeholder="รหัสผ่าน" autofocus required>
    </div>
    <button type="submit" class="btn btn-lg w-100" style="background:#C44DFF;color:#fff;border-radius:10px;">
      เข้าสู่ระบบ
    </button>
  </form>
</div>
</body>
</html>'''


GROUPS_HTML = '''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ bot_name }} Admin — จัดการกลุ่ม</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
:root{--purple:#C44DFF;--pink:#FF6B9D;}
body{background:#F8F7FF;font-family:"Sarabun",sans-serif;}
.navbar{background:linear-gradient(90deg,var(--pink),var(--purple));}
.navbar-brand{color:#fff!important;font-size:22px;font-weight:700;}
.stat-card{border:none;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);}
.stat-val{font-size:32px;font-weight:700;}
.table-wrapper{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.07);overflow:hidden;}
.table thead th{background:var(--purple);color:#fff;border:none;font-weight:600;white-space:nowrap;}
.table td{vertical-align:middle;}
.toggle-btn{border:none;border-radius:20px;padding:3px 14px;font-size:13px;cursor:pointer;transition:.2s;}
.toggle-btn.on{background:#d4f5e2;color:#1a8c4e;}
.toggle-btn.off{background:#ffe0e0;color:#c0392b;}
.email-cell{display:flex;align-items:center;gap:6px;}
.email-input{border:1px solid #ddd;border-radius:8px;padding:4px 8px;font-size:13px;width:180px;}
.email-save{border:none;background:var(--purple);color:#fff;border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer;}
.name-cell{display:flex;align-items:center;gap:6px;}
.name-input{border:1px solid #ddd;border-radius:8px;padding:4px 8px;font-size:13px;width:130px;}
.name-save{border:none;background:#5B7AFF;color:#fff;border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer;}
.gid{font-family:monospace;font-size:11px;color:#888;}
.search-box{border-radius:10px;border:1px solid #ddd;padding:8px 16px;width:280px;}
.bulk-bar{background:#fff3cd;border-radius:10px;padding:10px 16px;display:none;align-items:center;gap:12px;flex-wrap:wrap;}
.page-link{color:var(--purple);}
.page-item.active .page-link{background:var(--purple);border-color:var(--purple);}
</style>
</head>
<body>

<nav class="navbar px-4 py-2">
  <span class="navbar-brand">🍡 {{ bot_name }} Admin</span>
  <a href="/logout" class="btn btn-sm btn-outline-light">ออกจากระบบ</a>
</nav>

<div class="container-fluid py-4 px-4">

  <!-- Stats Cards -->
  <div class="row g-3 mb-4">
    <div class="col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:28px;">👥</div>
        <div class="stat-val" style="color:var(--purple);">{{ stats.groups }}</div>
        <div class="text-muted">กลุ่มทั้งหมด</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:28px;">🧾</div>
        <div class="stat-val" style="color:#FF6B9D;">{{ stats.bills }}</div>
        <div class="text-muted">บิลทั้งหมด</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:28px;">💰</div>
        <div class="stat-val" style="color:#00C070;">{{ "%.0f"|format(stats.bill_total) }}</div>
        <div class="text-muted">ยอดบิลรวม (฿)</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="stat-card card text-center p-3">
        <div style="font-size:28px;">📄</div>
        <div class="stat-val" style="color:#5B7AFF;">{{ total }}</div>
        <div class="text-muted">กลุ่มที่ค้นพบ</div>
      </div>
    </div>
  </div>

  <!-- Search + Bulk -->
  <div class="d-flex align-items-center gap-3 mb-3 flex-wrap">
    <form method="get" class="d-flex gap-2 align-items-center">
      <input class="search-box" type="text" name="q" value="{{ search }}"
             placeholder="🔍 ค้นหาชื่อกลุ่มหรือ Group ID…">
      <button type="submit" class="btn btn-sm" style="background:var(--purple);color:#fff;border-radius:8px;">ค้นหา</button>
      {% if search %}
      <a href="/groups" class="btn btn-sm btn-outline-secondary" style="border-radius:8px;">ล้าง</a>
      {% endif %}
    </form>
    <span class="text-muted" style="font-size:13px;">
      แสดง {{ (page-1)*per_page+1 }}–{{ [page*per_page, total]|min }} จาก {{ total }} กลุ่ม
    </span>
  </div>

  <!-- Bulk action bar -->
  <div class="bulk-bar mb-3" id="bulkBar">
    <span id="bulkCount" class="fw-bold"></span>
    <span>กลุ่มที่เลือก —</span>
    <button class="btn btn-sm btn-success" onclick="bulkToggle('notifications_enabled',1)">🔔 เปิดแจ้งเตือนทั้งหมด</button>
    <button class="btn btn-sm btn-secondary" onclick="bulkToggle('notifications_enabled',0)">🔕 ปิดแจ้งเตือนทั้งหมด</button>
    <button class="btn btn-sm btn-success" onclick="bulkToggle('daily_summary_enabled',1)">📅 เปิดสรุปทั้งหมด</button>
    <button class="btn btn-sm btn-secondary" onclick="bulkToggle('daily_summary_enabled',0)">📵 ปิดสรุปทั้งหมด</button>
    <button class="btn btn-sm btn-success" onclick="bulkToggle('archiving_enabled',1)">📂 เปิดบันทึกทั้งหมด</button>
    <button class="btn btn-sm btn-secondary" onclick="bulkToggle('archiving_enabled',0)">📵 ปิดบันทึกทั้งหมด</button>
    <div class="d-flex gap-1 align-items-center ms-2">
      <input type="email" id="bulkEmail" placeholder="อีเมลสำหรับทุกกลุ่มที่เลือก"
             style="border:1px solid #ddd;border-radius:8px;padding:4px 10px;font-size:13px;width:220px;">
      <button class="btn btn-sm btn-primary" onclick="bulkEmail()">ตั้งอีเมล</button>
    </div>
  </div>

  <!-- Table -->
  <div class="table-wrapper">
    <div class="table-responsive">
      <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th style="width:36px;"><input type="checkbox" id="checkAll"></th>
            <th>ชื่อกลุ่ม</th>
            <th>Group ID</th>
            <th>อีเมล</th>
            <th>แจ้งเตือน</th>
            <th>บันทึก</th>
            <th>สรุปรายวัน</th>
            <th>สถิติ</th>
            <th>บิล<br><small style="font-weight:400;">30 วัน</small></th>
            <th>อัปเดต</th>
          </tr>
        </thead>
        <tbody>
        {% for g in groups %}
        <tr data-gid="{{ g.group_id }}">
          <td><input type="checkbox" class="row-check" value="{{ g.group_id }}"></td>
          <td>
            <div class="name-cell">
              <input class="name-input" value="{{ g.group_name or '' }}"
                     placeholder="(ยังไม่ตั้งชื่อ)" data-gid="{{ g.group_id }}">
              <button class="name-save" onclick="saveName('{{ g.group_id }}', this)">บันทึก</button>
            </div>
          </td>
          <td><span class="gid">{{ g.group_id }}</span></td>
          <td>
            <div class="email-cell">
              <input type="email" class="email-input" value="{{ g.email or '' }}"
                     placeholder="email@example.com" data-gid="{{ g.group_id }}">
              <button class="email-save" onclick="saveEmail('{{ g.group_id }}', this)">บันทึก</button>
            </div>
          </td>
          <td>
            <button class="toggle-btn {{ 'on' if g.notifications_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="notifications_enabled"
                    onclick="toggle(this)">
              {{ '🔔 เปิด' if g.notifications_enabled else '🔕 ปิด' }}
            </button>
          </td>
          <td>
            <button class="toggle-btn {{ 'on' if g.archiving_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="archiving_enabled"
                    onclick="toggle(this)">
              {{ '📂 เปิด' if g.archiving_enabled else '📵 ปิด' }}
            </button>
          </td>
          <td>
            <button class="toggle-btn {{ 'on' if g.daily_summary_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="daily_summary_enabled"
                    onclick="toggle(this)">
              {{ '📅 เปิด' if g.daily_summary_enabled else '📵 ปิด' }}
            </button>
          </td>
          <td>
            <button class="toggle-btn {{ 'on' if g.stats_enabled else 'off' }}"
                    data-gid="{{ g.group_id }}" data-field="stats_enabled"
                    onclick="toggle(this)">
              {{ '📊 เปิด' if g.stats_enabled else '📵 ปิด' }}
            </button>
          </td>
          <td style="text-align:right;">
            {% if g.bill_count_30d %}
            <span style="color:#B8860B;font-weight:600;">{{ g.bill_count_30d }}</span>
            <small class="d-block text-muted">{{ "%.0f"|format(g.bill_total_30d or 0) }} ฿</small>
            {% else %}
            <span class="text-muted">—</span>
            {% endif %}
          </td>
          <td style="font-size:12px;color:#999;white-space:nowrap;">
            {{ g.updated_at[:16] if g.updated_at else '—' }}
          </td>
        </tr>
        {% else %}
        <tr><td colspan="10" class="text-center py-5 text-muted">ไม่พบกลุ่มที่ตรงกัน</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Pagination -->
  {% if total_pages > 1 %}
  <nav class="mt-4">
    <ul class="pagination justify-content-center">
      <li class="page-item {{ 'disabled' if page==1 }}">
        <a class="page-link" href="?q={{ search }}&page={{ page-1 }}">‹ ก่อนหน้า</a>
      </li>
      {% for p in range([1,page-3]|max, [total_pages+1,page+4]|min) %}
      <li class="page-item {{ 'active' if p==page }}">
        <a class="page-link" href="?q={{ search }}&page={{ p }}">{{ p }}</a>
      </li>
      {% endfor %}
      <li class="page-item {{ 'disabled' if page==total_pages }}">
        <a class="page-link" href="?q={{ search }}&page={{ page+1 }}">ถัดไป ›</a>
      </li>
    </ul>
  </nav>
  {% endif %}

</div><!-- /container -->

<div id="toast" style="position:fixed;bottom:24px;right:24px;background:#333;color:#fff;
     padding:10px 20px;border-radius:10px;display:none;z-index:9999;font-size:14px;"></div>

<script>
function showToast(msg, ok=true) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = ok ? '#1a8c4e' : '#c0392b';
  t.style.display = 'block';
  setTimeout(() => t.style.display='none', 2500);
}

async function toggle(btn) {
  const gid = btn.dataset.gid;
  const field = btn.dataset.field;
  const res = await fetch(`/api/group/${gid}/toggle`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({field})
  });
  const data = await res.json();
  if (data.ok) {
    const on = data.value === 1;
    const labels = {
      notifications_enabled: ['🔔 เปิด','🔕 ปิด'],
      archiving_enabled: ['📂 เปิด','📵 ปิด'],
      daily_summary_enabled: ['📅 เปิด','📵 ปิด'],
      stats_enabled: ['📊 เปิด','📵 ปิด'],
    };
    btn.textContent = on ? labels[field][0] : labels[field][1];
    btn.className = 'toggle-btn ' + (on ? 'on' : 'off');
    showToast(on ? '✅ เปิดแล้ว' : '✅ ปิดแล้ว');
  } else {
    showToast('❌ เกิดข้อผิดพลาด', false);
  }
}

async function saveEmail(gid, btn) {
  const input = btn.previousElementSibling;
  const email = input.value.trim();
  const res = await fetch(`/api/group/${gid}/email`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({email})
  });
  const data = await res.json();
  showToast(data.ok ? '✅ บันทึกอีเมลแล้ว' : '❌ เกิดข้อผิดพลาด', data.ok);
}

async function saveName(gid, btn) {
  const input = document.querySelector(`input.name-input[data-gid="${gid}"]`);
  const name = input.value.trim();
  const res = await fetch(`/api/group/${gid}/name`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name})
  });
  const data = await res.json();
  showToast(data.ok ? '✅ บันทึกชื่อแล้ว' : '❌ เกิดข้อผิดพลาด', data.ok);
}

// Checkbox logic
const checkAll = document.getElementById('checkAll');
checkAll.addEventListener('change', () => {
  document.querySelectorAll('.row-check').forEach(c => c.checked = checkAll.checked);
  updateBulkBar();
});
document.querySelectorAll('.row-check').forEach(c => {
  c.addEventListener('change', updateBulkBar);
});
function getSelected() {
  return Array.from(document.querySelectorAll('.row-check:checked')).map(c => c.value);
}
function updateBulkBar() {
  const sel = getSelected();
  const bar = document.getElementById('bulkBar');
  document.getElementById('bulkCount').textContent = sel.length;
  bar.style.display = sel.length > 0 ? 'flex' : 'none';
}

async function bulkToggle(field, value) {
  const ids = getSelected();
  if (!ids.length) return;
  const res = await fetch('/api/bulk', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({group_ids: ids, field, value})
  });
  const data = await res.json();
  if (data.ok) {
    showToast(`✅ อัปเดต ${data.updated} กลุ่มแล้ว`);
    setTimeout(() => location.reload(), 1200);
  } else {
    showToast('❌ เกิดข้อผิดพลาด', false);
  }
}

async function bulkEmail() {
  const ids = getSelected();
  const email = document.getElementById('bulkEmail').value.trim();
  if (!ids.length || !email) { showToast('กรุณาเลือกกลุ่มและระบุอีเมล', false); return; }
  const res = await fetch('/api/bulk', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({group_ids: ids, field: 'email', value: email})
  });
  const data = await res.json();
  showToast(data.ok ? `✅ ตั้งอีเมลให้ ${data.updated} กลุ่มแล้ว` : '❌ เกิดข้อผิดพลาด', data.ok);
  if (data.ok) setTimeout(() => location.reload(), 1200);
}

// Save email on Enter key
document.querySelectorAll('.email-input').forEach(input => {
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') input.nextElementSibling.click();
  });
});
document.querySelectorAll('.name-input').forEach(input => {
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') input.nextElementSibling.click();
  });
});
</script>
</body>
</html>'''


if __name__ == '__main__':
    port = int(os.environ.get('ADMIN_PORT', 5002))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    logger.info(f'Starting {BOT_NAME} Admin on port {port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
