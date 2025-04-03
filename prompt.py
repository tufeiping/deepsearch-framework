import os
from typing import Any, Dict
from jinja2 import Environment, BaseLoader
from llm import OpenRouterModel
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 获取API密钥并添加错误处理
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY environment variable not set. Please add it to your .env file.")
    
model = OpenRouterModel(api_key=api_key)

class Prompt:
    def __init__(self, template: str) -> None:
        self.template = template
        self.env = Environment(loader=BaseLoader())

    def __call__(self, **variables) -> str:
        prompt_template = self.env.from_string(self.template)
        prompt = prompt_template.render(**variables)
        prompt = prompt.strip()
        return prompt

    async def run(
        self,
        prompt_variables: Dict[str, Any] = {},
        generation_args: Dict[str, Any] = {},
    ) -> str:
        global model
        prompt = self(**prompt_variables)
        print(f"\nPrompt:\n{prompt}")
        try:
            result = await model(prompt)
            print(f"\n结果:\n{result}")
            return result
        except Exception as e:
            print(e)
            raise