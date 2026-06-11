"""
童话镇多智能体系统 - 启动脚本
"""
import os
import sys

# 确保backend目录在路径中
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 导入并运行Flask应用
from app import app

if __name__ == '__main__':
    print("=" * 50)
    print("童话镇多智能体系统")
    print("=" * 50)
    print("\n启动Flask服务器...")
    print("后端地址: http://localhost:5000")
    print("前端地址: http://localhost:8080 (需要另外启动)")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 50)

    # 启动Flask
    app.run(host='0.0.0.0', port=5000, debug=True)