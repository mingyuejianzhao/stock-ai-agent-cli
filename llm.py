
import os
import json
from typing import Callable
from openai import OpenAI

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

# 从环境变量中读取阿里云百炼（DashScope）的密钥和网关URL
# 推荐设置：DASHSCOPE_API_KEY 和可选的 DASHSCOPE_BASE_URL
# 兼容：如果未设置 DASHSCOPE_API_KEY，则回退到 OPENAI_API_KEY
def _get_api_key() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")


def _get_base_url() -> str:
    return os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")


def create_client() -> OpenAI:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("请设置 DASHSCOPE_API_KEY（或 OPENAI_API_KEY）环境变量")
    return OpenAI(api_key=api_key, base_url=_get_base_url())


def create_crewai_llm(model: str = "qwen-plus", temperature: float = 0.3, max_tokens: int = 900):
    from crewai.llm import LLM

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("请设置 DASHSCOPE_API_KEY（或 OPENAI_API_KEY）环境变量")

    return LLM(
        model=model,
        api_key=api_key,
        base_url=_get_base_url(),
        temperature=temperature,
        max_tokens=max_tokens,
    )


def chat(messages, model="qwen-plus", temperature=0.7, max_tokens=800) -> str:
    client = create_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _extract_json_object(text: str) -> str | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _chat_json(
    *,
    system: str,
    user: str,
    model: str = "qwen-plus",
    temperature: float = 0.2,
    max_tokens: int = 800,
    validate: Callable[[dict], tuple[bool, str]] | None = None,
) -> dict:
    text = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    json_text = _extract_json_object(text) or text
    try:
        obj = json.loads(json_text)
    except Exception:
        repair_system = (
            "你是一个JSON修复器。你必须只输出一个合法JSON对象，不要输出任何额外文本，不要使用Markdown。"
        )
        repair_user = f"""下面这段输出不是合法JSON。请你只输出一个合法JSON对象，字段名不要改变，类型要正确：
{text}
"""
        text2 = chat(
            messages=[
                {"role": "system", "content": repair_system},
                {"role": "user", "content": repair_user},
            ],
            model=model,
            temperature=0.0,
            max_tokens=max_tokens,
        )
        json_text2 = _extract_json_object(text2) or text2
        obj = json.loads(json_text2)

    if validate is None:
        return obj

    ok, err = validate(obj)
    if ok:
        return obj

    repair_system = (
        "你是一个JSON修复器。你必须只输出一个合法JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    repair_user = f"""下面这段JSON不符合要求。请你根据“错误原因”修复后输出一个合法JSON对象（字段名不要改变，类型要正确，枚举值必须合法）：

错误原因：
{err}

当前输出：
{json.dumps(obj, ensure_ascii=False)}
"""

    text3 = chat(
        messages=[
            {"role": "system", "content": repair_system},
            {"role": "user", "content": repair_user},
        ],
        model=model,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    json_text3 = _extract_json_object(text3) or text3
    obj2 = json.loads(json_text3)
    ok2, err2 = validate(obj2)
    if not ok2:
        raise ValueError(f"模型输出JSON无法通过校验：{err2}")
    return obj2


def _as_float(value) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _validate_agent_payload(obj: dict, stance: str) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "输出不是JSON对象"
    if obj.get("stance") != stance:
        return False, f"stance 必须为 {stance}"
    if obj.get("trend") not in ("up", "down", "sideways"):
        return False, "trend 必须为 up/down/sideways"
    c = _as_float(obj.get("confidence"))
    if c is None or not (0.0 <= c <= 1.0):
        return False, "confidence 必须为 0~1 的数字"
    signals = obj.get("signals")
    if not isinstance(signals, list) or not all(isinstance(s, str) for s in signals):
        return False, "signals 必须为字符串数组"
    if not isinstance(obj.get("analysis"), str):
        return False, "analysis 必须为字符串"
    return True, ""


def _validate_judge_payload(obj: dict) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "输出不是JSON对象"
    if obj.get("decision") not in ("BUY", "SELL", "HOLD"):
        return False, "decision 必须为 BUY/SELL/HOLD"
    if obj.get("trend") not in ("up", "down", "sideways"):
        return False, "trend 必须为 up/down/sideways"
    c = _as_float(obj.get("confidence"))
    if c is None or not (0.0 <= c <= 1.0):
        return False, "confidence 必须为 0~1 的数字"
    if obj.get("winner") not in ("BULL", "BEAR", "HOLD", "TIE"):
        return False, "winner 必须为 BULL/BEAR/HOLD/TIE"
    signals = obj.get("signals")
    if not isinstance(signals, list) or not all(isinstance(s, str) for s in signals):
        return False, "signals 必须为字符串数组"
    if not isinstance(obj.get("analysis"), str):
        return False, "analysis 必须为字符串"
    return True, ""


def parse_and_validate_agent_output(text: str, stance: str) -> dict:
    json_text = _extract_json_object(text) or text
    obj = json.loads(json_text)
    ok, err = _validate_agent_payload(obj, stance)
    if ok:
        return obj

    repair_system = (
        "你是一个JSON修复器。你必须只输出一个合法JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    repair_user = f"""下面这段JSON不符合要求。请你根据“错误原因”修复后输出一个合法JSON对象（字段名不要改变，类型要正确，枚举值必须合法）：

错误原因：
{err}

当前输出：
{json.dumps(obj, ensure_ascii=False)}
"""

    fixed_text = chat(
        messages=[
            {"role": "system", "content": repair_system},
            {"role": "user", "content": repair_user},
        ],
        model="qwen-plus",
        temperature=0.0,
        max_tokens=600,
    )
    fixed_json_text = _extract_json_object(fixed_text) or fixed_text
    fixed_obj = json.loads(fixed_json_text)
    ok2, err2 = _validate_agent_payload(fixed_obj, stance)
    if not ok2:
        raise ValueError(f"模型输出JSON无法通过校验：{err2}")
    return fixed_obj


def parse_and_validate_judge_output(text: str) -> dict:
    json_text = _extract_json_object(text) or text
    obj = json.loads(json_text)
    ok, err = _validate_judge_payload(obj)
    if ok:
        return obj

    repair_system = (
        "你是一个JSON修复器。你必须只输出一个合法JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    repair_user = f"""下面这段JSON不符合要求。请你根据“错误原因”修复后输出一个合法JSON对象（字段名不要改变，类型要正确，枚举值必须合法）：

错误原因：
{err}

当前输出：
{json.dumps(obj, ensure_ascii=False)}
"""

    fixed_text = chat(
        messages=[
            {"role": "system", "content": repair_system},
            {"role": "user", "content": repair_user},
        ],
        model="qwen-plus",
        temperature=0.0,
        max_tokens=700,
    )
    fixed_json_text = _extract_json_object(fixed_text) or fixed_text
    fixed_obj = json.loads(fixed_json_text)
    ok2, err2 = _validate_judge_payload(fixed_obj)
    if not ok2:
        raise ValueError(f"模型输出JSON无法通过校验：{err2}")
    return fixed_obj


def bull_agent(stock_data: str) -> dict:
    system = (
        "你是一个看多股票分析Agent。"
        "你的目标是尽可能找出看涨信号（趋势、反弹、支撑、动能等）。"
        "即使信号较弱，也要给出合理解释。"
        "不要直接否定买入，而是尽量构建“买入逻辑”。"
        "你必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    user = f"""输入是最近几天的股票价格数据：
{stock_data}

请用JSON输出你的观点：
{{
  "stance": "BULL",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}
要求：
- signals 用中文短语，尽量具体（例如“连续两日收盘创新高”）
- confidence 取 0~1
- analysis 简洁但有逻辑
"""
    return _chat_json(
        system=system,
        user=user,
        temperature=0.3,
        max_tokens=700,
        validate=lambda obj: _validate_agent_payload(obj, "BULL"),
    )


def bear_agent(stock_data: str) -> dict:
    system = (
        "你是一个看空股票分析Agent。"
        "你的目标是尽可能找出看跌信号（下跌趋势、破位、动能减弱等）。"
        "强调风险与不确定性，构建“卖出或观望”的逻辑。"
        "你必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    user = f"""输入是最近几天的股票价格数据：
{stock_data}

请用JSON输出你的观点：
{{
  "stance": "BEAR",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}
要求：
- signals 用中文短语，尽量具体（例如“连续三日收盘走低”）
- confidence 取 0~1
- analysis 简洁但有逻辑，突出风险
"""
    return _chat_json(
        system=system,
        user=user,
        temperature=0.3,
        max_tokens=700,
        validate=lambda obj: _validate_agent_payload(obj, "BEAR"),
    )


def hold_agent(stock_data: str) -> dict:
    system = (
        "你是一个继续持有（Hold）股票分析Agent。"
        "你的目标是在不确定或分歧较大时，构建“继续持有”的逻辑。"
        "你需要强调条件化策略（例如：若跌破某价位/若突破某价位再行动）、风险控制与等待确认信号。"
        "你必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    user = f"""输入是最近几天的股票价格数据：
{stock_data}

请用JSON输出你的观点：
{{
  "stance": "HOLD",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}
要求：
- signals 用中文短语，尽量具体（例如“波动收敛，缺乏方向性”）
- confidence 取 0~1
- analysis 简洁但有逻辑，给出持有的触发条件（例如“突破/跌破后再调整仓位”）
"""
    return _chat_json(
        system=system,
        user=user,
        temperature=0.3,
        max_tokens=700,
        validate=lambda obj: _validate_agent_payload(obj, "HOLD"),
    )


def judge_agent(stock_data: str, bull: dict, bear: dict, hold: dict) -> dict:
    system = (
        "你是最终决策Agent。你需要比较各方观点的confidence和signals质量，判断哪一方更有说服力。"
        "不要简单取高confidence，要结合逻辑质量判断。"
        "你必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )
    user = f"""输入是最近几天的股票价格数据：
{stock_data}

看多Agent输出：
{json.dumps(bull, ensure_ascii=False)}

看空Agent输出：
{json.dumps(bear, ensure_ascii=False)}

继续持有Agent输出：
{json.dumps(hold, ensure_ascii=False)}

请给出最终决策（BUY / SELL / HOLD），并说明理由。输出JSON：
{{
  "decision": "BUY|SELL|HOLD",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "winner": "BULL|BEAR|HOLD|TIE",
  "signals": [],
  "analysis": ""
}}
要求：
- signals 是你认为最关键的、经过筛选的信号（中文短语列表）
- analysis 解释为何某方更有说服力（可以指出对方逻辑薄弱点），并说明为何不选另外两方
"""
    return _chat_json(
        system=system,
        user=user,
        temperature=0.2,
        max_tokens=900,
        validate=_validate_judge_payload,
    )


def multi_agent_debate(stock_data: str) -> dict:
    bull = bull_agent(stock_data)
    bear = bear_agent(stock_data)
    hold = hold_agent(stock_data)
    judge = judge_agent(stock_data, bull, bear, hold)
    return {"bull": bull, "bear": bear, "hold": hold, "judge": judge}


def analyze_prices_json(stock_data: str) -> dict:
    system = (
        "你是一个股票分析Agent。"
        "输入是最近几天的股票价格数据。"
        "你必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown。"
    )

    user = f"""
输入是最近几天的股票价格数据：
{stock_data}

请完成：
1. 判断趋势（up / down / sideways）
2. 给出决策（buy / sell / hold）
3. 提取关键信号（列表形式）
4. 给出分析总结
5. 给出置信度（0-1）

必须用JSON格式输出：
{{
  "decision": "",
  "trend": "",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}
"""

    return _chat_json(system=system, user=user, temperature=0.2, max_tokens=500)


def get_investment_advice(stock_data):
    try:
        prompt = f"""
你是一位专业的股票分析师。
请根据以下最近几天的股票数据，为我提供关于这只股票的投资建议。

股票数据：
{stock_data}

请提供明确的结论（买入、卖出、观望），并给出简洁的理由（不超过100字）。
你的回答应该只包含结论和理由，不要有其他无关内容。
"""

        return chat(
            messages=[
                {"role": "system", "content": "你是一位专业的股票分析师。"},
                {"role": "user", "content": prompt},
            ],
            model="qwen-plus",
            temperature=0.7,
            max_tokens=150,
        )
    except Exception as e:
        return f"调用AI模型时发生错误：{e}"

if __name__ == '__main__':
    # 这是一个测试代码块
    test_data = """
    AAPL 最近 5 天的收盘价：
    2023-10-23: 173.00
    2023-10-24: 173.44
    2023-10-25: 171.10
    2023-10-26: 166.89
    2023-10-27: 168.22
    """
    advice = get_investment_advice(test_data)
    print("AI 投资建议：")
    print(advice)
