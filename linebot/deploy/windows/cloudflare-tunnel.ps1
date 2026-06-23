# cloudflare-tunnel.ps1
# ตั้งค่า Cloudflare Tunnel สำหรับ HTTPS ฟรี ไม่ต้องเปิด port
# ไม่ต้องมี domain / SSL certificate
#
# ข้อดี:
#   - HTTPS อัตโนมัติ ไม่ต้องซื้อ SSL
#   - ไม่ต้อง port-forward บน router
#   - URL คงที่ ใช้ได้นาน
#   - ฟรี (Cloudflare Zero Trust Free tier)
#
# ขั้นตอน:
#   1. สมัคร Cloudflare (ฟรี): https://dash.cloudflare.com/sign-up
#   2. ไปที่ Zero Trust → Tunnels → Create a tunnel
#   3. ตั้งชื่อ เช่น "mochi-line-bot"
#   4. ดาวน์โหลด cloudflared.exe และรันคำสั่งที่ได้
#   5. เพิ่ม Public Hostname: subdomain.yourdomain.com → http://localhost:5001
#   6. ใช้ URL นั้นเป็น LINE Webhook URL

Write-Host "=== Cloudflare Tunnel Setup Guide ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "วิธีที่ 1: ใช้ Cloudflare Zero Trust (URL คงที่ แนะนำ)" -ForegroundColor Green
Write-Host "  1. https://dash.cloudflare.com → Zero Trust → Networks → Tunnels"
Write-Host "  2. Create tunnel → ตั้งชื่อ 'mochi-line-bot'"
Write-Host "  3. ดาวน์โหลด cloudflared.exe ตาม OS"
Write-Host "  4. รันคำสั่งที่ได้ใน CMD (ขึ้นต้นด้วย cloudflared.exe service install ...)"
Write-Host "  5. เพิ่ม Public Hostname:"
Write-Host "     Subdomain: mochi"
Write-Host "     Domain: yourdomain.com  (หรือ workers.dev ฟรี)"
Write-Host "     Service: http://localhost:5001"
Write-Host "  6. LINE Webhook URL: https://mochi.yourdomain.com/webhook"
Write-Host ""
Write-Host "วิธีที่ 2: Quick tunnel (URL เปลี่ยนทุกครั้งรัน - ใช้ test เท่านั้น)" -ForegroundColor Yellow
Write-Host "  cloudflared.exe tunnel --url http://localhost:5001"
Write-Host ""

# ตรวจสอบว่ามี cloudflared แล้วหรือยัง
$cfPath = "C:\cloudflared\cloudflared.exe"
if (-not (Test-Path $cfPath)) {
    Write-Host "[*] ดาวน์โหลด cloudflared..." -ForegroundColor Cyan
    $downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    New-Item -ItemType Directory -Force -Path "C:\cloudflared" | Out-Null
    Invoke-WebRequest -Uri $downloadUrl -OutFile $cfPath
    Write-Host "[+] ดาวน์โหลดสำเร็จ: $cfPath" -ForegroundColor Green
} else {
    Write-Host "[+] พบ cloudflared แล้ว: $cfPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "รัน quick tunnel (สำหรับทดสอบ):" -ForegroundColor Yellow
Write-Host "  $cfPath tunnel --url http://localhost:5001"
