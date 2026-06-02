"""
登录验证模块 — 简单的用户名密码认证
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import hashlib
import json
import os

# 配置：默认账号密码（部署后请修改！）
# 密码用 SHA256 加密存储
DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _load_users():
    """从文件加载用户配置，不存在则用默认"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _verify_password(username, password):
    """验证用户名密码"""
    users = _load_users()
    if username in users:
        return users[username]['password_hash'] == hashlib.sha256(password.encode()).hexdigest()
    # 默认账号
    if username == DEFAULT_USERNAME:
        return hashlib.sha256(password.encode()).hexdigest() == DEFAULT_PASSWORD_HASH
    return False


@auth_bp.route('/login', methods=['POST'])
def login():
    """登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'ok': False, 'msg': '请输入用户名和密码'}), 400

    if _verify_password(username, password):
        session['user'] = username
        session.permanent = True
        return jsonify({'ok': True, 'msg': '登录成功'})

    return jsonify({'ok': False, 'msg': '用户名或密码错误'}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """退出登录"""
    session.pop('user', None)
    return jsonify({'ok': True, 'msg': '已退出'})


@auth_bp.route('/check', methods=['GET'])
def check():
    """检查登录状态"""
    if 'user' in session:
        return jsonify({'ok': True, 'user': session['user']})
    return jsonify({'ok': False}), 401


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'ok': False, 'msg': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated
