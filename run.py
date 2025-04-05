#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSearch Framework 启动脚本
"""

import os
import sys

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

def main():
    """主函数，启动Web界面"""
    if not check_dependencies() or not check_env_file():
        sys.exit(1)
    
    try:
        from app import demo
        print("正在启动DeepSearch Framework Web界面...")
        demo.launch(server_name="0.0.0.0", server_port=7860)
    except Exception as e:
        print(f"启动Web界面时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 