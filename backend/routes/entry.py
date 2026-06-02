"""
录入 API — POST/DELETE /api/entry, POST /api/refresh
"""

import os
import json
from flask import Blueprint, jsonify, request, current_app
from backend.services.entry_log import EntryLogService
from backend.services.json_cache import JsonCache
from backend.services.excel_reader import ExcelReader
from backend.config import EXCEL_PATH
from backend.routes.materials import get_all_materials, _load_extra_materials, _save_extra_materials

entry_bp = Blueprint('entry', __name__)


@entry_bp.route('/api/entry', methods=['POST'])
def add_entry():
    log_service = EntryLogService(current_app.config['ENTRY_LOG_PATH'])

    body = request.get_json(silent=True) or {}
    mat_code = body.get('material_code', '').strip()
    prod_code_from_body = body.get('product_code', '').strip()
    entry_type = body.get('type', '入库')
    quantity = body.get('quantity', 0)
    date = body.get('date', '')

    if not quantity or quantity < 1:
        return jsonify({'error': '数量必须大于0'}), 400
    if entry_type not in ('入库', '出库', '不良'):
        return jsonify({'error': '类型必须是 入库、出库 或 不良'}), 400

    # 如果只填了产品代码没填物料编码 → 自动生成临时编码
    materials = get_all_materials(current_app)

    if not mat_code:
        # 只有产品代码，自动分配临时编码
        from backend.routes.materials import _next_temp_id
        mat_code = _next_temp_id(current_app)
        prod_code = prod_code_from_body
        # 创建临时物料
        extra = _load_extra_materials(current_app)
        extra[mat_code] = {
            'material_code': mat_code,
            'product_code': prod_code,
            'warning': 0,
            'temp': True,
        }
        _save_extra_materials(current_app, extra)
        is_new = True
    else:
        # 有物料编码，查找或创建
        mat = materials.get(mat_code)
        if mat:
            prod_code = mat.get('product_code', '')
            is_new = False
        else:
            prod_code = prod_code_from_body
            extra = _load_extra_materials(current_app)
            extra[mat_code] = {
                'material_code': mat_code,
                'product_code': prod_code,
                'warning': 0,
                'temp': False,
            }
            _save_extra_materials(current_app, extra)
            is_new = True

    entry = log_service.add_entry(mat_code, prod_code, entry_type, quantity, date or None)

    return jsonify({
        'success': True,
        'entry': entry,
        'is_new': is_new,
        'temp': mat_code.startswith('TEMP-'),
    }), 201


@entry_bp.route('/api/entry/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    log_service = EntryLogService(current_app.config['ENTRY_LOG_PATH'])
    removed = log_service.delete_entry(entry_id)
    if removed:
        return jsonify({'success': True, 'entry': removed})
    return jsonify({'error': '未找到该记录'}), 404


@entry_bp.route('/api/entry/clear', methods=['POST'])
def clear_date_entries():
    log_service = EntryLogService(current_app.config['ENTRY_LOG_PATH'])
    body = request.get_json(silent=True) or {}
    date = body.get('date', '')
    if date:
        log_service.clear_date(date)
    return jsonify({'success': True})


@entry_bp.route('/api/entries', methods=['GET'])
def get_entries():
    log_service = EntryLogService(current_app.config['ENTRY_LOG_PATH'])
    date = request.args.get('date', '')
    entries = log_service.get_entries(date or None)
    return jsonify({'entries': entries, 'total': len(entries)})


@entry_bp.route('/api/refresh', methods=['POST'])
def refresh_excel():
    """
    同步 entry_log → Excel
    将未同步的 entry 写入 Excel，然后标记为已同步
    """
    log_service = EntryLogService(current_app.config['ENTRY_LOG_PATH'])
    unsynced = log_service.get_unsynced_entries()

    if not unsynced:
        return jsonify({'success': True, 'synced': 0, 'message': '没有需要同步的记录'})

    from backend.services.excel_writer import ExcelWriter
    writer = ExcelWriter(EXCEL_PATH)

    synced_ids = []
    errors = []
    for entry in unsynced:
        try:
            result = writer.write_entry(entry)
            if result.get('success'):
                synced_ids.append(entry['id'])
            else:
                errors.append({'id': entry['id'], 'error': result.get('error', '写入失败')})
        except Exception as e:
            errors.append({'id': entry['id'], 'error': str(e)})

    # 标记已同步
    if synced_ids:
        log_service.mark_synced(synced_ids)

    # 刷新 JSON 缓存
    reader = ExcelReader(EXCEL_PATH)
    fresh_data = reader.parse_all()
    cache = JsonCache(current_app.config['JSON_CACHE_PATH'])
    cache.save(fresh_data)

    return jsonify({
        'success': True,
        'synced': len(synced_ids),
        'errors': len(errors),
        'error_details': errors,
        'message': f'成功同步 {len(synced_ids)} 条记录到 Excel',
    })
