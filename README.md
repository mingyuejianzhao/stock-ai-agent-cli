# 股票分析 AI Agent（A 股） / Stock AI Agent (China A-shares)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#)
[![GitHub stars](https://img.shields.io/github/stars/mingyuejianzhao/stock-ai-agent-cli?style=social)](https://github.com/mingyuejianzhao/stock-ai-agent-cli/stargazers)

中文 / English
- [中文介绍](#中文介绍)
- [English Overview](#english-overview)

---

## 中文介绍

这是一个命令行小工具：输入 A 股股票代码与天数，程序会抓取最近 N 天的收盘价与市场情绪信息（含“恐惧与贪婪指数”代理指标），并让大模型以“看多 / 看空 / 持有 / 最终决策”四个角色输出结构化 JSON 分析结果。

适合用来：
- 快速得到结构化结论（便于接入你自己的工作流/自动化）
- 观察多方观点冲突点（Bull vs Bear vs Hold）
- 结合情绪指标（Fear & Greed proxy）做市场氛围参考

## English Overview

A CLI tool for China A-shares: fetches recent prices + market context (including a proxy “Fear & Greed Index”), then runs a multi-role LLM debate (Bull / Bear / Hold / Judge) and outputs structured JSON insights.

Great for:
- Structured outputs (easy to integrate)
- Multi-perspective debate (pros/cons/neutral)
- Quick sentiment snapshot via Fear & Greed proxy

---

## 目录 / Table of Contents

- [运行环境](#运行环境)
- [安装依赖](#安装依赖)
- [快速开始（中文）](#快速开始中文)
- [配置密钥（不要提交到 GitHub）](#配置密钥不要提交到-github)
- [Quick Start (English)](#quick-start-english)
- [示例输出 / Demo Output](#示例输出--demo-output)
- [恐惧与贪婪指数（说明）](#恐惧与贪婪指数说明)
- [Fear & Greed Index (What it is)](#fear--greed-index-what-it-is)
- [依赖清单（需要下载）](#依赖清单需要下载)

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

## 示例输出 / Demo Output

<details>
<summary>展开 / Expand</summary>

示例输出为示意（字段结构与真实一致，具体内容会随输入与市场数据变化）。

```text
Summary
- Decision: HOLD
- Trend: sideways
- Confidence: 0.62
- Winner: HOLD

Fear & Greed Index
- Score: 54.10
- Rating: Neutral
- Source: AShare Proxy (breadth + northbound)
```

</details>

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

---

免责声明 / Disclaimer
- 本项目仅用于学习与信息展示，不构成任何投资建议。
- This is for educational/informational purposes only. Not financial advice.

## 依赖清单（需要下载）

- `akshare`：拉取 A 股行情数据与市场情绪信息
- `crewai`：多角色 Agent 编排
- `openai`：调用 OpenAI 兼容接口（DashScope Compatible Mode）
- `python-dotenv`：从 `.env` 加载环境变量（可选但推荐）
- `rich`：更美观的命令行界面输出
