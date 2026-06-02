import os
import sys

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Excel 文件路径（先在 data 目录找，再回退到 Desktop）
EXCEL_FILENAME = '苏州库存管理-6.1.xlsx'
DATA_EXCEL = os.path.join(DATA_DIR, EXCEL_FILENAME)
DESKTOP_EXCEL = os.path.join(os.path.dirname(BASE_DIR), EXCEL_FILENAME)
EXCEL_PATH = DATA_EXCEL if os.path.exists(DATA_EXCEL) else DESKTOP_EXCEL

# 缓存 JSON
JSON_CACHE_PATH = os.path.join(DATA_DIR, 'inventory_data.json')

# 录入日志
ENTRY_LOG_PATH = os.path.join(DATA_DIR, 'entry_log.json')

# 用户自定义预警值
WARNING_OVERRIDE_PATH = os.path.join(DATA_DIR, 'warning_override.json')

# 用户新增物料
EXTRA_MATERIALS_PATH = os.path.join(DATA_DIR, 'extra_materials.json')
