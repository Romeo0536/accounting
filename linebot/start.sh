#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create .env from example if not exists
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Created .env from .env.example — กรุณาใส่ค่า token ก่อนรัน"
  exit 1
fi

# Create venv if not exists
if [ ! -d venv ]; then
  echo "📦 สร้าง virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

mkdir -p storage

echo "🍡 Starting น้องโมจิ LINE Bot..."
python app.py
