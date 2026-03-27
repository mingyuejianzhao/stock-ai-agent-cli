
import argparse
import json
from agent import analyze_stock

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except Exception:
    Console = None
    Table = None
    Panel = None

_ZH = {
    "title": "股票分析 AI Agent（A 股）",
    "prompt": "\n请输入股票代码（可选天数，例如 600519 5）：",
    "exit_hint": "您可以随时输入 'exit' 来退出程序。",
    "bye": "感谢使用，再见！",
    "error": "在分析过程中发生未知错误：{e}",
    "summary": "摘要",
    "decision": "最终决策",
    "trend": "趋势",
    "confidence": "置信度",
    "winner": "胜方",
    "fear_greed": "恐惧与贪婪指数",
    "score": "分数",
    "rating": "评级",
    "source": "来源",
    "bull": "看多（BULL）",
    "bear": "看空（BEAR）",
    "hold": "持有（HOLD）",
    "signals": "信号",
    "analysis": "分析",
    "sep": "---------------------",
}

_EN = {
    "title": "Stock AI Agent (China A-shares)",
    "prompt": "\nEnter ticker (optional days, e.g. 600519 5): ",
    "exit_hint": "Type 'exit' anytime to quit.",
    "bye": "Bye.",
    "error": "Unexpected error during analysis: {e}",
    "summary": "Summary",
    "decision": "Decision",
    "trend": "Trend",
    "confidence": "Confidence",
    "winner": "Winner",
    "fear_greed": "Fear & Greed Index",
    "score": "Score",
    "rating": "Rating",
    "source": "Source",
    "bull": "Bull (BULL)",
    "bear": "Bear (BEAR)",
    "hold": "Hold (HOLD)",
    "signals": "Signals",
    "analysis": "Analysis",
    "sep": "---------------------",
}


def _pick_lang(lang: str | None) -> dict:
    if (lang or "").lower().startswith("en"):
        return _EN
    return _ZH


def _format_conf(v) -> str:
    try:
        f = float(v)
        return f"{f:.2f}"
    except Exception:
        return str(v)


def _render_rich(result: dict, text: dict) -> None:
    console = Console()
    market = result.get("market_context") or {}
    fear = (market.get("fear_greed") or {}) if isinstance(market, dict) else {}
    judge = result.get("judge") or {}

    rows = [
        (text["decision"], (judge.get("decision") or "")),
        (text["trend"], (judge.get("trend") or "")),
        (text["confidence"], _format_conf(judge.get("confidence"))),
        (text["winner"], (judge.get("winner") or "")),
    ]

    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column(style="bold")
    t.add_column()
    for k, v in rows:
        t.add_row(k, str(v))

    if isinstance(fear, dict) and fear:
        fg = Table(show_header=False, box=None, pad_edge=False)
        fg.add_column(style="bold")
        fg.add_column()
        fg.add_row(text["score"], str(fear.get("score", "")))
        fg.add_row(text["rating"], str(fear.get("rating", "")))
        fg.add_row(text["source"], str(fear.get("source", "")))
        console.print(Panel.fit(t, title=text["summary"]))
        console.print(Panel.fit(fg, title=text["fear_greed"]))
    else:
        console.print(Panel.fit(t, title=text["summary"]))

    for key in ("bull", "bear", "hold"):
        obj = result.get(key) or {}
        p = Table(show_header=False, box=None, pad_edge=False)
        p.add_column(style="bold")
        p.add_column()
        p.add_row(text["trend"], str(obj.get("trend", "")))
        p.add_row(text["confidence"], _format_conf(obj.get("confidence")))
        sig = obj.get("signals") or []
        if isinstance(sig, list):
            sig_text = "\n".join([f"- {s}" for s in sig if isinstance(s, str)]) or ""
        else:
            sig_text = str(sig)
        p.add_row(text["signals"], sig_text)
        p.add_row(text["analysis"], str(obj.get("analysis", "")))
        title = text[key]
        console.print(Panel(p, title=title))


def _render_plain(result: dict, text: dict) -> None:
    market = result.get("market_context") or {}
    fear = (market.get("fear_greed") or {}) if isinstance(market, dict) else {}
    judge = result.get("judge") or {}

    print(f"\n{text['summary']}:")
    print(f"- {text['decision']}: {judge.get('decision', '')}")
    print(f"- {text['trend']}: {judge.get('trend', '')}")
    print(f"- {text['confidence']}: {_format_conf(judge.get('confidence'))}")
    print(f"- {text['winner']}: {judge.get('winner', '')}")

    if isinstance(fear, dict) and fear:
        print(f"\n{text['fear_greed']}:")
        print(f"- {text['score']}: {fear.get('score', '')}")
        print(f"- {text['rating']}: {fear.get('rating', '')}")
        print(f"- {text['source']}: {fear.get('source', '')}")

    def _print_agent(title: str, obj: dict) -> None:
        print(f"\n--- {title} ---")
        print(f"{text['trend']}: {obj.get('trend', '')}")
        print(f"{text['confidence']}: {_format_conf(obj.get('confidence'))}")
        sig = obj.get("signals") or []
        if isinstance(sig, list) and sig:
            print(text["signals"] + ":")
            for s in sig:
                if isinstance(s, str) and s.strip():
                    print(f"- {s}")
        else:
            print(text["signals"] + ":")
            print("（无）" if text is _ZH else "(none)")
        print(text["analysis"] + ":")
        print(obj.get("analysis", ""))

    _print_agent(text["bull"], result.get("bull") or {})
    _print_agent(text["bear"], result.get("bear") or {})
    _print_agent(text["hold"], result.get("hold") or {})


def _run_once(ticker: str, days: int, *, as_json: bool, text: dict) -> None:
    result = analyze_stock(ticker, days=days)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if isinstance(result, dict) and Console is not None and Table is not None and Panel is not None:
        _render_rich(result, text)
    elif isinstance(result, dict):
        _render_plain(result, text)
    else:
        print(result)
    print("\n" + text["sep"])


def main():
    """
    程序主函数，负责与用户交互。
    """
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("ticker", nargs="?", help="Ticker, e.g. 600519")
    parser.add_argument("days", nargs="?", type=int, help="Days, e.g. 5")
    parser.add_argument("--lang", default="zh", choices=["zh", "en"], help="UI language")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output")
    args = parser.parse_args()

    text = _pick_lang(args.lang)
    print(text["title"])
    print(text["exit_hint"])

    if args.ticker:
        _run_once(args.ticker, args.days or 5, as_json=args.json, text=text)
        return

    while True:
        raw = input(text["prompt"]).strip()
        if not raw:
            continue

        if raw.lower() == "exit":
            print(text["bye"])
            break

        parts = raw.split()
        ticker = parts[0].strip()
        days = 5
        for p in parts[1:]:
            try:
                days = int(p)
            except Exception:
                pass

        try:
            _run_once(ticker, days, as_json=args.json, text=text)
        except Exception as e:
            print(text["error"].format(e=e))

if __name__ == "__main__":
    main()
