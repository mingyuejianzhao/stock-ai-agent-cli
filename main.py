
import json
from agent import analyze_stock

def main():
    """
    程序主函数，负责与用户交互。
    """
    print("欢迎使用股票分析 AI Agent！")
    print("您可以随时输入 'exit' 来退出程序。")

    while True:
        raw = input("\n请输入股票代码（可选天数，例如 600519 5）：").strip()
        if not raw:
            continue

        if raw.lower() == "exit":
            print("感谢使用，再见！")
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
            result = analyze_stock(ticker, days=days)
            if isinstance(result, dict):
                bull = result.get("bull")
                bear = result.get("bear")
                hold = result.get("hold")
                judge = result.get("judge")

                print("\n--- 看多 Agent（BULL） ---")
                print(json.dumps(bull, ensure_ascii=False, indent=2))
                print("\n--- 看空 Agent（BEAR） ---")
                print(json.dumps(bear, ensure_ascii=False, indent=2))
                print("\n--- 持有 Agent（HOLD） ---")
                print(json.dumps(hold, ensure_ascii=False, indent=2))
                print("\n--- 最终决策 Agent（JUDGE） ---")
                print(json.dumps(judge, ensure_ascii=False, indent=2))
            else:
                print("\n--- 输出 ---")
                print(result)
            print("\n---------------------")
        except Exception as e:
            print(f"在分析过程中发生未知错误：{e}")

if __name__ == "__main__":
    main()
