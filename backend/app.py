from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os, json
from datetime import datetime

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
     allow_headers=['Content-Type','Authorization'],
     methods=['GET','POST','PUT','DELETE','OPTIONS'])

app.secret_key = 'portfolio-secret-2026-change-in-production'
# ✅ สำคัญ: รองรับ cross-origin session บน Render (HTTPS)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 ชั่วโมง

# รองรับทั้ง SQLite (local/Render free) และ PostgreSQL (Render paid)
if os.environ.get("DATABASE_URL"):
    db_url = os.environ.get("DATABASE_URL")
    # Render ใช้ postgres:// แต่ SQLAlchemy ต้องการ postgresql://
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
    id          = db.Column(db.String(50),  primary_key=True)
    username    = db.Column(db.String(80),  unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name        = db.Column(db.String(200))
    dept        = db.Column(db.String(200))
    role        = db.Column(db.String(50),  default='Viewer')
    status      = db.Column(db.String(50),  default='pending')
    created_at  = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id':        self.id,
            'username':  self.username,
            'name':      self.name or '',
            'dept':      self.dept or '',
            'role':      self.role,
            'status':    self.status,
            'createdAt': self.created_at or datetime.now().isoformat(),
        }


class Project(db.Model):
    __tablename__ = 'projects'
    id   = db.Column(db.String(50),  primary_key=True)
    data = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return json.loads(self.data)


class Idea(db.Model):
    __tablename__ = 'ideas'
    id   = db.Column(db.String(50),  primary_key=True)
    data = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return json.loads(self.data)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _current_user():
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


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    body     = request.get_json() or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''

    # Built-in admin — hardcoded (ไม่เก็บใน DB)
    if username == 'admin' and password == 'admin2026':
        session.permanent = True
        session['uid'] = '__admin__'
        return jsonify({'success': True, 'user': {
            'id': '__admin__', 'username': 'admin', 'name': 'System Admin',
            'dept': 'Administration', 'role': 'Admin', 'status': 'approved',
            'createdAt': datetime.now().isoformat(),
        }})

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'error': 'Username หรือ Password ไม่ถูกต้อง'})

    if user.status == 'rejected':
        return jsonify({'success': False, 'error': 'บัญชีของคุณถูกปฏิเสธ กรุณาติดต่อ Admin'})

    session.permanent = True
    session['uid'] = user.id
    return jsonify({'success': True, 'pending': user.status == 'pending', 'user': user.to_dict()})


@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    body     = request.get_json() or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    name     = (body.get('name') or '').strip()
    dept     = (body.get('dept') or '').strip()
    role     = body.get('role') or 'Viewer'

    if not username or not password or not name:
        return jsonify({'success': False, 'error': 'กรุณากรอกข้อมูลที่จำเป็น'})

    if username == 'admin' or User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Username นี้ถูกใช้แล้ว'})

    u = User(
        id='u' + str(int(datetime.now().timestamp() * 1000)),
        username=username,
        password_hash=generate_password_hash(password),
        name=name, dept=dept, role=role,
        status='pending',
        created_at=datetime.now().isoformat(),
    )
    db.session.add(u)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
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
    password = body.get('password') or ''
    name     = (body.get('name') or '').strip()
    dept     = (body.get('dept') or '').strip()
    role     = body.get('role') or 'Viewer'
    status   = body.get('status') or 'pending'

    if not username or not password or not name:
        return jsonify({'success': False, 'error': 'กรุณากรอกข้อมูลที่จำเป็น'})
    if username == 'admin' or User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Username นี้ถูกใช้แล้ว'})

    u = User(
        id='u' + str(int(datetime.now().timestamp() * 1000)),
        username=username,
        password_hash=generate_password_hash(password),
        name=name, dept=dept, role=role, status=status,
        created_at=datetime.now().isoformat(),
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
    password = body.get('password') or ''
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
    projects = body.get('projects', [])
    ideas    = body.get('ideas', [])

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


# ─── Serve Frontend (GitHub Pages จะไม่ใช้ส่วนนี้) ────────────────────────────

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
