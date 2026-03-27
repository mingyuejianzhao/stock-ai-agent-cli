
import datetime
import contextlib
import io
import time

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

try:
    import akshare as ak
except ImportError:
    ak = None

_CACHE: dict[tuple[str, int], tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 60
_SENTIMENT_CACHE: dict[str, tuple[float, dict]] = {}
_SENTIMENT_TTL_SECONDS = 300


def _normalize_ticker(raw: str) -> str:
    t = (raw or "").strip().upper()
    if t.isdigit() and len(t) == 6:
        if t.startswith("6"):
            return f"{t}.SS"
        return f"{t}.SZ"
    return t


def _silent_call(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


def _as_float(value) -> float | None:
    try:
        return float(value)
    except Exception:
        return None



def _tanh(x: float) -> float:
    e2x = pow(2.718281828459045, 2 * x)
    return (e2x - 1) / (e2x + 1)


def _fear_greed_proxy(breadth: dict | None, northbound: dict | None) -> dict:
    score = 50.0
    details = {}

    if isinstance(breadth, dict):
        up = _as_float(breadth.get("up")) or 0.0
        down = _as_float(breadth.get("down")) or 0.0
        total = _as_float(breadth.get("total")) or (up + down)
        if total > 0:
            balance = (up - down) / total
            score += balance * 20.0
            details["breadth_balance"] = balance

        limit_up = _as_float(breadth.get("limit_up")) or 0.0
        limit_down = _as_float(breadth.get("limit_down")) or 0.0
        if total > 0:
            limit_balance = (limit_up - limit_down) / total
            score += limit_balance * 30.0
            details["limit_balance"] = limit_balance

    if isinstance(northbound, dict):
        v = _as_float(northbound.get("net_inflow_billion_cny"))
        if v is not None:
            score += _tanh(v / 50.0) * 10.0
            details["northbound_scaled"] = _tanh(v / 50.0)

    score = max(0.0, min(100.0, score))
    rating = (
        "Extreme Fear"
        if score < 25
        else "Fear"
        if score < 45
        else "Neutral"
        if score < 55
        else "Greed"
        if score < 75
        else "Extreme Greed"
    )

    return {
        "score": round(score, 2),
        "rating": rating,
        "source": "AShare Proxy (breadth + northbound)",
        "details": details,
    }


def _make_json_safe(value):
    if isinstance(value, dict):
        return {str(k): _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(v) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().isoformat()
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _akshare_a_share_breadth() -> dict | None:
    if ak is None:
        return None
    df = _silent_call(ak.stock_zh_a_spot_em)
    if df is None or df.empty:
        return None

    change_col = "涨跌幅"
    if change_col not in df.columns:
        return None

    s = df[change_col]
    up = int((s > 0).sum())
    down = int((s < 0).sum())
    flat = int((s == 0).sum())
    total = int(len(s))
    limit_up = int((s >= 9.9).sum())
    limit_down = int((s <= -9.9).sum())
    avg_change = float(s.mean()) if total else 0.0
    return {
        "total": total,
        "up": up,
        "down": down,
        "flat": flat,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "avg_change_pct": round(avg_change, 4),
    }


def _akshare_major_indices() -> list[dict] | None:
    if ak is None:
        return None
    if hasattr(ak, "stock_zh_index_spot_em"):
        df = _silent_call(ak.stock_zh_index_spot_em)
    elif hasattr(ak, "stock_zh_index_spot_sina"):
        df = _silent_call(ak.stock_zh_index_spot_sina)
    else:
        return None
    if df is None or df.empty:
        return None

    names = {"上证指数", "深证成指", "创业板指"}
    if "名称" not in df.columns:
        return None
    rows = df[df["名称"].isin(names)]
    result = []
    for _, r in rows.iterrows():
        result.append(
            {
                "name": r.get("名称"),
                "price": _as_float(r.get("最新价")),
                "change_pct": _as_float(r.get("涨跌幅")),
            }
        )
    return result


def _akshare_northbound_latest() -> dict | None:
    if ak is None:
        return None
    if not hasattr(ak, "stock_hsgt_fund_flow_summary_em"):
        return None
    df = _silent_call(ak.stock_hsgt_fund_flow_summary_em)
    if df is None or df.empty:
        return None

    required = {"交易日", "资金方向", "成交净买额"}
    if not required.issubset(set(df.columns)):
        return None

    latest_date = df["交易日"].iloc[0]
    latest = df[df["交易日"] == latest_date]
    north = latest[latest["资金方向"] == "北向"]
    if north.empty:
        return None
    v = _as_float(north["成交净买额"].sum())
    return {
        "date": str(latest_date),
        "net_inflow_billion_cny": v,
    }


def _akshare_individual_fund_flow(ticker: str) -> dict | None:
    if ak is None:
        return None
    t = _normalize_ticker(ticker)
    if "." not in t:
        return None
    code, suffix = t.split(".", 1)
    if suffix not in ("SS", "SZ", "BJ"):
        return None
    market = "sh" if suffix == "SS" else "sz" if suffix == "SZ" else "bj"
    df = _silent_call(ak.stock_individual_fund_flow, stock=code, market=market)
    if df is None or df.empty:
        return None
    last = df.iloc[-1].to_dict()
    for k, v in list(last.items()):
        if hasattr(v, "item"):
            last[k] = v.item()
    return {"market": market, "latest": last}


def get_market_context(ticker: str) -> dict:
    key = _normalize_ticker(ticker)
    cached = _SENTIMENT_CACHE.get(key)
    now = time.time()
    if cached is not None and now - cached[0] <= _SENTIMENT_TTL_SECONDS:
        return cached[1]

    if ak is None:
        context = {"ticker": key, "error": "未安装 akshare，请先安装：pip install akshare"}
        _SENTIMENT_CACHE[key] = (now, context)
        return context

    breadth = None
    indices = None
    northbound = None
    fund_flow = None
    error = {}
    try:
        breadth = _akshare_a_share_breadth()
    except Exception as e:
        error["breadth_error"] = str(e)
    try:
        indices = _akshare_major_indices()
    except Exception as e:
        error["indices_error"] = str(e)
    try:
        northbound = _akshare_northbound_latest()
    except Exception as e:
        error["northbound_error"] = str(e)
    try:
        fund_flow = _akshare_individual_fund_flow(key)
    except Exception as e:
        error["fund_flow_error"] = str(e)

    fear_greed = _fear_greed_proxy(breadth, northbound)

    context = {
        "ticker": key,
        "source": "AkShare",
        "indices": indices,
        "breadth": breadth,
        "northbound": northbound,
        "fund_flow": fund_flow,
        "fear_greed": fear_greed,
    }
    if error:
        context["errors"] = error

    safe = _make_json_safe(context)
    _SENTIMENT_CACHE[key] = (now, safe)
    return safe


def get_stock_data(ticker, days=5):
    """
    获取指定股票代码最近N天的历史数据。

    :param ticker: 股票代码，例如 "AAPL"
    :param days: 需要获取的天数
    :return: 一个包含日期和收盘价的字符串，或者在出错时返回None
    """
    try:
        if not ticker:
            return "错误：股票代码不能为空。"
        try:
            days = int(days)
        except Exception:
            return "错误：days 必须是正整数。"
        if days <= 0:
            return "错误：days 必须是正整数。"

        if ak is None:
            return "错误：未安装 akshare，请先安装：pip install akshare"

        display_ticker = _normalize_ticker(ticker)
        if "." not in display_ticker:
            return "错误：仅支持 A 股股票代码，例如 600519 或 600519.SS / 000001.SZ"

        cache_key = (display_ticker, days)
        cached = _CACHE.get(cache_key)
        now = time.time()
        if cached is not None and now - cached[0] <= _CACHE_TTL_SECONDS:
            return cached[1]

        code, suffix = display_ticker.split(".", 1)
        if suffix not in ("SS", "SZ", "BJ"):
            return "错误：仅支持 A 股股票代码，例如 600519 或 600519.SS / 000001.SZ"

        today = datetime.date.today()
        start = today - datetime.timedelta(days=max(60, days * 10))
        df = _silent_call(
            ak.stock_zh_a_hist,
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
            adjust="",
        )
        if df is None or df.empty:
            return f"错误：无法获取股票代码 {display_ticker} 的数据，请检查代码是否正确。"

        if "日期" not in df.columns or "收盘" not in df.columns:
            return f"错误：AkShare 返回字段缺失，无法解析 {display_ticker} 的收盘价。"

        df = df.tail(days)
        result = f"{display_ticker} 最近 {days} 天的收盘价：\n"
        for _, row in df.iterrows():
            date_str = str(row.get("日期"))
            close_val = row.get("收盘")
            try:
                result += f"{date_str}: {float(close_val):.2f}\n"
            except Exception:
                result += f"{date_str}: {close_val}\n"

        _CACHE[cache_key] = (now, result)
        return result

    except Exception as e:
        return f"错误：获取数据时发生异常 - {e}"

if __name__ == '__main__':
    # 这是一个测试代码块，当你直接运行此文件时会执行
    # 用于测试 get_stock_data 函数是否正常工作
    test_ticker = "AAPL"
    stock_data = get_stock_data(test_ticker)
    print(stock_data)

    test_invalid_ticker = "INVALIDTICKER"
    stock_data_invalid = get_stock_data(test_invalid_ticker)
    print(stock_data_invalid)
