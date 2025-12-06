# Earnings Report Pipeline

A comprehensive system for collecting, processing, and generating professional earnings reports using data from yfinance, Alpha Vantage, and Finnhub APIs.

## Overview

The Earnings Report Pipeline automatically collects financial data from multiple sources, processes and normalizes it, and generates professional HTML reports for both pre-earnings (preview) and post-earnings (analysis) scenarios.

## Features

- **Multi-Source Data Collection**: Aggregates data from yfinance, Alpha Vantage, and Finnhub
- **Comprehensive Coverage**: Collects 100+ data points across all financial statement categories
- **Data Normalization**: Intelligently merges and prioritizes data from multiple sources
- **Automatic Calculations**: Computes financial ratios and derived metrics
- **Data Quality Validation**: Scores data completeness and identifies missing fields
- **Professional Reports**: Generates beautiful, responsive HTML reports
- **Caching System**: Smart caching to reduce API calls and improve performance
- **Batch Processing**: Process multiple tickers efficiently
- **Flexible API**: Easy-to-use Python interface

## Installation

### Prerequisites

```bash
# Install required packages (already in requirements.txt)
pip install yfinance finnhub-python requests pandas numpy
```

### API Keys

Set up your API keys as environment variables:

```bash
# Windows PowerShell
$env:FINNHUB_API_KEY = "your_finnhub_api_key"
$env:ALPHA_API_KEY = "your_alpha_vantage_api_key"

# Linux/Mac
export FINNHUB_API_KEY="your_finnhub_api_key"
export ALPHA_API_KEY="your_alpha_vantage_api_key"
```

Or create a `.env` file in your project root:

```
FINNHUB_API_KEY=your_finnhub_api_key
ALPHA_API_KEY=your_alpha_vantage_api_key
```

## Quick Start

### Simple Usage

```python
from earnings_reports import quick_generate

# Generate both pre and post earnings reports
result = quick_generate('AAPL', report_type='both')

if result['overall_success']:
    print(f"Reports generated successfully!")
    print(f"Pre-earnings: {result['pre_earnings']['report_path']}")
    print(f"Post-earnings: {result['post_earnings']['report_path']}")
```

### Using the Pipeline

```python
from earnings_reports import EarningsPipeline

# Initialize pipeline
pipeline = EarningsPipeline(log_level='INFO')

# Generate pre-earnings report
result = pipeline.generate_pre_earnings_report('MSFT')

# Generate post-earnings report
result = pipeline.generate_post_earnings_report('GOOGL')

# Get data without generating report
data = pipeline.get_data_only('TSLA')
```

## Data Coverage

The pipeline collects all required data points organized into categories:

### Company Identification (6 fields)
- ticker, company_name, cik, exchange, sector, market_cap

### Earnings Timeline (6 fields)
- earnings_date, fiscal_quarter, fiscal_year, filing_date, period_end_date, filing_type

### Income Statement (16 fields)
- total_revenue, cost_of_revenue, gross_profit, operating_income, net_income, earnings_per_share_basic, earnings_per_share_diluted, research_and_development, sales_and_marketing, general_and_administrative, depreciation_and_amortization, interest_expense, tax_provision, stock_based_compensation, weighted_average_shares_basic, weighted_average_shares_diluted

### Balance Sheet (16 fields)
- total_assets, current_assets, cash_and_equivalents, accounts_receivable, inventory, property_plant_equipment, goodwill, intangible_assets, total_liabilities, current_liabilities, accounts_payable, long_term_debt, total_debt, stockholders_equity, retained_earnings, working_capital

### Cash Flow Statement (7 fields)
- operating_cash_flow, net_cash_investing, net_cash_financing, free_cash_flow, capital_expenditures, dividends_paid, share_repurchases

### Analyst Estimates (6 fields)
- estimated_revenue, estimated_eps, estimate_high, estimate_low, number_of_analysts, estimate_year_ago

### Actual vs Estimate (4 fields)
- revenue_surprise, eps_surprise, revenue_actual, eps_actual

