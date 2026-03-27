
# 导入我们自己创建的模块
import os
import json
from data import get_market_context, get_stock_data
from crewai import Agent as CrewAgent
from crewai import Crew, Process, Task
from llm import create_crewai_llm, parse_and_validate_agent_output, parse_and_validate_judge_output

def analyze_stock(ticker, days=5):
    """
    执行完整的股票分析流程。

    :param ticker: 用户输入的股票代码
    :param days: 需要获取的天数
    :return: 包含分析结果的字符串
    """
    print(f"正在获取 {ticker} 的股票数据...")
    
    # 1. 获取股票数据
    stock_data = get_stock_data(ticker, days=days)
    
    # 检查数据获取是否成功
    if "错误" in stock_data:
        return stock_data
    
    market_context = get_market_context(ticker)

    print("数据获取成功，正在调用 AI 模型进行分析...")
    print("\n" + stock_data)
    print("市场情绪信息：")
    print(json.dumps(market_context, ensure_ascii=False, indent=2))
    
    combined_input = (
        stock_data
        + "\n\n市场情绪信息（信息收集层）：\n"
        + json.dumps(market_context, ensure_ascii=False, indent=2)
        + "\n"
    )

    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

    llm = create_crewai_llm(model="qwen-plus", temperature=0.3, max_tokens=900)

    bull = CrewAgent(
        role="看多分析师",
        goal="尽可能找出看涨信号，并构建买入逻辑",
        backstory="你偏向寻找上涨证据，但必须基于输入数据，不要虚构成交量或K线细节。",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    bear = CrewAgent(
        role="看空分析师",
        goal="尽可能找出看跌信号，强调风险与不确定性，构建卖出或观望逻辑",
        backstory="你偏向寻找下跌证据，但必须基于输入数据，不要虚构成交量或K线细节。",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    hold = CrewAgent(
        role="持有策略师",
        goal="在分歧或不确定时构建继续持有逻辑，并给出条件化策略与风控触发点",
        backstory="你强调稳健与可验证的条件触发，不要给无法从输入推导的细节。",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    judge = CrewAgent(
        role="最终决策官",
        goal="比较各方的 confidence 与信号质量，综合给出 BUY/SELL/HOLD 的最终决策",
        backstory="你不简单看谁自信高，而是评估证据是否可验证、逻辑是否闭环。",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    bull_task = Task(
        agent=bull,
        description=f"""输入是最近几天的股票价格数据与市场情绪信息：
{combined_input}

请尽可能找出看涨信号（趋势、反弹、支撑、动能等）。即使信号较弱，也要给出合理解释。不要直接否定买入，而是尽量构建“买入逻辑”。

必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown：
{{
  "stance": "BULL",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}""",
        expected_output="严格JSON对象，stance=BULL，trend 枚举，confidence 0~1，signals 字符串数组。",
        markdown=False,
    )

    bear_task = Task(
        agent=bear,
        description=f"""输入是最近几天的股票价格数据与市场情绪信息：
{combined_input}

请尽可能找出看跌信号（下跌趋势、破位、动能减弱等）。强调风险与不确定性，构建“卖出或观望”的逻辑。

必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown：
{{
  "stance": "BEAR",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}""",
        expected_output="严格JSON对象，stance=BEAR，trend 枚举，confidence 0~1，signals 字符串数组。",
        markdown=False,
    )

    hold_task = Task(
        agent=hold,
        description=f"""输入是最近几天的股票价格数据与市场情绪信息：
{combined_input}

请构建“继续持有”的逻辑，强调条件化策略（突破/跌破后再行动）、风险控制与等待确认信号。

必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown：
{{
  "stance": "HOLD",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "signals": [],
  "analysis": ""
}}""",
        expected_output="严格JSON对象，stance=HOLD，trend 枚举，confidence 0~1，signals 字符串数组。",
        markdown=False,
    )

    judge_task = Task(
        agent=judge,
        context=[bull_task, bear_task, hold_task],
        description=f"""输入是最近几天的股票价格数据与市场情绪信息：
{combined_input}

你将收到看多/看空/持有三方的输出作为上下文。请比较双方的 confidence 和 signals 质量，判断哪一方更有说服力。不要简单取高 confidence，要结合逻辑质量判断。综合给出最终决策（BUY / SELL / HOLD）。

必须只输出JSON对象，不要输出任何额外文本，不要使用Markdown：
{{
  "decision": "BUY|SELL|HOLD",
  "trend": "up|down|sideways",
  "confidence": 0.0,
  "winner": "BULL|BEAR|HOLD|TIE",
  "signals": [],
  "analysis": ""
}}""",
        expected_output="严格JSON对象，decision 枚举，trend 枚举，confidence 0~1，winner 枚举，signals 字符串数组。",
        markdown=False,
    )

    crew = Crew(
        agents=[bull, bear, hold, judge],
        tasks=[bull_task, bear_task, hold_task, judge_task],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )

    crew.kickoff()

    bull_out = parse_and_validate_agent_output(bull_task.output.raw, "BULL") if bull_task.output else {}
    bear_out = parse_and_validate_agent_output(bear_task.output.raw, "BEAR") if bear_task.output else {}
    hold_out = parse_and_validate_agent_output(hold_task.output.raw, "HOLD") if hold_task.output else {}
    judge_out = parse_and_validate_judge_output(judge_task.output.raw) if judge_task.output else {}

    advice = {
        "bull": bull_out,
        "bear": bear_out,
        "hold": hold_out,
        "judge": judge_out,
        "market_context": market_context,
    }
    
    print("AI 分析完成！")
    
    # 3. 返回最终结果
    return advice

if __name__ == '__main__':
    # 这是一个测试代码块
    test_ticker = "600519"  # 以贵州茅台为例
    final_advice = analyze_stock(test_ticker)
    
    print("\n--- 分析结果 ---")
    print(final_advice)
    print("------------------")
