import asyncio
import os
import gradio as gr
import json
import re
from datetime import datetime
from typing import Dict, List, Any
from main import Agent, Prompt, BreakPrompt, AGENT_PROMPT_TEMPLATE

def format_memory_blocks(blocks: Dict[str, str]) -> str:
    """格式化记忆块为HTML展示"""
    if not blocks:
        return "<p>暂无记忆块</p>"
    
    html = ""
    for block_id, content in blocks.items():
        html += f'''
        <div class="memory-block">
            <div class="block-id">{block_id}</div>
            <div class="block-content">{content}</div>
        </div>
        '''
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
        
    async def process_task(self, task: str, max_rounds: int = 8, progress=gr.Progress()) -> Dict:
        """处理任务并返回结果"""
        self.task = task
        self.tools_used = []
        self.status = "进行中"
        self.answer = None
        self.important_links = []
        
        prompt = Prompt(AGENT_PROMPT_TEMPLATE)
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.agent = Agent(task=task, prompt=prompt, current_date=current_date)
        
        # 使用传入的max_rounds作为最大轮数
        try:
            # 遍历执行每一轮
            for round_num in range(max_rounds):
                progress((round_num) / max_rounds, f"执行第 {round_num + 1} 轮搜索...")
                
                # 执行一轮处理
                await self.agent.run(loop=False)
                
                # 记录工具调用
                if self.agent.tool_records:
                    # 重要：深拷贝tool_records，避免引用同一个对象
                    for record in self.agent.tool_records:
                        # 使用字典复制而不是直接引用
                        self.tools_used.append({
                            "tool": record["tool"],
                            "input": record["input"],
                            "output": record["output"]
                        })
                    
                    print(f"第 {round_num + 1} 轮工具调用: {len(self.agent.tool_records)} 个")
                
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
            
            # 打印工具调用总数
            print(f"工具调用总数: {len(self.tools_used)}")
        
        except Exception as e:
            self.status = "出错"
            self.answer = f"发生错误: {str(e)}"
            print(f"执行过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        
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
    /* 记忆块样式 */
    .memory-block {
        background-color: var(--block-background-fill);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow: auto;
    }
    .block-id {
        color: var(--primary-500);
        font-weight: bold;
        margin-bottom: 5px;
        font-size: 16px;
    }
    .block-content {
        margin-left: 10px;
        white-space: pre-wrap;
        word-break: break-word;
    }
    
    /* 重要链接样式 */
    .important-links {
        margin-top: 20px;
    }
    .important-links ul {
        padding-left: 20px;
    }
    .important-links a {
        color: var(--link-text-color);
        text-decoration: none;
    }
    .important-links a:hover {
        text-decoration: underline;
    }
    
    /* 工具调用记录样式 */
    .tool-record {
        margin-bottom: 15px;
    }
    .tool-output {
        margin-top: 8px;
        padding: 10px;
        background-color: var(--background-fill-secondary);
        border-radius: 4px;
        max-height: 300px;
        overflow: auto;
    }
    .tool-output pre {
        white-space: pre-wrap;
        word-break: break-word;
        margin: 0;
        color: var(--body-text-color);
    }
    details {
        padding: 8px;
        background-color: var(--background-fill-primary);
        border-radius: 4px;
    }
    details summary {
        cursor: pointer;
        padding: 4px;
        color: var(--body-text-color);
    }
    
    /* 自定义一些变量，确保在没有暗色主题的情况下也能正常显示 */
    :root {
        --block-background-fill: #f5f5f5;
        --link-text-color: #1976d2;
    }
    
    /* 针对暗色主题的覆盖样式 */
    .dark .memory-block {
        background-color: #333;
    }
    .dark .tool-output {
        background-color: #333;
    }
    .dark details {
        background-color: #2a2a2a;
    }
    .dark .important-links a {
        color: #61afef;
    }
""", title="DeepSearch Framework - 智能信息搜索分析") as demo:
    gr.Markdown("""
    # 深度搜索助手 - DeepSearch Framework
    
    通过输入您的查询，利用搜索和网页抓取工具获取与分析相关信息。
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            task_input = gr.Textbox(
                label="输入您的查询", 
                placeholder="例如：帮我制定一个计划，5月份到新加坡游玩4-5天...",
                lines=3
            )
            
            with gr.Row():
                # 只保留开始搜索按钮
                submit_btn = gr.Button("开始搜索", variant="primary")
        
        with gr.Column(scale=2):
            status_output = gr.Textbox(label="状态", value="等待开始")
            # 将轮数滑块移到右侧状态下方
            max_rounds_slider = gr.Slider(
                minimum=1,
                maximum=12,
                value=10,
                step=1,
                label="最大任务轮数",
                info="设置任务执行的最大轮数（1-12轮）"
            )
    
    with gr.Tabs() as tabs:
        with gr.TabItem("搜索结果"):
            answer_output = gr.Markdown(label="分析结果")
            links_output = gr.HTML(label="重要链接")
        
        with gr.TabItem("记忆块"):
            memory_output = gr.HTML(label="记忆块", value="<p>暂无记忆块</p>")
        
        with gr.TabItem("工具调用"):
            tools_container = gr.Accordion(label="工具调用记录容器", open=True)
            with tools_container:
                tools_output = gr.HTML("暂无工具调用记录")
    
    async def process_query(task, max_rounds):
        results = await gradio_agent.process_task(task, int(max_rounds))
        
        # 格式化记忆块
        memory_html = ""
        if results["memory_blocks"]:
            for block_id, content in results["memory_blocks"].items():
                # 确保HTML标签被转义
                safe_content = content.replace("<", "&lt;").replace(">", "&gt;")
                memory_html += f'''
                <div class="memory-block">
                    <div class="block-id">{block_id}</div>
                    <div class="block-content">{safe_content}</div>
                </div>
                '''
        else:
            memory_html = "<p>暂无记忆块</p>"
        
        # 格式化链接
        links_html = format_links(results["important_links"])
        
        # 格式化工具调用记录为HTML
        tools_html = ""
        for record in results["tool_records"]:
            tools_html += f"""
            <div class="tool-record">
                <details>
                    <summary><strong>[{record['index']}] {record['tool']}: {record['input']}</strong></summary>
                    <div class="tool-output">
                        <pre>{record['output']}</pre>
                    </div>
                </details>
            </div>
            """
        
        if not tools_html:
            tools_html = "<p>暂无工具调用记录</p>"
        
        return [
            results["status"],
            results["answer"],
            links_html,
            memory_html,
            tools_html
        ]
    
    submit_btn.click(
        fn=process_query,
        inputs=[task_input, max_rounds_slider],
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
    demo.launch(server_name="0.0.0.0", server_port=7860, favicon_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon.ico")) 