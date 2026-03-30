from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os, json, secrets
from datetime import datetime, timezone, timedelta

TZ_BANGKOK = timezone(timedelta(hours=7))

def now_bangkok():
    return datetime.now(TZ_BANGKOK).isoformat()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(__name__, static_folder=os.path.join(ROOT_DIR, 'frontend'))

CORS(app,
     supports_credentials=True,
     origins=[
         'https://bundit4102.github.io',
         'https://portfolio-dashboard-v1.onrender.com',
         'http://localhost:5000',
         'http://127.0.0.1:5000',
     ],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

app.secret_key = 'portfolio-secret-2026-change-in-production'

# ✅ รองรับ cross-origin session บน Render (HTTPS)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 ชั่วโมง

# รองรับทั้ง SQLite (local/Render free) และ PostgreSQL (Render paid)
if os.environ.get("DATABASE_URL"):
    db_url = os.environ.get("DATABASE_URL")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(ROOT_DIR, 'portfolio.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id           = db.Column(db.String(50),  primary_key=True)
    username     = db.Column(db.String(80),  unique=True, nullable=False)
    password_hash= db.Column(db.String(256), nullable=False)
    name         = db.Column(db.String(200))
    dept         = db.Column(db.String(200))
    role         = db.Column(db.String(50),  default='Viewer')
    status       = db.Column(db.String(50),  default='pending')
    created_at   = db.Column(db.String(50))
    # ✅ token สำหรับ cross-origin auth (GitHub Pages → Render)
    token        = db.Column(db.String(64),  nullable=True)

    def to_dict(self):
        return {
            'id':        self.id,
            'username':  self.username,
            'name':      self.name or '',
            'dept':      self.dept or '',
            'role':      self.role,
            'status':    self.status,
            'createdAt': self.created_at or now_bangkok(),
        }

class Project(db.Model):
    __tablename__ = 'projects'
    id   = db.Column(db.String(50), primary_key=True)
    data = db.Column(db.Text,       nullable=False)

    def to_dict(self):
        return json.loads(self.data)

class Idea(db.Model):
    __tablename__ = 'ideas'
    id   = db.Column(db.String(50), primary_key=True)
    data = db.Column(db.Text,       nullable=False)

    def to_dict(self):
        return json.loads(self.data)

# ─── Token store สำหรับ admin (in-memory) ────────────────────────────────────
# admin ไม่มี DB row — เก็บ token ใน dict แทน
_admin_tokens = set()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_token_from_request():
    """อ่าน token จาก Authorization header หรือ query param"""
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return request.args.get('token', '').strip() or None

def _current_user():
    """
    ตรวจสอบ identity จาก:
    1. Authorization: Bearer <token>  ← ใช้เมื่อ cross-origin (GitHub Pages)
    2. session['uid']                 ← ใช้เมื่อ same-origin (Render โดยตรง)
    """
    # 1. Token-based (cross-origin)
    token = _get_token_from_request()
    if token:
        if token in _admin_tokens:
            return {'id': '__admin__', 'role': 'Admin', 'status': 'approved'}
        user = User.query.filter_by(token=token).first()
        if user:
            return user
        return None

    # 2. Session-based (same-origin)
    uid = session.get('uid')
    if not uid:
        return None
    if uid == '__admin__':
        return {'id': '__admin__', 'role': 'Admin', 'status': 'approved'}
    return User.query.get(uid)

def _is_admin():
    u = _current_user()
    if not u:
        return False
    role = u['role'] if isinstance(u, dict) else u.role
    return role == 'Admin'

def _is_authenticated():
    u = _current_user()
    if not u:
        return False
    if isinstance(u, dict):
        return True
    return u.status == 'approved'

def _get_role():
    u = _current_user()
    if not u:
        return None
    return u['role'] if isinstance(u, dict) else u.role

# ─── CORS preflight handler ──────────────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '')
    allowed = [
        'https://bundit4102.github.io',
        'https://portfolio-dashboard-v1.onrender.com',
        'http://localhost:5000',
        'http://127.0.0.1:5000',
    ]
    if origin in allowed:
        response.headers['Access-Control-Allow-Origin']      = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods']     = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Headers']     = 'Content-Type,Authorization'
    return response

@app.route('/api/auth/register', methods=['OPTIONS'])
@app.route('/api/auth/login',    methods=['OPTIONS'])
@app.route('/api/data',          methods=['OPTIONS'])
def handle_options(*args, **kwargs):
    return '', 204

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    body     = request.get_json() or {}
    username = (body.get('username') or '').strip()
    password =  body.get('password') or ''

    # Built-in admin
    if username == 'admin' and password == 'admin2026':
        # สร้าง token ใหม่ทุกครั้ง login
        token = secrets.token_hex(32)
        _admin_tokens.add(token)

        session.permanent = True
        session['uid'] = '__admin__'
        return jsonify({'success': True, 'token': token, 'user': {
            'id': '__admin__', 'username': 'admin', 'name': 'System Admin',
            'dept': 'Administration', 'role': 'Admin', 'status': 'approved',
            'createdAt': now_bangkok(),
        }})

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'error': 'Username หรือ Password ไม่ถูกต้อง'})

    if user.status == 'rejected':
        return jsonify({'success': False, 'error': 'บัญชีของคุณถูกปฏิเสธ กรุณาติดต่อ Admin'})

    # สร้าง token และบันทึกลง DB
    token = secrets.token_hex(32)
    user.token = token
    db.session.commit()

    session.permanent = True
    session['uid'] = user.id
    return jsonify({
        'success': True,
        'pending': user.status == 'pending',
        'token':   token,
        'user':    user.to_dict(),
    })

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    body     = request.get_json() or {}
    username = (body.get('username') or '').strip()
    password =  body.get('password') or ''
    name     = (body.get('name')     or '').strip()
    dept     = (body.get('dept')     or '').strip()
    role     =  body.get('role')     or 'Viewer'

    if not username or not password or not name:
        return jsonify({'success': False, 'error': 'กรุณากรอกข้อมูลที่จำเป็น'})
    if username == 'admin' or User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Username นี้ถูกใช้แล้ว'})

    u = User(
        id=           'u' + str(int(datetime.now(TZ_BANGKOK).timestamp() * 1000)),
        username=     username,
        password_hash=generate_password_hash(password),
        name=name, dept=dept, role=role,
        status=       'pending',
        created_at=   now_bangkok(),
    )
    db.session.add(u)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    # ลบ token ถ้ามี
    token = _get_token_from_request()
    if token:
        if token in _admin_tokens:
            _admin_tokens.discard(token)
        else:
            user = User.query.filter_by(token=token).first()
            if user:
                user.token = None
                db.session.commit()
    session.clear()
    return jsonify({'success': True})

