from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os, json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(__name__, static_folder=os.path.join(ROOT_DIR, 'frontend'))

# ✅ สำคัญมาก
CORS(app, supports_credentials=True)

app.secret_key = 'portfolio-secret-2026-change-in-production'

# ✅ รองรับ Render (Production)
if os.environ.get("DATABASE_URL"):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(ROOT_DIR, 'portfolio.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ─── Models ─────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(200))
    dept = db.Column(db.String(200))
    role = db.Column(db.String(50), default='Viewer')
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name or '',
            'dept': self.dept or '',
            'role': self.role,
            'status': self.status,
            'createdAt': self.created_at or datetime.now().isoformat(),
        }


# ─── Auth ─────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def login():
    body = request.get_json()
    username = body.get('username')
    password = body.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'error': 'Login failed'})

    session['uid'] = user.id
    return jsonify({'success': True, 'user': user.to_dict()})


@app.route('/api/auth/register', methods=['POST'])
def register():
    body = request.get_json()

    user = User(
        id=str(int(datetime.now().timestamp())),
        username=body['username'],
        password_hash=generate_password_hash(body['password']),
        name=body.get('name', ''),
        dept=body.get('dept', ''),
        role='Viewer',
        status='pending'
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True})


@app.route("/")
def home():
    return "API is running"


# ─── Init DB ───────────────────────────────────────

with app.app_context():
    db.create_all()


# ✅ สำคัญสำหรับ Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
