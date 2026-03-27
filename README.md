# 股票分析 AI Agent（A 股） / Stock AI Agent (China A-shares)

这是一个命令行小工具：输入 A 股股票代码与天数，程序会抓取最近 N 天的收盘价与市场情绪信息（含“恐惧与贪婪指数”代理指标），并调用大模型分别以“看多 / 看空 / 持有 / 最终决策”四个角色输出结构化 JSON 分析结果。

A CLI tool for China A-shares: fetches recent prices + market context (including a proxy “Fear & Greed Index”), then runs a multi-role LLM debate (Bull/Bear/Hold/Judge) and outputs structured JSON insights.

## 运行环境

- Python 3.11+（建议使用虚拟环境）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始（中文）

启动：

```bash
python main.py
```

按提示输入：

- 仅股票代码：`600519`
- 股票代码 + 天数：`600519 5`
- 也支持显式交易所后缀：`600519.SS` / `000001.SZ`

退出：输入 `exit`

## 配置密钥（不要提交到 GitHub）

本项目通过阿里云百炼（DashScope）的 OpenAI 兼容接口调用模型。

1) 复制环境变量模板：

```bash
copy .env.example .env
```

2) 编辑 `.env`，填入你的密钥：

- `DASHSCOPE_API_KEY`：必填
- `DASHSCOPE_BASE_URL`：可选（默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`）

说明：项目已在 `.gitignore` 中忽略 `.env`，公开仓库不会上传你的密钥。

## Quick Start (English)

Run:

```bash
python main.py
```

Examples:

- Ticker only: `600519`
- Ticker + days: `600519 5`
- With exchange suffix: `600519.SS` / `000001.SZ`

Quit: type `exit`

Optional flags:

```bash
python main.py 600519 5 --lang en
python main.py 600519 5 --json
```

## 恐惧与贪婪指数（说明）

这里的“恐惧与贪婪指数”不是官方指数，而是一个 A 股市场情绪的代理指标（proxy），基于：

- 市场涨跌家数/涨跌幅分布（breadth）
- 涨停/跌停的强弱
- 北向资金净流入（若可获取）

输出字段：

- `score`：0~100，越高越偏“贪婪”
- `rating`：Extreme Fear / Fear / Neutral / Greed / Extreme Greed

## Fear & Greed Index (What it is)

This project shows a *proxy* Fear & Greed Index for China A-shares (not an official index). It’s derived from:

- Market breadth (advancers/decliners)
- Limit-up vs limit-down strength
- Northbound net inflow (when available)

Fields:

- `score`: 0~100 (higher means more “greed”)
- `rating`: Extreme Fear / Fear / Neutral / Greed / Extreme Greed

## 依赖清单（需要下载）

- `akshare`：拉取 A 股行情数据与市场信息
- `crewai`：多角色 Agent 编排
- `openai`：调用 OpenAI 兼容接口（DashScope Compatible Mode）
- `python-dotenv`：从 `.env` 加载环境变量（可选但推荐）
- `rich`：更美观的命令行界面输出