### Stock Price Data (11 fields)
- price, open, high, low, close, volume, price_change, price_change_percent, 52_week_high, 52_week_low

### Forward Guidance (5 fields)
- guidance_revenue_low, guidance_revenue_high, guidance_eps_low, guidance_eps_high, next_year_estimate

### Calculated Ratios (8 fields)
- profit_margin, operating_margin, gross_margin, return_on_equity, return_on_assets, debt_to_equity, current_ratio, pe_ratio

**Total: 85+ individual data points**

## Architecture

### Module Structure

```
earnings_reports/
├── __init__.py              # Package initialization
├── earnings_config.py       # Configuration settings
├── data_collector.py        # Multi-source data collection
├── data_processor.py        # Data normalization & processing
├── report_generator.py      # HTML report generation
├── pipeline.py              # Main orchestrator
├── utils.py                 # Helper utilities
├── examples.py              # Usage examples
└── README.md               # This file
```

### Data Flow

```
1. Data Collection (data_collector.py)
   ├── yfinance API
   ├── Alpha Vantage API
   └── Finnhub API
   
2. Data Processing (data_processor.py)
   ├── Normalize formats
   ├── Merge from multiple sources
   ├── Calculate derived metrics
   └── Validate quality
   
3. Report Generation (report_generator.py)
   ├── Pre-earnings preview
   └── Post-earnings analysis
```

## Advanced Usage

### Custom Configuration

```python
from earnings_reports import EarningsPipeline, EarningsConfig

# Create custom config
config = EarningsConfig()
config.CACHE_EXPIRY_HOURS = 12
config.MAX_RETRIES = 5
config.RATE_LIMIT_DELAY = 2.0

# Use custom config
pipeline = EarningsPipeline(config=config)
```

### Batch Processing

```python
from earnings_reports import EarningsPipeline

pipeline = EarningsPipeline()

tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

results = pipeline.batch_generate_reports(
    tickers=tickers,
    report_type='both',  # or 'pre' or 'post'
    use_cache=True,
    save_reports=True
)

# Check results
for result in results:
    if result.get('overall_success'):
        print(f"✓ {result['ticker']}")
    else:
        print(f"✗ {result['ticker']}: {result.get('error')}")
```

### Data Quality Check

```python
from earnings_reports import EarningsPipeline

pipeline = EarningsPipeline()

quality_report = pipeline.validate_and_report_data_quality('AAPL')

print(f"Completeness: {quality_report['completeness_score']}%")
print(f"Recommendation: {quality_report['recommendation']}")
print(f"Missing fields: {quality_report['missing_critical_fields']}")
```

### Data Only (No Report)

```python
from earnings_reports import EarningsPipeline

pipeline = EarningsPipeline()

result = pipeline.get_data_only('MSFT', use_cache=True)

if result['success']:
    data = result['data']
    summary = result['summary']
    
    # Use the data for custom processing
    earnings_data = data['earnings_data']
    income_statement = earnings_data['income_statement']
    balance_sheet = earnings_data['balance_sheet']
    # ... etc
```

## Configuration Options

### EarningsConfig Class

```python
# Cache settings
CACHE_DIR = 'generated_data/earnings_cache'
CACHE_EXPIRY_HOURS = 6

# Report output
REPORTS_DIR = 'generated_data/earnings_reports'

# API settings
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 1.0
```

## Report Examples

### Pre-Earnings Report Includes:
- Analyst consensus estimates
- EPS and revenue expectations
- Current stock performance
- Recent financial performance
- Forward guidance
- Key metrics to watch
- Company overview

### Post-Earnings Report Includes:
- Actual vs estimate comparison
- Complete income statement
- Balance sheet snapshot
- Cash flow statement
- Key financial ratios
- Stock performance
- Forward guidance
- Data quality metrics

## Cache Management

```python
from earnings_reports.utils import estimate_cache_size, clear_old_cache

# Check cache size
cache_info = estimate_cache_size('generated_data/earnings_cache')
print(f"Cache: {cache_info['count']} files, {cache_info['size_mb']} MB")

# Clear old cache files (older than 7 days)
clear_old_cache('generated_data/earnings_cache', days_old=7)
```

