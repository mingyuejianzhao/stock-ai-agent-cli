# 股票分析 AI Agent（A 股）

这是一个命令行小工具：输入 A 股股票代码与天数，程序会抓取最近 N 天的收盘价，并调用大模型分别以“看多 / 看空 / 持有 / 最终决策”四个角色输出结构化 JSON 分析结果。

## 运行环境

- Python 3.11+（建议使用虚拟环境）

## 安装依赖

```bash
pip install -r requirements.txt
```

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

## 使用方法

启动：

```bash
python main.py
```

按提示输入：

- 仅股票代码：`600519`
- 股票代码 + 天数：`600519 5`
- 也支持显式交易所后缀：`600519.SS` / `000001.SZ`

退出：输入 `exit`

## 依赖清单（需要下载）

- `akshare`：拉取 A 股行情数据与市场信息
- `crewai`：多角色 Agent 编排
- `openai`：调用 OpenAI 兼容接口（DashScope Compatible Mode）
- `python-dotenv`：从 `.env` 加载环境变量（可选但推荐）
