import asyncio
import gradio as gr
import json
import re
from datetime import datetime
from typing import Dict, List, Any
from main import Agent, Prompt, BreakPrompt

def format_memory_blocks(blocks: Dict[str, str]) -> str:
    """格式化记忆块为HTML展示"""
    html = ""
    for block_id, content in blocks.items():
        html += f'<div class="memory-block"><div class="block-id">{block_id}</div><div class="block-content">{content}</div></div>'
    return html

def format_links(links: List[Dict[str, str]]) -> str:
    """格式化重要链接为HTML展示，包含超链接"""
    if not links:
        return "<p>暂无重要链接</p>"
    
    html = "<ul>"
    for link in links:
        html += f'<li><a href="{link["url"]}" target="_blank">{link["title"]}</a></li>'
    html += "</ul>"
    return html

def format_tool_records(tool_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """格式化工具调用记录，便于折叠显示"""
    formatted_records = []
    if not tool_records:
        return formatted_records
    
    for i, record in enumerate(tool_records):
        formatted_records.append({
            "index": i + 1,
            "tool": record["tool"],
            "input": record["input"],
            "output": record["output"]
        })
    
    return formatted_records

class GradioAgent:
    def __init__(self):
        self.agent = None
        self.is_running = False
        self.tools_used = []
        self.answer = None
        self.important_links = []
        self.status = "等待开始"
        self.task = ""
        
    async def process_task(self, task: str, progress=gr.Progress()) -> Dict:
        """处理任务并返回结果"""
        self.task = task
        self.tools_used = []
        self.status = "进行中"
        self.answer = None
        self.important_links = []
        
        prompt = Prompt("""
{% macro format_tool_results(tool_records) %}
{% for to in tool_records %}
来源 {{ loop.index }}️: {{ to.tool }}: {{ to.input }}
结果:
```
{{ to.output }}
```
{% endfor %}
{% endmacro %}

日期：`{{ current_date }}`。
你是一个信息分析和探索代理，通过系统调查构建解决方案。

## 调查周期
你以持续的调查周期运作：

1. 查看当前工作区（你的记忆块）
2. 分析新的工具结果（如果是第一轮，则分析初始任务）
3. 使用新的见解更新记忆并跟踪调查进度
4. 根据已识别的线索和信息差距决定下一步要调用的工具
5. 重复，直到任务完成

## 记忆结构
你的记忆在调查周期之间持续存在，并且由以下部分组成：
- **状态**：始终是第一行，指示任务是进行中还是已完成
- **记忆**：离散信息块的集合，每个块都有一个唯一的 ID


## 记忆块的使用
- 每个记忆块都有一个格式为 <abc-123>content</abc-123> 的唯一 ID
- 为不同的信息片段创建单独的块：
  * 发现的 URL（已探索和待处理）
  * 需要调查的信息差距
  * 已采取的行动（避免重复）
  * 有希望的未来探索线索
  * 关键事实和发现
  * 发现的矛盾或不一致之处
- 保持每个块专注于单个想法或信息
- 在记录来自工具结果的信息时，始终引用来源
- 使用 ID 来跟踪和管理你的知识（例如，删除过时的信息）
- 确保存储你存储的事实和发现的来源（URL）
- 重要的链接包含在多个<important link>标签中

## 线索管理
- 由于你每轮只能进行 3 次工具调用，因此请存储有希望的线索以供以后使用
- 为以后要抓取的 URL 创建专用记忆块
- 维护可在未来轮次中探索的潜在搜索查询的块
- 根据与任务的相关性对线索进行优先排序

## 可用工具
- **search**: 用于对新主题或概念进行广泛的信息收集
  * 示例: {"tool": "search", "input": "2023 年可再生能源统计数据"}
- **scrape**: 用于从发现的 URL 中提取特定详细信息
  * 示例: {"tool": "scrape", "input": "https://example.com/energy-report"}

## 工具使用指南
- **何时使用 search**: 对于新概念、填补知识空白或探索新方向
- **何时使用 scrape**: 对于发现的可能包含详细信息的 URL
- **每轮最多 3 次工具调用**
- **切勿重复完全相同的工具调用**
- **始终在记忆块中记录来自工具结果的有价值信息**

## 响应格式
你必须使用包含以下内容的有效 JSON 对象进行响应：

```json
{
  "status_update": "进行中 或 已完成",
  "memory_updates": [
    {"operation": "add", "content": "要调查的新见解或线索"},
    {"operation": "delete", "id": "abc-123"}
  ],
  "tool_calls": [
    {"tool": "search", "input": "specific search query"},
    {"tool": "scrape", "input": "https://discovered-url.com"}
  ],
  "answer": "已完成"时，你的最终、全面答案",
  "important_links": [
    {"url": "https://example.com", "title": "对于任务产生重要影响的URL和页面title"}
  ]
}
```

## 重要规则
- "add" 操作会创建一个新的记忆块
    你不需要指定 ID，系统会自动添加它。
- "delete" 操作需要要删除的块的特定 ID
- 切勿编造或捏造信息 - 仅使用来自你的记忆或工具结果的事实
- 切勿编造 URL - 仅使用通过工具结果发现的 URL
- 关键：任何未记录在你的记忆块中的信息都将在下一轮中丢失
  例如，如果你找到一个要抓取的潜在网页，你必须存储 URL 和你的意图
  示例: `{"operation": "add", "content": "找到相关 URL: https://... 要抓取 ..."}`
- 重要：确保删除不再需要的记忆块
- 仅当你已完全解决任务时，才将状态设置为"已完成"
- 仅当状态为"已完成"时才包含"answer" 字段
- 仅当有效采用的数据所在的页面url和title才能加入到important_links中

任务：
```
{{ task }}
```

当前工作区：
```
{{ workspace }}
```

工具结果：
{{ format_tool_results(tool_records) if tool_records else '... no previous tool results ...'}}

重要：按照上述格式生成有效的 JSON 响应。

仔细思考：
- 你需要保留哪些信息
- 下一步要调用哪些工具
- 如何使用专注的记忆块系统地构建你的答案

不要依赖你的内部知识（可能有偏见），目标是使用工具发现信息！
""")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.agent = Agent(task=task, prompt=prompt, current_date=current_date)
        
        max_rounds = 8
        try:
            for round_num in range(max_rounds):
                progress(round_num / max_rounds, f"执行第 {round_num + 1} 轮搜索...")
                await self.agent.run(loop=False)
                
                if self.agent.tool_records:
                    self.tools_used.extend(self.agent.tool_records)
                
                # 如果任务完成，跳出循环
                if self.agent.workspace.is_done():
                    self.status = "已完成"
                    self.answer = self.agent.workspace.state['answer']
                    self.important_links = self.agent.workspace.state['important_links']
                    break
            
            # 如果未完成，使用BreakPrompt生成总结
            if self.status != "已完成":
                progress(0.9, "生成总结...")
                brokeprompt = BreakPrompt()
                self.answer = await brokeprompt.run(self.agent.workspace.to_string())
                self.important_links = self.agent.workspace.state['important_links']
                self.status = "已总结"
        
        except Exception as e:
            self.status = "出错"
            self.answer = f"发生错误: {str(e)}"
        
        # 返回结果
        return {
            "status": self.status,
            "answer": self.answer if self.answer else "尚未生成答案",
            "important_links": self.important_links,
            "memory_blocks": self.agent.workspace.state["blocks"],
            "tool_records": format_tool_records(self.tools_used)
        }

# 初始化代理
gradio_agent = GradioAgent()

# 创建Gradio接口
with gr.Blocks(css="""
    .memory-block {
        background-color: #f5f5f5;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .block-id {
        color: #2962ff;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .block-content {
        margin-left: 10px;
    }
    .important-links {
        margin-top: 20px;
    }
    .important-links ul {
        padding-left: 20px;
    }
    .important-links a {
        color: #1976d2;
        text-decoration: none;
    }
    .important-links a:hover {
        text-decoration: underline;
    }
    .tool-accordion {
        margin-bottom: 10px;
    }
""") as demo:
    gr.Markdown("""
    # 深度搜索助手 - DeepSearch Framework
    
    通过输入您的查询，利用搜索和网页抓取工具获取与分析相关信息。
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            task_input = gr.Textbox(
                label="输入您的查询", 
                placeholder="例如：帮我制定一个计划，5月份到新加坡游玩4-5天...",
                lines=5
            )
            submit_btn = gr.Button("开始搜索", variant="primary")
        
        with gr.Column(scale=2):
            status_output = gr.Textbox(label="状态", value="等待开始")
    
    with gr.Tabs() as tabs:
        with gr.TabItem("搜索结果"):
            answer_output = gr.Markdown(label="分析结果")
            links_output = gr.HTML(label="重要链接")
        
        with gr.TabItem("记忆块"):
            memory_output = gr.HTML(label="记忆块")
        
        with gr.TabItem("工具调用"):
            tools_output = gr.Accordion(
                label="工具调用记录", 
                open=False
            )
    
    def format_tools_output(tool_records):
        """将工具记录格式化为accordion组件"""
        accordions = []
        for record in tool_records:
            label = f"[{record['index']}] {record['tool']}: {record['input']}"
            accordions.append(gr.Accordion(
                label=label,
                open=False,
                render=False
            ))
            with accordions[-1]:
                gr.Markdown(record['output'])
        return accordions
    
    async def process_query(task):
        results = await gradio_agent.process_task(task)
        
        # 格式化记忆块
        memory_html = format_memory_blocks(results["memory_blocks"])
        
        # 格式化链接
        links_html = format_links(results["important_links"])
        
        # 创建工具调用accordion
        tool_accordions = []
        for record in results["tool_records"]:
            tool_accordions.append(
                gr.Accordion(
                    label=f"[{record['index']}] {record['tool']}: {record['input']}",
                    open=False
                ),
            )
            with tool_accordions[-1]:
                gr.Markdown(record['output'])
        
        return [
            results["status"],
            results["answer"],
            links_html,
            memory_html,
            *tool_accordions
        ]
    
    submit_btn.click(
        fn=process_query,
        inputs=[task_input],
        outputs=[
            status_output,
            answer_output,
            links_output,
            memory_output,
            tools_output
        ]
    )

# 启动入口
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860) 