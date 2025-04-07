#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSearch Framework 启动脚本
"""

import os
import sys
import argparse

def check_dependencies():
    """检查依赖项是否已安装"""
    try:
        import gradio
        import jinja2
        import aiohttp
        import tavily
        import bs4
        import dotenv
        return True
    except ImportError as e:
        print(f"缺少依赖项: {e}")
        print("请先运行: pip install -r requirements.txt")
        return False

def check_env_file():
    """检查.env文件是否存在并包含必要的配置"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("未找到.env文件，请根据.env.example创建")
            print("\n可以参考以下命令:")
            print("cp .env.example .env")
            print("然后编辑.env文件，填入您的API密钥")
        else:
            print("未找到.env文件，也未找到.env.example文件")
            print("请确保项目包含环境配置文件")
        return False
    
    # 读取.env文件检查是否包含必要的配置
    required_keys = ["OPENROUTER_API_KEY", "TAVILY_API_KEY"]
    missing_keys = []
    
    with open(".env", "r") as f:
        content = f.read()
        for key in required_keys:
            if key not in content:
                missing_keys.append(key)
    
    if missing_keys:
        print(f"以下必要的环境变量在.env文件中缺失: {', '.join(missing_keys)}")
        return False
    
    return True

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="DeepSearch Framework 启动程序")
    parser.add_argument("--host", type=str, default="0.0.0.0", 
                        help="监听的IP地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=7860, 
                        help="监听的端口号 (默认: 7860)")
    return parser.parse_args()

def main():
    """主函数，启动Web界面"""
    # 解析命令行参数
    args = parse_args()
    host = args.host
    port = args.port
    
    if not check_dependencies() or not check_env_file():
        sys.exit(1)
    
    try:
        from app import demo
        print("正在启动DeepSearch Framework Web界面...")
        print(f"监听地址: {host}:{port}")
        print(f"浏览器访问地址: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        demo.launch(server_name='0.0.0.0', server_port=port, favicon_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon.ico"))
    except Exception as e:
        print(f"启动Web界面时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 