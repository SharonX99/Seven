"""
苏州仓库库存管理系统 — 启动入口
"""

import sys
import os

# 将项目根目录加到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app

app = create_app()

if __name__ == '__main__':
    print('=' * 50)
    print('  苏州仓库库存管理系统')
    print('  启动服务: http://localhost:5000')
    print('=' * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