## API Rate Limits

### Default Rate Limits:
- **yfinance**: No official limit, but use responsibly
- **Alpha Vantage**: 25 calls/day (free tier), 500 calls/day (premium)
- **Finnhub**: 60 calls/minute (free tier)

### Rate Limiting Strategy:
- Automatic rate limiting with configurable delays
- Smart caching to minimize API calls
- Fallback to cached data when limits reached

## Error Handling

The pipeline includes comprehensive error handling:

```python
result = pipeline.generate_pre_earnings_report('INVALID')

if not result['success']:
    print(f"Error: {result['error']}")
    print(f"Ticker: {result['ticker']}")
```

## Logging

```python
from earnings_reports import EarningsPipeline

# Set log level
pipeline = EarningsPipeline(log_level='DEBUG')  # DEBUG, INFO, WARNING, ERROR

# Or use utility
from earnings_reports.utils import setup_logging
setup_logging(log_level='INFO', log_file='logs/earnings_pipeline.log')
```

## Testing

Run the examples to test the pipeline:

```python
# Run all examples
python earnings_reports/examples.py

# Run specific example
python earnings_reports/examples.py 1  # Simple report
python earnings_reports/examples.py 4  # Data quality check
```

## Troubleshooting

### Common Issues:

1. **Missing API Keys**
   ```python
   from earnings_reports.utils import check_api_credentials
   credentials = check_api_credentials()
   print(credentials)  # Shows which APIs are configured
   ```

2. **API Rate Limits**
   - Use caching: `use_cache=True`
   - Increase `CACHE_EXPIRY_HOURS`
   - Reduce `RATE_LIMIT_DELAY` cautiously

3. **Missing Data**
   ```python
   # Check data quality
   quality = pipeline.validate_and_report_data_quality('TICKER')
   print(quality['missing_critical_fields'])
   ```

4. **Network Issues**
   - Increase `REQUEST_TIMEOUT` in config
   - Increase `MAX_RETRIES`

## Integration with Existing Systems

### With Automation Scripts

```python
# In your automation script
from earnings_reports import EarningsPipeline

pipeline = EarningsPipeline()

# Generate report as part of your workflow
result = pipeline.generate_post_earnings_report(ticker)

if result['success']:
    # Continue with your automation
    html_content = result['html_content']
    # Post to WordPress, send email, etc.
```

### With Gemini Article System

```python
from earnings_reports import EarningsPipeline
from gemini_article_system import GeminiArticleGenerator

# Get earnings data
pipeline = EarningsPipeline()
data_result = pipeline.get_data_only('AAPL')

# Use with Gemini for enhanced articles
if data_result['success']:
    earnings_summary = data_result['summary']
    # Pass to Gemini for AI-enhanced content
```

## Performance

- **Single ticker**: 10-30 seconds (without cache)
- **Single ticker**: 1-2 seconds (with cache)
- **Batch (10 tickers)**: 2-5 minutes (without cache)
- **Report generation**: < 1 second

## Future Enhancements

- [ ] PDF report generation
- [ ] Email delivery integration
- [ ] Scheduled earnings calendar monitoring
- [ ] Comparison with peer companies
- [ ] Historical earnings trend analysis
- [ ] Integration with charting libraries
- [ ] Custom report templates
- [ ] Database storage for historical data

## Contributing

This is part of the Tickzen project. To contribute:
1. Follow existing code structure
2. Add logging for debugging
3. Include error handling
4. Update this README for new features

## License

Part of the Tickzen project.

## Support

For issues or questions:
1. Check the examples in `examples.py`
2. Review the inline documentation
3. Check logs for detailed error messages

## Version History

- **v1.0.0** (November 2025)
  - Initial release
  - Multi-source data collection
  - Pre and post earnings reports
  - Comprehensive data coverage (85+ fields)
  - Smart caching system
  - Batch processing
  - Data quality validation
