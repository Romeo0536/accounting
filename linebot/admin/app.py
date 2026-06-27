"""
Standalone runner for local development.
On Render / production, the blueprint is mounted in the main app.py instead.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from database import init_db
from flask import Flask
from admin.blueprint import admin_bp

init_db()

app = Flask(__name__)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'mochi-admin-dev-key')
app.register_blueprint(admin_bp)

if __name__ == '__main__':
    port = int(os.environ.get('ADMIN_PORT', 5002))
    print(f'Admin panel running at http://localhost:{port}/admin/')
    app.run(host='0.0.0.0', port=port, debug=True)
