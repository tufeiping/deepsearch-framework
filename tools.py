import os
import aiohttp
from typing import TypedDict, List
from tavily import TavilyClient
import re
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

def extract_largest_json(text):
    """
    从文本中提取最大的JSON对象
    """
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    matches = re.findall(json_pattern, text)
    
    if not matches:
        return None
    
    # 按长度排序，取最长的
    matches.sort(key=len, reverse=True)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None

class ScrapTool:
    def __init__(self, gather_links: bool = True) -> None:
        self.gather_links = gather_links

    async def __call__(self, input: str, context: str | None) -> str:
        try:
            result = await self.scrap_webpage(input, context)
            return result
        except Exception as e:
            error_message = f"抓取网页失败: {str(e)}"
            print(error_message)
            return error_message

    async def scrap_webpage(self, url: str, context: str | None) -> str:
        # 如果URL不是以http或https开头，添加https前缀
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        return f"无法获取页面 {url}: HTTP状态码 {response.status}"
                    html = await response.text()
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除JavaScript和CSS
            for script in soup(["script", "style"]):
                script.extract()
            
            # 获取文本内容
            text = soup.get_text()
            
            # 清理文本（删除多余空行和空格）
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # 如果需要收集链接
            if self.gather_links:
                links = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    # 处理相对URL
                    if href.startswith('/'):
                        base_url = re.match(r'https?://[^/]+', url)
                        if base_url:
                            href = f"{base_url.group(0)}{href}"
                    elif not href.startswith(('http://', 'https://')):
                        href = f"{url.rstrip('/')}/{href.lstrip('/')}"
                    
                    link_text = link.get_text().strip()
                    if link_text and href:
                        links.append(f"{link_text}: {href}")
                
                if links:
                    text += "\n\n链接摘要:\n" + "\n".join(links)
            
            # 如果提供了上下文，可以简单地根据上下文关键词过滤内容
            if context is not None:
                # 简单的上下文匹配 - 提取包含上下文关键词的段落
                context_keywords = context.lower().split()
                paragraphs = text.split('\n\n')
                relevant_paragraphs = []
                
                for para in paragraphs:
                    if any(keyword in para.lower() for keyword in context_keywords):
                        relevant_paragraphs.append(para)
                
                if relevant_paragraphs:
                    text = '\n\n'.join(relevant_paragraphs)
            
            return text

        except Exception as e:
            return f"抓取 {url} 时出错: {str(e)}"
        

class SearchResult(TypedDict):
    url: str
    title: str
    description: str


class SearchTool:
    def __init__(self, timeout: int = 60 * 5) -> None:
        self.timeout = timeout
        self.tavily_client = None
        # 初始化时先不创建客户端，因为可能还没有设置 API 密钥

    async def __call__(self, input: str, *args) -> str:
        results = await self.search(input)
        formatted_results = self._format_results(results)
        return formatted_results

    async def search(self, query: str) -> List[SearchResult]:
        # 懒加载 TavilyClient，确保在首次使用时创建
        if self.tavily_client is None:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise Exception("TAVILY_API_KEY environment variable not set. Please add it to your .env file.")
            self.tavily_client = TavilyClient(api_key=api_key)

        try:
            # 使用 Tavily 进行搜索
            response = self.tavily_client.search(
                query=query,
                search_depth="basic"  # 或者使用 "advanced"，取决于需求
            )
            
            # 从 Tavily 响应中提取相关信息
            results = []
            for result in response.get("results", []):
                results.append(
                    SearchResult(
                        url=result.get("url", ""),
                        title=result.get("title", ""),
                        description=result.get("content", "")  # Tavily 可能使用 "content" 而不是 "description"
                    )
                )
            
            return results

        except Exception as e:
            print(f"Tavily搜索错误: {str(e)}")
            return []

    def _format_results(self, results: List[SearchResult]) -> str:
        formatted_results = []

        for i, result in enumerate(results, 1):
            formatted_results.extend(
                [
                    f"Title: {result['title']}",
                    f"URL Source: {result['url']}",
                    f"Description: {result['description']}",
                    "",
                ]
            )

        return "\n".join(formatted_results).rstrip()