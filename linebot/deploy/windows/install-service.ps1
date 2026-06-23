# install-service.ps1
# ติดตั้ง น้องโมจิ เป็น Windows Service ด้วย NSSM
# รันด้วยสิทธิ์ Administrator

param(
    [string]$BotPath = (Resolve-Path "$PSScriptRoot\..\..").Path,
    [string]$ServiceName = "MochiLineBot",
    [string]$NssmPath = "C:\nssm\nssm.exe"
)

# Check NSSM
if (-not (Test-Path $NssmPath)) {
    Write-Host "[!] ไม่พบ NSSM ที่ $NssmPath" -ForegroundColor Red
    Write-Host "    ดาวน์โหลดได้ที่ https://nssm.cc/download" -ForegroundColor Yellow
    Write-Host "    แตกไฟล์และวางไว้ที่ C:\nssm\nssm.exe" -ForegroundColor Yellow
    exit 1
}

$PythonExe = "$BotPath\venv\Scripts\python.exe"
$AppScript  = "$BotPath\app.py"
$LogDir     = "$BotPath\logs"

# Create log dir
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "[*] ติดตั้ง $ServiceName Service..." -ForegroundColor Cyan

# Remove old service if exists
& $NssmPath stop $ServiceName 2>$null
& $NssmPath remove $ServiceName confirm 2>$null

# Install service
& $NssmPath install $ServiceName $PythonExe $AppScript
& $NssmPath set $ServiceName AppDirectory $BotPath
& $NssmPath set $ServiceName AppStdout "$LogDir\stdout.log"
& $NssmPath set $ServiceName AppStderr "$LogDir\stderr.log"
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateBytes 10485760
& $NssmPath set $ServiceName DisplayName "น้องโมจิ LINE Bot"
& $NssmPath set $ServiceName Description "LINE Bot สำหรับบันทึกไฟล์และข้อความในกลุ่ม"
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Load env file into service environment
if (Test-Path "$BotPath\.env") {
    $envContent = Get-Content "$BotPath\.env" | Where-Object { $_ -match "^[^#].*=.*" }
    foreach ($line in $envContent) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            & $NssmPath set $ServiceName AppEnvironmentExtra "+$key=$val"
        }
    }
}

# Start service
& $NssmPath start $ServiceName

$status = & $NssmPath status $ServiceName
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  น้องโมจิ Service: $status" -ForegroundColor Green
Write-Host "  Log: $LogDir\" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "คำสั่งที่ใช้บ่อย:" -ForegroundColor Yellow
Write-Host "  เริ่ม:   nssm start $ServiceName"
Write-Host "  หยุด:   nssm stop $ServiceName"
Write-Host "  สถานะ:  nssm status $ServiceName"
Write-Host "  ถอนการติดตั้ง: nssm remove $ServiceName confirm"
