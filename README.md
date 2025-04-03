# Deep Search Framework

一个基于 `Tavily API` 和网页抓取的信息搜索和分析框架。

## 环境设置

1. 安装依赖:

```bash
pip install -r requirements.txt
```

2. 配置环境变量:

复制`.env.example`文件（如果存在）或创建一个新的`.env`文件，并设置必要的API密钥:

```
# Tavily API密钥
TAVILY_API_KEY=your_tavily_api_key_here
```

您可以从[Tavily官网](https://tavily.com/)获取API密钥。

## 使用方法

运行主程序:

```bash
python main.py
```

## 功能

- 使用Tavily进行网络搜索
- 网页内容抓取和解析
- 基于上下文的内容过滤
- 自动链接提取

## 注意事项

- `.env`文件包含敏感信息，已添加到`.gitignore`中，不会被提交到代码仓库
- 确保您有有效的Tavily API密钥 