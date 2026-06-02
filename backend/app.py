"""
Flask 应用工厂
"""

import os
import json
from flask import Flask, session, jsonify, send_from_directory, redirect
from flask_cors import CORS


def create_app():
    app = Flask(__name__, static_folder=None)

    # Session 密钥（生产环境请换一个随机值）
    app.secret_key = os.environ.get('SECRET_KEY', 'sz-warehouse-2024-secret-key-change-me')
    app.config['SESSION_COOKIE_NAME'] = 'sz_warehouse_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    CORS(app, supports_credentials=True)

    # 从配置加载路径
    from backend.config import JSON_CACHE_PATH, ENTRY_LOG_PATH, EXCEL_PATH, DATA_DIR, WARNING_OVERRIDE_PATH, EXTRA_MATERIALS_PATH
    app.config['JSON_CACHE_PATH'] = JSON_CACHE_PATH
    app.config['ENTRY_LOG_PATH'] = ENTRY_LOG_PATH
    app.config['EXCEL_PATH'] = EXCEL_PATH
    app.config['DATA_DIR'] = DATA_DIR
    app.config['WARNING_OVERRIDE_PATH'] = WARNING_OVERRIDE_PATH
    app.config['EXTRA_MATERIALS_PATH'] = EXTRA_MATERIALS_PATH

    # 确保缓存存在
    _ensure_cache(app)

    # 注册蓝图
    from backend.auth import auth_bp, login_required
    from backend.routes.materials import materials_bp
    from backend.routes.inventory import inventory_bp
    from backend.routes.daily import daily_bp
    from backend.routes.entry import entry_bp
    from backend.routes.stats import stats_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(daily_bp)
    app.register_blueprint(entry_bp)
    app.register_blueprint(stats_bp)

    # 所有 /api/ 路由都需要登录（除了 auth 相关）
    _public_api_prefixes = ('/api/auth/',)

    @app.before_request
    def check_auth():
        from flask import request
        if request.path.startswith('/api/'):
            if not any(request.path.startswith(p) for p in _public_api_prefixes):
                if 'user' not in session:
                    return jsonify({'ok': False, 'msg': '请先登录'}), 401

    # 前端静态文件（login.html 不需要登录）
    _public_pages = ('/login.html',)

    @app.route('/')
    def index():
        if 'user' not in session:
            return redirect('/login.html')
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/<path:path>')
    def static_files(path):
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        # 登录页面和静态资源不需要登录验证
        if path in _public_pages or path.startswith('login.'):
            return send_from_directory(frontend_dir, path)
        # 其他页面需要登录
        if 'user' not in session:
            return redirect('/login.html')
        return send_from_directory(frontend_dir, path)

    return app


def _ensure_cache(app):
    """确保 JSON 缓存已生成"""
    from backend.services.excel_reader import ExcelReader
    from backend.services.json_cache import JsonCache

    cache = JsonCache(app.config['JSON_CACHE_PATH'])

    if not cache.exists():
        print('正在从 Excel 生成缓存...')
        reader = ExcelReader(app.config['EXCEL_PATH'])
        data = reader.parse_all()
        cache.save(data)
        print(f'缓存生成完成: {len(data.get("materials", {}))} 种物料')
    else:
        print('缓存已存在，直接加载')
