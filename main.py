import asyncio
import random
import re
import string
import sys
import traceback
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from break_prompt import BreakPrompt
from prompt import Prompt
from tools import ScrapTool, SearchTool, extract_largest_json


class Workspace:
    def __init__(self):
        self.state = {"status": "进行中", "blocks": {}, "answer": None}

    def to_string(self):
        """
        Converts the workspace state to a formatted string representation.

        Returns:
            str: A string representation of the workspace state
        """
        result = f"Status: {self.state['status']}\n"
        result += "Memory: \n"

        if not self.state["blocks"]:
            result += "... no memory blocks ...\n"
        else:
            for block_id, content in self.state["blocks"].items():
                result += f"<{block_id}>{content}</{block_id}>\n"

        return result

    def _generate_unique_block_id(self):
        """
        Generate a unique block ID in the format abc-123.

        Returns:
            str: A unique ID consisting of 3 lowercase letters, a hyphen, and 3 digits
        """
        while True:
            # Generate random ID in abc-123 format
            letters = "".join(random.choices(string.ascii_lowercase, k=3))
            digits = "".join(random.choices(string.digits, k=3))
            new_id = f"{letters}-{digits}"

            # Return ID if it's unique
            if new_id not in self.state["blocks"]:
                return new_id

    def update_blocks(
        self, status: str, blocks: List[Dict], answer: Optional[str] = None
    ):
        """
        Updates the workspace state with new status, blocks, and answer.

        Args:
            status (str): New status ("IN_PROGRESS" or "DONE")
            blocks (List[Dict]): List of block operations to apply
                Each dict should have:
                - "operation": "add" or "delete"
                - "content": content to add (for "add" operation)
                - "id": block id to delete (for "delete" operation)
            answer (Optional[str]): Final answer when status is "DONE"
        """
        # Update status
        self.state["status"] = status

        # Update blocks based on operations
        for block_op in blocks:
            operation = block_op.get("operation")

            if operation == "add":
                # Generate a unique block ID using helper function
                new_id = self._generate_unique_block_id()
                self.state["blocks"][new_id] = block_op.get("content", "")

            elif operation == "delete":
                block_id = block_op.get("id")
                if block_id in self.state["blocks"]:
                    del self.state["blocks"][block_id]

        # Update answer if provided
        if answer is not None:
            self.state["answer"] = answer

    def is_done(self):
        return self.state["status"] != "进行中"
    
class Agent:
    # Tools the agent can call
    tools = {"search": SearchTool(), "scrape": ScrapTool()}

    def __init__(
        self,
        task: str,
        prompt: Prompt,
        current_date: str = datetime.now().strftime("%Y-%m-%d"),
    ):
        self.task = task
        self.prompt = prompt
        self.current_date = current_date
        self.tool_records = None
        self.workspace = Workspace()
        self.round = 0

    async def run_tool(
        self, tool_id: str, tool_input: str, context: str | None = None
    ) -> str:
        try:
            assert tool_id in ["search", "scrape"], f"Illegal tool: {tool_id}"
            tool = self.tools[tool_id]
            result = await tool(tool_input, context)
            return result
        except Exception as e:
            print(f"Failed to run tool {e}")
            print(traceback.format_exc())
            return f"Tool execution failed: {e}"

    async def run(self, loop=True, max_rounds: int | None = None) -> Dict[str, Any]:
        while True:
            try:
                # Rate limiting - 1 round per 20 seconds
                await asyncio.sleep(20)

                response = await self.prompt.run(
                    {
                        "current_date": self.current_date,
                        "task": self.task,
                        "workspace": self.workspace.to_string(),
                        "tool_records": self.tool_records,
                    }
                )

                response = re.sub(
                    r"(?:<think>)?.*?</think>", "", response, flags=re.DOTALL
                )
                response_json = extract_largest_json(response)
                if not response_json:
                    print(f"无法从响应中提取JSON: {response[:200]}...")
                    await asyncio.sleep(10)
                    continue

                # 确保memory_updates字段存在
                if "memory_updates" not in response_json:
                    print("响应中缺少memory_updates字段")
                    response_json["memory_updates"] = []
                
                # 确保tool_calls字段存在
                if "tool_calls" not in response_json:
                    print("响应中缺少tool_calls字段")
                    response_json["tool_calls"] = []

                self.workspace.update_blocks(
                    response_json.get("status_update", "进行中"),
                    response_json.get("memory_updates", []),
                    response_json.get("answer", None),
                )

                tool_calls = response_json["tool_calls"]

                tasks = [
                    self.run_tool(call["tool"], call["input"], self.task)
                    for call in tool_calls
                ]

                tool_outputs = await asyncio.gather(*tasks)

                tool_records = [
                    {**call, "output": output}
                    for call, output in zip(tool_calls, tool_outputs)
                ]

                # Will be appended to the prompt in the next round
                self.tool_records = tool_records

            except Exception as e:
                print(f"Error in agent loop: {str(e)}")
                print(traceback.format_exc())
                await asyncio.sleep(10)
                continue

            self.round += 1
            if max_rounds and self.round > max_rounds:
                break

            if not loop:
                break

            if self.workspace.is_done():
                break

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
  "answer": "已完成"时，你的最终、全面答案"
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

task = """
帮我制定一个计划，5月份到新加坡游玩4-5天，需要尽量保证旅游质量的情况下，经济实惠.
1. 我需要保留2天来回的时间（游玩2-3天）.
2. 需要著名景点，需要包括书店.
3. 餐饮以实惠为主.
住宿我可能不关注，可以住在朋友家里.
"""

async def main(task: str = task):
    agent = Agent(task=task, prompt=prompt)
    await agent.run(loop=True, max_rounds=8)
    if agent.workspace.state['status'] != '已完成':
        brokeprompt = BreakPrompt()
        response = await brokeprompt.run(agent.workspace.to_string())
        print(f"\n最终答案:\n{response}")
    else:
        print(f"\n最终答案:\n{agent.workspace.state['answer']}")

if __name__ == "__main__":
    # if has args, then run main with args
    if len(sys.argv) > 1:
        asyncio.run(main(sys.argv[1]))
    else:   
        asyncio.run(main())