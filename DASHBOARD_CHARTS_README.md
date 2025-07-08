# Dashboard Charts Feature

## Overview
The Dashboard Charts feature provides interactive, responsive analytics visualizations for your Tickzen stock analysis platform. It uses Chart.js for beautiful, mobile-friendly charts that display real-time data from your generated reports.

## Features

### 1. Reports Generated Over Time
- **Chart Type**: Line chart with area fill
- **Data**: Number of reports generated over time
- **Controls**: Toggle between daily, weekly, monthly, and quarterly views
- **Features**: 
  - Smooth animations
  - Interactive tooltips
  - Responsive design
  - Moving average trend line

### 2. Most Analyzed Tickers
- **Chart Type**: Horizontal bar chart
- **Data**: Top tickers by analysis count
- **Controls**: Toggle between Top 5, 10, or 15 tickers
- **Features**:
  - Color-coded by sector (Tech, Finance, Healthcare, etc.)
  - Click to view reports for specific tickers
  - Responsive bar heights

### 3. Publishing Status
- **Chart Type**: Pie/Doughnut chart (toggleable)
- **Data**: Breakdown of report publishing status
- **Controls**: Switch between pie, doughnut, and bar chart views
- **Features**:
  - Color-coded status (Published, Scheduled, Draft, Failed)
  - Percentage calculations
  - Interactive segments

### 4. Activity Heatmap
- **Chart Type**: GitHub-style calendar heatmap
- **Data**: Daily activity levels throughout the year
- **Controls**: Toggle between different years
- **Features**:
  - Color intensity based on activity level
  - Hover tooltips with exact counts
  - Click for detailed view

## Technical Implementation

### Backend (Python/Flask)
- **File**: `app/dashboard_analytics.py`
- **Data Source**: Scans generated report files in `app/static/stock_reports/`
- **API Endpoints**:
  - `/api/dashboard/stats` - Overall statistics
  - `/api/dashboard/reports-over-time` - Time series data
  - `/api/dashboard/most-analyzed` - Top tickers
  - `/api/dashboard/publishing-status` - Status breakdown
  - `/api/dashboard/activity-heatmap` - Calendar data

### Frontend (HTML/JavaScript)
- **File**: `app/templates/dashboard_charts.html`
- **Library**: Chart.js v4.x
- **Features**:
  - Responsive design for mobile/desktop
  - Real-time data fetching
  - Interactive controls
  - Smooth animations

## Installation & Setup

1. **Dependencies**: Chart.js is loaded via CDN, no additional installation needed
2. **Data**: Automatically scans existing report files
3. **Access**: Available via `/dashboard-charts` route
4. **Integration**: Added to main dashboard as "Dashboard Analytics" tool

## Usage

1. Navigate to your main dashboard
2. Click "Dashboard Analytics" in the tools section
3. Use the interactive controls to explore different views
4. Hover over charts for detailed information
5. Click on chart elements for additional actions

## Customization

### Adding New Charts
1. Create new API endpoint in `dashboard_analytics.py`
2. Add corresponding fetch function in the frontend
3. Create new chart container and initialization code

### Styling
- Colors are defined in CSS variables
- Chart.js themes can be customized
- Mobile responsiveness is built-in

### Data Sources
- Currently uses file system scanning
- Can be extended to use database queries
- Supports real-time updates via WebSocket

## Performance Considerations

- **Caching**: Data is cached for 5 minutes to reduce file system calls
- **Lazy Loading**: Charts load data on demand
- **Mobile Optimization**: Reduced chart heights on small screens
- **Error Handling**: Graceful fallbacks for missing data

## Future Enhancements

1. **Real-time Updates**: WebSocket integration for live data
2. **Export Features**: Download charts as PNG/PDF
3. **Advanced Filtering**: Date ranges, ticker filters
4. **Comparative Analytics**: Compare periods or tickers
5. **Custom Dashboards**: User-configurable layouts

## Troubleshooting

### Common Issues
1. **No data showing**: Check if report files exist in the correct directory
2. **Charts not loading**: Verify Chart.js CDN is accessible
3. **Mobile display issues**: Check responsive CSS classes

### Debug Mode
- Open browser console for detailed error messages
- Check Flask logs for backend errors
- Verify API endpoints return expected JSON format

## API Reference

### GET /api/dashboard/stats
Returns overall dashboard statistics.

**Response:**
```json
{
  "total_reports": 172,
  "this_month": 45,
  "published_reports": 156,
  "unique_tickers": 23
}
```

### GET /api/dashboard/reports-over-time?period=week
Returns time series data for reports.

**Parameters:**
- `period`: "week", "month", "quarter"

**Response:**
```json
{
  "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  "data": [5, 8, 12, 6, 9, 3, 7]
}
```

### GET /api/dashboard/most-analyzed?limit=5
Returns most analyzed tickers.

**Parameters:**
- `limit`: Number of tickers to return

**Response:**
```json
{
  "tickers": ["TSLA", "AAPL", "MSFT"],
  "counts": [45, 38, 32],
  "sectors": ["tech", "tech", "tech"]
}
```

### GET /api/dashboard/publishing-status
Returns publishing status breakdown.

**Response:**
```json
{
  "labels": ["Published", "Scheduled", "Draft", "Failed"],
  "data": [156, 12, 4, 2],
  "colors": ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"]
}
```

### GET /api/dashboard/activity-heatmap?year=2024
Returns activity heatmap data.

**Parameters:**
- `year`: Year for heatmap data

**Response:**
```json
{
  "2024-01-01": 5,
  "2024-01-02": 3,
  "2024-01-03": 0
}
``` 