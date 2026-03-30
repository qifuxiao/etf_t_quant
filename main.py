"""
ETF T策略量化交易系统
主入口文件

运行方式：
    python main.py

说明：
    - 需要先启动QMT客户端并登录
    - 配置文件: config.yml
    - 日志目录: logs/
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main_controller import MainController
from src.config import Config
from loguru import logger


def main():
    """主函数"""
    # 加载配置
    config = Config()
    
    # 创建主控器
    controller = MainController(config)
    
    # 启动策略系统
    try:
        logger.info("=" * 50)
        logger.info("ETF T策略量化交易系统启动")
        logger.info("=" * 50)
        
        controller.start()
        
        # 主循环
        controller.run()
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，系统即将停止...")
        controller.stop()
        
    except Exception as e:
        logger.exception(f"系统运行异常: {e}")
        controller.stop()
        raise
        
    finally:
        logger.info("系统已停止")


if __name__ == "__main__":
    main()
