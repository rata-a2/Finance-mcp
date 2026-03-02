# Finance MCP Server

An MCP (Model Context Protocol) server that provides financial data to Claude Code and other MCP-compatible AI assistants.

Supports **US stocks**, **Japanese stocks (TSE)**, and **EDINET filings**.

## Features

| Tool | Description | Source |
|------|-------------|--------|
| `get_stock_price` | Current stock price, change, volume | yfinance |
| `get_stock_history` | Historical OHLCV data | yfinance |
| `get_company_info` | Company profile & summary | yfinance |
| `get_financial_statements` | Income statement / Balance sheet / Cash flow | yfinance |
| `get_basic_financials` | Key metrics (PE, PB, ROE, etc.) | Finnhub |
| `get_company_news` | Company-specific news articles | Finnhub |
| `get_market_news` | General market news | Finnhub |
| `search_edinet_documents` | Search EDINET filings by date | EDINET |
| `get_edinet_document_info` | EDINET document metadata | EDINET |
| `get_edinet_financial_data` | Download & parse EDINET CSV data | EDINET |

## Data Sources

| API | What it provides | Auth | Rate Limit |
|-----|------------------|------|------------|
| **[yfinance](https://github.com/ranaroussi/yfinance)** | Stock prices, company info, financial statements | None required | Unofficial (may throttle) |
| **[Finnhub](https://finnhub.io/)** | News, financial metrics | Free API key | 60 calls/min |
| **[EDINET](https://disclosure.edinet-fsa.go.jp/)** | Japanese company filings | Free API key | Not specified |

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rata-a2/Finance-MCP.git
cd Finance-MCP
pip install -e .
```

### 2. Get API Keys (free)

- **Finnhub**: Sign up at [finnhub.io/register](https://finnhub.io/register)
- **EDINET**: Register at [disclosure.edinet-fsa.go.jp](https://disclosure.edinet-fsa.go.jp/)

> Note: yfinance tools work without any API key.

### 3. Configure Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "finance": {
      "command": "python",
      "args": ["/path/to/Finance-MCP/run_server.py"],
      "env": {
        "FINNHUB_API_KEY": "your_finnhub_key",
        "EDINET_API_KEY": "your_edinet_key"
      }
    }
  }
}
```

Or create a `.env` file in the project root (see `.env.example`).

## Usage Examples

```
# US stock price
get_stock_price("AAPL")

# Japanese stock (Tokyo Stock Exchange)
get_stock_price("7203.T")       # Toyota
get_stock_price("6758.T")       # Sony

# Historical data
get_stock_history("MSFT", period="3mo", interval="1d")

# Company news
get_company_news("AAPL", from_date="2025-01-01", to_date="2025-01-31")

# Financial statements
get_financial_statements("GOOGL", statement_type="income")

# Key financial metrics
get_basic_financials("AAPL")

# EDINET (Japanese filings)
search_edinet_documents("2025-03-01", doc_type="120")
```

## Requirements

- Python 3.11+
- Dependencies: `mcp[cli]`, `yfinance`, `finnhub-python`, `requests`, `python-dotenv`

## License

MIT
