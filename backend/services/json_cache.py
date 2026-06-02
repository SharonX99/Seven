"""
JSON 缓存服务 — 将 Excel 数据缓存到 inventory_data.json
"""

import json
import os


class JsonCache:
    """缓存管理"""

    def __init__(self, cache_path):
        self.cache_path = cache_path

    def exists(self):
        """缓存文件是否存在"""
        return os.path.exists(self.cache_path) and os.path.getsize(self.cache_path) > 0

    def load(self):
        """加载缓存"""
        if not self.exists():
            return None
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def save(self, data):
        """保存缓存"""
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def refresh(self, excel_data):
        """从 Excel 数据刷新缓存"""
        self.save(excel_data)
        return excel_data
