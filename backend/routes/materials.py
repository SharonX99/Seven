"""
物料 API — GET /api/materials, POST /api/material/new, POST /api/material/correct
"""

import os
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from backend.services.json_cache import JsonCache
from backend.services.entry_log import EntryLogService

materials_bp = Blueprint('materials', __name__)


def _load_extra_materials(app):
    """加载用户新增的物料"""
    path = app.config.get('EXTRA_MATERIALS_PATH', '')
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_extra_materials(app, extra):
    """保存用户新增的物料"""
    path = app.config.get('EXTRA_MATERIALS_PATH', '')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(extra, f, ensure_ascii=False, indent=2)


def get_all_materials(app):
    """合并 Excel 物料 + 用户新增物料"""
    cache = JsonCache(app.config['JSON_CACHE_PATH'])
    data = cache.load()
    materials = {}
    if data:
        materials.update(data.get('materials', {}))
    extra = _load_extra_materials(app)
    materials.update(extra)
    return materials


def _next_temp_id(app):
    """生成临时物料编码 TEMP-yyyyMMdd-xxx"""
    extra = _load_extra_materials(app)
    temp_count = sum(1 for k in extra if k.startswith('TEMP-'))
    today = datetime.now().strftime('%Y%m%d')
    return f'TEMP-{today}-{temp_count + 1:03d}'


@materials_bp.route('/api/materials', methods=['GET'])
def get_materials():
    materials = get_all_materials(current_app)

    query = request.args.get('q', '').strip().lower()
    if query:
        result = {}
        for code, mat in materials.items():
            if query in code.lower() or query in mat.get('product_code', '').lower():
                result[code] = mat
        return jsonify(result)
    else:
        return jsonify(materials)


@materials_bp.route('/api/materials/<code>', methods=['GET'])
def get_material(code):
    materials = get_all_materials(current_app)
    mat = materials.get(code)
    if mat:
        return jsonify(mat)
    return jsonify({'error': '未找到该物料'}), 404


@materials_bp.route('/api/material/new', methods=['POST'])
def add_material():
    """
    新增物料
    POST {"material_code": "xxx", "product_code": "xxx", "warning": 0}
    如果 material_code 为空则自动生成临时编码
    """
    body = request.get_json(silent=True) or {}
    mat_code = body.get('material_code', '').strip()
    prod_code = body.get('product_code', '').strip()
    warning = body.get('warning', 0)

    if not prod_code:
        return jsonify({'error': '产品代码不能为空'}), 400

    # 没填物料编码 → 自动生成临时编码
    if not mat_code:
        mat_code = _next_temp_id(current_app)

    # 检查是否已存在
    materials = get_all_materials(current_app)
    if mat_code in materials:
        return jsonify({'error': f'物料编码 {mat_code} 已存在'}), 400

    extra = _load_extra_materials(current_app)
    extra[mat_code] = {
        'material_code': mat_code,
        'product_code': prod_code,
        'warning': warning,
        'temp': mat_code.startswith('TEMP-'),  # 标记是否为临时编码
    }
    _save_extra_materials(current_app, extra)

    return jsonify({'success': True, 'material': extra[mat_code], 'temp': mat_code.startswith('TEMP-')}), 201


@materials_bp.route('/api/material/correct', methods=['POST'])
def correct_material():
    """
    补正物料编码：将临时编码替换为正式编码
    POST {"temp_code": "TEMP-xxx", "real_code": "1000088888", "product_code": "..."}
    同时更新 entry_log 中所有该物料编码的记录
    """
    body = request.get_json(silent=True) or {}
    temp_code = body.get('temp_code', '').strip()
    real_code = body.get('real_code', '').strip()
    prod_code = body.get('product_code', '').strip()

    if not temp_code:
        return jsonify({'error': '临时编码不能为空'}), 400
    if not real_code:
        return jsonify({'error': '正式物料编码不能为空'}), 400
    if not prod_code:
        return jsonify({'error': '产品代码不能为空'}), 400

    # 检查临时编码是否存在
    extra = _load_extra_materials(current_app)
    if temp_code not in extra:
        return jsonify({'error': f'未找到临时编码 {temp_code}'}), 404

    # 检查正式编码是否已被占用
    materials = get_all_materials(current_app)
    if real_code in materials:
        return jsonify({'error': f'物料编码 {real_code} 已存在，请勿重复创建'}), 400

    # 1. 更新 extra_materials：删除旧的临时编码，创建正式编码
    temp_data = extra.pop(temp_code)
    extra[real_code] = {
        'material_code': real_code,
        'product_code': prod_code,
        'warning': temp_data.get('warning', 0),
        'temp': False,
    }
    _save_extra_materials(current_app, extra)

    # 2. 更新 entry_log 中所有使用临时编码的记录 → 改为正式编码
    entry_service = EntryLogService(current_app.config['ENTRY_LOG_PATH'])
    entry_service.correct_material_code(temp_code, real_code, prod_code)

    return jsonify({
        'success': True,
        'old_code': temp_code,
        'new_code': real_code,
        'product_code': prod_code,
    })


@materials_bp.route('/api/material/pending', methods=['GET'])
def get_pending_materials():
    """获取所有待补正的物料（临时编码的）"""
    extra = _load_extra_materials(current_app)
    pending = {k: v for k, v in extra.items() if v.get('temp', False) or k.startswith('TEMP-')}
    return jsonify({
        'items': pending,
        'count': len(pending),
    })
