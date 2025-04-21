import os
import aiohttp
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

class OpenRouterModel:
    def __init__(self, model_name=None, api_key=None, base_url=None): #openai/gpt-4.1 deepseek/deepseek-r1:free
        self.model_name = model_name or os.getenv("MODEL_NAME")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("API_BASE_URL")

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages, reasoning_effort="low"):
        return {
            "model": self.model_name,
            "messages": messages,
            "reasoning": {"effort": reasoning_effort},
        }

    async def __call__(self, message: str, reasoning_effort="low"):
        messages = [{"role": "user", "content": message}]
        headers = self._get_headers()
        payload = self._build_payload(messages, reasoning_effort)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url, headers=headers, json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"API request failed with status {response.status}: {error_text}"
                    )
                response = await response.json()
                print(response)
                think_content = response["choices"][0]["message"]["reasoning"]
                content = (
                    think_content + "\n" + response["choices"][0]["message"]["content"]
                )
                return content