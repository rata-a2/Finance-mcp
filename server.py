"""Finance MCP Server - Stock prices, news, and financial data."""

import json
import os
from datetime import datetime, timedelta

import finnhub
import requests
import yfinance as yf
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(
    "Finance",
    instructions="Stock prices, financial data, news, and EDINET reports for AI assistants.",
)

# --- Finnhub client ---
_finnhub_client = None


def _get_finnhub() -> finnhub.Client:
    global _finnhub_client
    if _finnhub_client is None:
        key = os.getenv("FINNHUB_API_KEY", "")
        if not key:
            raise ValueError(
                "FINNHUB_API_KEY is not set. "
                "Get a free key at https://finnhub.io/register"
            )
        _finnhub_client = finnhub.Client(api_key=key)
    return _finnhub_client


def _edinet_key() -> str:
    key = os.getenv("EDINET_API_KEY", "")
    if not key:
        raise ValueError(
            "EDINET_API_KEY is not set. "
            "Register at https://disclosure.edinet-fsa.go.jp/"
        )
    return key


# ============================================================
# Stock Price & Market Data (yfinance)
# ============================================================


@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """Get the current stock price, change, and volume.

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "7203.T" for Toyota on TSE)
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            hist = ticker.history(period="5d")
            if hist.empty:
                return json.dumps({"error": f"No data found for symbol: {symbol}"})
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]
            price = float(last["Close"])
            change = price - float(prev["Close"])
            return json.dumps({
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change / float(prev["Close"]) * 100, 2),
                "volume": int(last["Volume"]),
                "date": str(last.name.date()),
                "source": "yfinance (history fallback)",
            })

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change = (price - prev_close) if price and prev_close else None

        return json.dumps({
            "symbol": symbol,
            "name": info.get("shortName", ""),
            "price": price,
            "currency": info.get("currency", ""),
            "change": round(change, 2) if change else None,
            "change_percent": round(change / prev_close * 100, 2) if change and prev_close else None,
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "volume": info.get("volume"),
            "market_cap": info.get("marketCap"),
            "exchange": info.get("exchange", ""),
            "source": "yfinance",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


@mcp.tool()
def get_stock_history(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
) -> str:
    """Get historical stock price data.

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "7203.T")
        period: Data period - 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
        interval: Data interval - 1m, 5m, 15m, 1h, 1d, 1wk, 1mo
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return json.dumps({"error": f"No history for {symbol}"})

        records = []
        for idx, row in hist.iterrows():
            records.append({
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        # Limit to 60 records to avoid huge responses
        if len(records) > 60:
            records = records[-60:]

        return json.dumps({
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "count": len(records),
            "data": records,
            "source": "yfinance",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


@mcp.tool()
def get_company_info(symbol: str) -> str:
    """Get company profile information.

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "7203.T")
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or "shortName" not in info:
            return json.dumps({"error": f"No info found for {symbol}"})

        return json.dumps({
            "symbol": symbol,
            "name": info.get("shortName", ""),
            "long_name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", ""),
            "website": info.get("website", ""),
            "summary": info.get("longBusinessSummary", "")[:500],
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "employees": info.get("fullTimeEmployees"),
            "currency": info.get("currency", ""),
            "exchange": info.get("exchange", ""),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "source": "yfinance",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


# ============================================================
# Financial Statements (yfinance)
# ============================================================


@mcp.tool()
def get_financial_statements(
    symbol: str,
    statement_type: str = "income",
) -> str:
    """Get financial statements (income statement, balance sheet, or cash flow).

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "7203.T")
        statement_type: Type of statement - "income", "balance", or "cashflow"
    """
    try:
        ticker = yf.Ticker(symbol)

        if statement_type == "income":
            df = ticker.financials
            label = "Income Statement"
        elif statement_type == "balance":
            df = ticker.balance_sheet
            label = "Balance Sheet"
        elif statement_type == "cashflow":
            df = ticker.cashflow
            label = "Cash Flow Statement"
        else:
            return json.dumps({"error": f"Invalid statement_type: {statement_type}. Use income, balance, or cashflow."})

        if df is None or df.empty:
            return json.dumps({"error": f"No {label} data for {symbol}"})

        # Convert DataFrame: columns are dates, rows are line items
        result = {}
        for col in df.columns:
            period_key = str(col.date()) if hasattr(col, "date") else str(col)
            period_data = {}
            for item_name, value in df[col].items():
                if value is not None and str(value) != "nan":
                    try:
                        period_data[str(item_name)] = float(value)
                    except (ValueError, TypeError):
                        period_data[str(item_name)] = str(value)
            result[period_key] = period_data

        return json.dumps({
            "symbol": symbol,
            "statement": label,
            "periods": result,
            "source": "yfinance",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


# ============================================================
# Basic Financials (Finnhub)
# ============================================================


@mcp.tool()
def get_basic_financials(symbol: str) -> str:
    """Get key financial metrics (PE, PB, ROE, dividend yield, etc.) from Finnhub.

    Args:
        symbol: Ticker symbol (e.g. "AAPL" — US stocks only for Finnhub)
    """
    try:
        client = _get_finnhub()
        data = client.company_basic_financials(symbol, "all")

        if not data or not data.get("metric"):
            return json.dumps({"error": f"No financial metrics for {symbol}"})

        m = data["metric"]
        return json.dumps({
            "symbol": symbol,
            "pe_ratio": m.get("peTTM"),
            "pb_ratio": m.get("pbQuarterly"),
            "ps_ratio": m.get("psTTM"),
            "roe": m.get("roeTTM"),
            "roa": m.get("roaTTM"),
            "current_ratio": m.get("currentRatioQuarterly"),
            "debt_to_equity": m.get("totalDebt/totalEquityQuarterly"),
            "dividend_yield_indicated": m.get("dividendYieldIndicatedAnnual"),
            "eps_ttm": m.get("epsTTM"),
            "revenue_growth_3y": m.get("revenueGrowth3Y"),
            "net_margin": m.get("netProfitMarginTTM"),
            "gross_margin": m.get("grossMarginTTM"),
            "52w_high": m.get("52WeekHigh"),
            "52w_low": m.get("52WeekLow"),
            "52w_high_date": m.get("52WeekHighDate"),
            "52w_low_date": m.get("52WeekLowDate"),
            "beta": m.get("beta"),
            "10d_avg_volume": m.get("10DayAverageTradingVolume"),
            "source": "finnhub",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


# ============================================================
# News (Finnhub)
# ============================================================


@mcp.tool()
def get_company_news(
    symbol: str,
    from_date: str = "",
    to_date: str = "",
) -> str:
    """Get recent news articles for a specific company.

    Args:
        symbol: Ticker symbol (e.g. "AAPL")
        from_date: Start date in YYYY-MM-DD (default: 7 days ago)
        to_date: End date in YYYY-MM-DD (default: today)
    """
    try:
        client = _get_finnhub()
        today = datetime.now()
        if not to_date:
            to_date = today.strftime("%Y-%m-%d")
        if not from_date:
            from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")

        news = client.company_news(symbol, _from=from_date, to=to_date)

        if not news:
            return json.dumps({"symbol": symbol, "count": 0, "articles": []})

        articles = []
        for item in news[:20]:
            articles.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", "")[:200],
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "datetime": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%d %H:%M"),
                "category": item.get("category", ""),
            })

        return json.dumps({
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "count": len(articles),
            "articles": articles,
            "source": "finnhub",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


@mcp.tool()
def get_market_news(category: str = "general") -> str:
    """Get general market news.

    Args:
        category: News category - "general", "forex", "crypto", "merger"
    """
    try:
        client = _get_finnhub()
        news = client.general_news(category, min_id=0)

        if not news:
            return json.dumps({"category": category, "count": 0, "articles": []})

        articles = []
        for item in news[:15]:
            articles.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", "")[:200],
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "datetime": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%d %H:%M"),
                "category": item.get("category", ""),
            })

        return json.dumps({
            "category": category,
            "count": len(articles),
            "articles": articles,
            "source": "finnhub",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================
# EDINET (Japanese company filings)
# ============================================================

EDINET_BASE = "https://disclosure.edinet-fsa.go.jp/api/v2"

# Document type codes
DOC_TYPES = {
    "120": "有価証券報告書",
    "130": "半期報告書",
    "140": "四半期報告書",
    "150": "臨時報告書",
    "160": "有価証券届出書",
}


@mcp.tool()
def search_edinet_documents(
    date: str,
    doc_type: str = "",
    company_name: str = "",
) -> str:
    """Search EDINET for submitted financial documents on a specific date.

    Args:
        date: Target date in YYYY-MM-DD format
        doc_type: Document type code filter (120=有価証券報告書, 140=四半期報告書, empty=all)
        company_name: Filter by company name (partial match, Japanese)
    """
    try:
        key = _edinet_key()
        url = f"{EDINET_BASE}/documents.json"
        params = {
            "date": date,
            "type": 2,  # include metadata
            "Subscription-Key": key,
        }

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results_list = data.get("results", [])
        documents = []

        for doc in results_list:
            # Filter by doc type if specified
            if doc_type and doc.get("docTypeCode") != doc_type:
                continue
            # Filter by company name if specified
            if company_name and company_name not in (doc.get("filerName") or ""):
                continue
            # Skip if no docID
            if not doc.get("docID"):
                continue

            documents.append({
                "doc_id": doc.get("docID"),
                "company_name": doc.get("filerName", ""),
                "edinet_code": doc.get("edinetCode", ""),
                "sec_code": doc.get("secCode", ""),
                "doc_type_code": doc.get("docTypeCode", ""),
                "doc_type_name": DOC_TYPES.get(doc.get("docTypeCode", ""), doc.get("docTypeCode", "")),
                "doc_description": doc.get("docDescription", ""),
                "submit_datetime": doc.get("submitDateTime", ""),
                "period_start": doc.get("periodStart", ""),
                "period_end": doc.get("periodEnd", ""),
            })

        # Limit results
        if len(documents) > 50:
            documents = documents[:50]

        return json.dumps({
            "date": date,
            "total_found": len(documents),
            "filters": {"doc_type": doc_type or "all", "company_name": company_name or "all"},
            "documents": documents,
            "source": "EDINET",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def get_edinet_document_info(doc_id: str) -> str:
    """Get detailed metadata for a specific EDINET document.

    Args:
        doc_id: EDINET document ID (e.g. "S100XXXX")
    """
    try:
        key = _edinet_key()

        # We need to search recent dates to find the document
        # Try fetching document directly with type=2 (metadata only)
        url = f"{EDINET_BASE}/documents/{doc_id}"
        params = {
            "type": 2,  # document info
            "Subscription-Key": key,
        }

        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "")
            if "json" in content_type:
                return json.dumps(resp.json(), ensure_ascii=False)
            else:
                return json.dumps({
                    "doc_id": doc_id,
                    "status": "Document exists",
                    "note": "Use search_edinet_documents to find metadata, then get_edinet_financial_data to download.",
                }, ensure_ascii=False)
        else:
            return json.dumps({"error": f"Document {doc_id} not found (HTTP {resp.status_code})"})
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def get_edinet_financial_data(doc_id: str) -> str:
    """Download and extract financial data from an EDINET document (CSV format).

    Args:
        doc_id: EDINET document ID (e.g. "S100XXXX")
    """
    import csv
    import io
    import tempfile
    import zipfile

    try:
        key = _edinet_key()
        url = f"{EDINET_BASE}/documents/{doc_id}"
        params = {
            "type": 5,  # CSV format
            "Subscription-Key": key,
        }

        resp = requests.get(url, params=params, timeout=30)

        if resp.status_code != 200:
            return json.dumps({
                "error": f"Failed to download document {doc_id} (HTTP {resp.status_code})",
                "hint": "Ensure the doc_id is correct and the document has CSV data available.",
            }, ensure_ascii=False)

        # Extract ZIP contents
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "doc.zip")
            with open(zip_path, "wb") as f:
                f.write(resp.content)

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    csv_files = [n for n in zf.namelist() if n.endswith(".csv")]

                    if not csv_files:
                        return json.dumps({
                            "doc_id": doc_id,
                            "error": "No CSV files found in the ZIP archive",
                            "files_in_zip": zf.namelist()[:20],
                        }, ensure_ascii=False)

                    # Parse the main financial CSV file
                    financial_data = {}
                    for csv_file in csv_files[:5]:  # Limit to first 5 CSV files
                        content = zf.read(csv_file).decode("utf-8", errors="replace")
                        reader = csv.reader(io.StringIO(content))
                        rows = list(reader)

                        if len(rows) > 1:
                            headers = rows[0] if rows else []
                            data_rows = rows[1:100]  # Limit rows
                            financial_data[csv_file] = {
                                "headers": headers,
                                "row_count": len(rows) - 1,
                                "sample_data": data_rows[:20],
                            }

                    return json.dumps({
                        "doc_id": doc_id,
                        "csv_files_count": len(csv_files),
                        "parsed_files": financial_data,
                        "source": "EDINET",
                    }, ensure_ascii=False)

            except zipfile.BadZipFile:
                return json.dumps({
                    "error": f"Document {doc_id} did not return a valid ZIP file",
                    "content_type": resp.headers.get("Content-Type", ""),
                }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
