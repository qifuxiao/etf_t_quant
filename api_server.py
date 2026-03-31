#!/usr/bin/env python3
"""
API 服务启动脚本

使用方法:
    python api_server.py

或指定端口:
    python api_server.py --port 9000

说明:
    - 启动前需确保 QMT 客户端已登录
    - API 服务默认监听 0.0.0.0:8080
    - 文档地址: http://localhost:8080/docs
"""

import sys
import os
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from src.api import app


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ETF T Quant API Server")
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080,
        help="API 服务端口 (默认: 8080)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="API 服务地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载 (开发模式)"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("ETF T Quant API 服务启动")
    print(f"监听地址: {args.host}:{args.port}")
    print(f"文档地址: http://{args.host}:{args.port}/docs")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()