# ─── User Routes (Admin only) ─────────────────────────────────────────────────

@app.route('/api/users', methods=['GET'])
def users_list():
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify([u.to_dict() for u in User.query.order_by(User.created_at).all()])

@app.route('/api/users', methods=['POST'])
def users_create():
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    body     = request.get_json() or {}
    username = (body.get('username') or '').strip()
    password =  body.get('password') or ''
    name     = (body.get('name')     or '').strip()
    dept     = (body.get('dept')     or '').strip()
    role     =  body.get('role')     or 'Viewer'
    status   =  body.get('status')   or 'pending'

    if not username or not password or not name:
        return jsonify({'success': False, 'error': 'กรุณากรอกข้อมูลที่จำเป็น'})
    if username == 'admin' or User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Username นี้ถูกใช้แล้ว'})

    u = User(
        id=           'u' + str(int(datetime.now(TZ_BANGKOK).timestamp() * 1000)),
        username=     username,
        password_hash=generate_password_hash(password),
        name=name, dept=dept, role=role, status=status,
        created_at=   now_bangkok(),
    )
    db.session.add(u)
    db.session.commit()
    return jsonify({'success': True, 'user': u.to_dict()})

@app.route('/api/users/<uid>', methods=['PUT'])
def users_update(uid):
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    u = User.query.get(uid)
    if not u:
        return jsonify({'error': 'Not found'}), 404
    body = request.get_json() or {}
    if 'status' in body:
        u.status = body['status']
    if 'role' in body:
        u.role = body['role']
    db.session.commit()
    return jsonify({'success': True, 'user': u.to_dict()})

@app.route('/api/users/<uid>/password', methods=['PUT'])
def users_reset_password(uid):
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    u = User.query.get(uid)
    if not u:
        return jsonify({'error': 'Not found'}), 404
    body     = request.get_json() or {}
    password =  body.get('password') or ''
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password ต้องมีอย่างน้อย 6 ตัวอักษร'})
    u.password_hash = generate_password_hash(password)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/users/<uid>', methods=['DELETE'])
def users_delete(uid):
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    u = User.query.get(uid)
    if not u:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(u)
    db.session.commit()
    return jsonify({'success': True})

# ─── Data Routes ──────────────────────────────────────────────────────────────

@app.route('/api/data', methods=['GET'])
def data_get():
    if not _is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    projects = [p.to_dict() for p in Project.query.all()]
    ideas    = [i.to_dict() for i in Idea.query.all()]
    return jsonify({'projects': projects, 'ideas': ideas})

@app.route('/api/data', methods=['PUT'])
def data_save():
    if not _is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    if _get_role() == 'Viewer':
        return jsonify({'error': 'Viewers cannot modify data'}), 403

    body     = request.get_json() or {}
    projects =  body.get('projects', [])
    ideas    =  body.get('ideas',    [])

    db.session.query(Project).delete()
    for p in projects:
        pid = p.get('id')
        if pid:
            db.session.add(Project(id=pid, data=json.dumps(p, ensure_ascii=False)))

    db.session.query(Idea).delete()
    for idea in ideas:
        iid = idea.get('id')
        if iid:
            db.session.add(Idea(id=iid, data=json.dumps(idea, ensure_ascii=False)))

    db.session.commit()
    return jsonify({'success': True})

# ─── Admin: Clear all users (reset) ──────────────────────────────────────────

@app.route('/api/users/clear-all', methods=['DELETE'])
def users_clear_all():
    """ลบ users ทั้งหมด (admin only) — สำหรับ reset database"""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    count = User.query.count()
    User.query.delete()
    db.session.commit()
    return jsonify({'success': True, 'deleted': count})


# ─── Reset DB (admin only) ────────────────────────────────────────────────────

@app.route('/api/admin/reset-db', methods=['POST'])
def reset_db():
    """Drop and recreate all tables — admin only"""
    body = request.get_json() or {}
    if body.get('secret') != 'reset-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    db.drop_all()
    db.create_all()
    return jsonify({'success': True, 'message': 'Database reset complete'})


# ─── Public Data (VIP view — no login required) ───────────────────────────────

@app.route('/api/data/public', methods=['GET'])
def data_public():
    """Public read-only endpoint for VIP dashboard — no auth required"""
    projects = [p.to_dict() for p in Project.query.all()]
    ideas    = [i.to_dict() for i in Idea.query.all()]
    return jsonify({'projects': projects, 'ideas': ideas})

# ─── Serve Frontend ───────────────────────────────────────────────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# ─── Init DB ──────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
