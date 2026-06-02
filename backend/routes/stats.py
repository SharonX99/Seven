"""
统计 API — GET /api/stats
"""

from flask import Blueprint, jsonify, current_app
from backend.services.json_cache import JsonCache

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/api/stats', methods=['GET'])
def get_stats():
    cache = JsonCache(current_app.config['JSON_CACHE_PATH'])
    data = cache.load()
    if not data:
        return jsonify({'error': '数据未加载'}), 500

    current_stock = data.get('current_stock', [])
    total = len(current_stock)
    low = sum(1 for i in current_stock if i.get('status', '').startswith('库存不足'))
    zero = sum(1 for i in current_stock if i.get('actual_stock', 0) <= 0)

    # 今日交易
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    transactions = data.get('transactions', [])
    today_txns = [t for t in transactions if t.get('date') == today]
    today_in = sum(t.get('quantity', 0) for t in today_txns if t.get('type') == '入库')
    today_out = sum(t.get('quantity', 0) for t in today_txns if t.get('type') == '出库')

    return jsonify({
        'total_materials': total,
        'low_stock': low,
        'zero_stock': zero,
        'today_in': today_in,
        'today_out': today_out,
        'today_transactions': len(today_txns),
        'last_updated': data.get('last_updated', ''),
    })
