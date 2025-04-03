import os

from llm import OpenRouterModel
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

PROMPT = """
你是一个可以总结和归纳的AI，请根据以下内容，总结出最核心的内容，并给出总结后的内容。
比如下面是返回内容：
```
Status: 进行中
Memory: 
<ivx-110>经济餐饮推荐（来源3）：
- 牛车水大厦美食中心：了凡油鸡饭面
- 中鲁市场：柏水
- 老巴刹沙街
需验证档口营业时间</ivx-110>
<lnp-232>圣淘沙景点门票确认（来源1）：西乐索海滩免费，巴拉望海滩免费，环球影城需门票（SGD82起）</lnp-232>
<pnt-158>新增特色书店信息（来源2）：Woods in the books（永锡街3号，10:00-19:00，周二休）和Littered with Books（达士敦路20号，12:00-20:00）</pnt-158>
<xmn-907>餐饮时间补充（来源1）：老巴刹沙嗲街19:00-凌晨开放，牛车水中秋灯会2025年8月30日-10月2日（可能与行程时间不匹配）</xmn-907>
<blp-631>更新景点清单（来源1）：
- 免费景点：滨海湾花园户外区/灯光秀、鱼尾狮公园、阿拉伯区哈芝巷、牛车水佛牙寺
- 收费景点：滨海湾花园冷室（SGD28）、金沙观景台（SGD26）</blp-631>
<aie-832>更新特色书店营业时间（来源1）：
1. 卓尔书店 10:00-22:00
2. 草根书室 12:00-20:00（周二休）
3. Woods in the Books 10:00-19:00（周二休）
4. Littered with Books 12:00-20:00</aie-832>
<nqe-987>交通卡信息（来源3）：游客通行卡三日卡SGD20（含SGD10押金），可无限次乘坐公交地铁</nqe-987>
<oir-870>新增经济餐饮（来源1）：猩猩咖喱（武吉巴督街33号）、HJH Maimunah（惹兰比桑11号）、Nakhon Kitchen（VivoCity B2层）</oir-870>
<bjr-569>环球影城新活动线索（来源3）：2025年2月开放小黄人乐园，需确认5月是否持续</bjr-569>
<gre-315>需补充景点间交通动线：结合现有景点分布优化行程路线</gre-315>
<lgl-675>卫塞节期间运营确认（来源1）：2025年5月12日为公共假期，环球影城/滨海湾花园官网显示正常开放，书店需单独确认</lgl-675>
<oqp-155>环球影城门票新线索（来源2）：Klook客路平台提供29%折扣门票（需验证有效期是否含5月）</oqp-155>
<jrg-426>需验证Klook环球影城折扣票有效期是否包含2025年5月（来源1）</jrg-426>
<mcx-260>卫塞节（5月12日）书店营业时间需特别确认：卓尔书店/草根书室/Woods in the Books周二休，可能受公共假期影响</mcx-260>
<uxn-976>Klook环球影城门票页面需抓取有效期细节（来源1）：https://www.klook.com/zh-CN/activity/117-universal-studios-singapore/</uxn-976>
<aap-339>需验证VivoCity大食代替代方案：搜索'怡丰城Food Republic 2025营业时间'</aap-339>
<fvm-108>卫塞节书店营业时间缺口：需专项搜索'卓尔书店 草根书室 2025年5月12日营业时间'</fvm-108>
```
你应该关注确定的景点，比如：游客通行卡三日卡SGD20（含SGD10押金），可无限次乘坐公交地铁;西乐索海滩免费，巴拉望海滩免费，环球影城需门票（SGD82起等。而对于不确定的内容，如：书店营业时间需特别确认，需专项搜索'卓尔书店 草根书室 2025年5月12日营业时间'，则不需要关注。

以下是你需要总结和归纳的内容：
```
{content}
```

"""

class BreakPrompt():
    def __init__(self):
        self.model = OpenRouterModel(api_key=os.getenv("OPENROUTER_API_KEY"))

    async def run(self, content: str):
        try:
            return await self.model(PROMPT.format(content=content))
        except Exception as e:
            print(e)
            raise