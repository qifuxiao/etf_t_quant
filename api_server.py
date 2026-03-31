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
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from src.api import app


def setup_logging(log_dir: Path):
    """配置日志系统"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "api_server.log"
    error_file = log_dir / "api_error.log"
    
    # 配置 uvicorn 日志
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": str(log_file),
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(error_file),
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file", "error_file"]
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            }
        }
    }
    
    return log_config


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
    
    # 日志目录
    project_dir = Path(__file__).parent
    log_dir = project_dir / "logs"
    
    # 配置日志
    log_config = setup_logging(log_dir)
    
    print("=" * 50)
    print("ETF T Quant API 服务启动")
    print(f"监听地址: {args.host}:{args.port}")
    print(f"文档地址: http://{args.host}:{args.port}/docs")
    print(f"日志文件: {log_dir / 'api_server.log'}")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=log_config
    )


if __name__ == "__main__":
    main()