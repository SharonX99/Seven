"""
录入日志管理 — 操作即时写入 entry_log.json
"""

import json
import os
from datetime import datetime


class EntryLogService:
    """录入日志服务，管理增删改"""

    def __init__(self, log_path):
        self.log_path = log_path
        self._ensure_file()

    def _ensure_file(self):
        """确保日志文件存在"""
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump({'entries': [], 'next_id': 1}, f, ensure_ascii=False, indent=2)

    def _read(self):
        """读取日志"""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {'entries': [], 'next_id': 1}

    def _write(self, data):
        """写入日志"""
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_entry(self, material_code, product_code, entry_type, quantity, date=None):
        """
        添加录入记录
        返回创建的 entry 字典
        """
        data = self._read()
        entry_id = data['next_id']
        data['next_id'] = entry_id + 1

        entry = {
            'id': entry_id,
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'material_code': material_code,
            'product_code': product_code,
            'type': entry_type,  # '入库' or '出库'
            'quantity': quantity,
            'synced': False,  # 是否已同步到 Excel
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        data['entries'].append(entry)
        self._write(data)
        return entry

    def delete_entry(self, entry_id):
        """删除录入记录"""
        data = self._read()
        for i, e in enumerate(data['entries']):
            if e['id'] == entry_id:
                removed = data['entries'].pop(i)
                self._write(data)
                return removed
        return None

    def get_entries(self, date=None):
        """获取录入记录，可筛选日期"""
        data = self._read()
        entries = data['entries']
        if date:
            entries = [e for e in entries if e['date'] == date]
        return sorted(entries, key=lambda x: x['id'], reverse=True)

    def get_unsynced_entries(self):
        """获取未同步的记录"""
        data = self._read()
        return [e for e in data['entries'] if not e.get('synced')]

    def mark_synced(self, entry_ids):
        """标记记录为已同步"""
        data = self._read()
        id_set = set(entry_ids)
        for e in data['entries']:
            if e['id'] in id_set:
                e['synced'] = True
        self._write(data)

    def clear_date(self, date):
        """清空某日所有录入"""
        data = self._read()
        data['entries'] = [e for e in data['entries'] if e['date'] != date]
        self._write(data)

    def correct_material_code(self, old_code, new_code, new_prod_code):
        """
        补正物料编码：将 entry_log 中所有 old_code 替换为 new_code
        同时更新 product_code
        """
        data = self._read()
        updated = 0
        for e in data['entries']:
            if e['material_code'] == old_code:
                e['material_code'] = new_code
                e['product_code'] = new_prod_code
                updated += 1
        if updated:
            self._write(data)
        return updated
