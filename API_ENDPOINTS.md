# API Endpoints Reference

**Base URL**: `https://job-crawler-api-0885.onrender.com`

## Health & System

| Endpoint | Method | Use |
|----------|--------|-----|
| `/health` | GET | Check if API is running |
| `/api/system/status` | GET | Get system status and info |
| `/api/system/stats` | GET | Get total counts (jobs, results, admit cards) |
| `/api/system/stats/by-portal` | GET | Get stats broken down by portal |

## Jobs

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/jobs` | GET | List all jobs (paginated) |
| `/api/jobs/{id}` | GET | Get single job by ID |
| `/api/jobs/search` | GET | Search jobs by title, portal, date |
| `/api/jobs/filter` | GET | Filter jobs by date range or portal |
| `/api/jobs/filter/with-details` | GET | Filter jobs with full details included |

**Query Parameters**: `page`, `limit`, `portal`, `sort`, `date_from`, `date_to`

## Results (Exam)

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/results` | GET | List all exam results (paginated) |
| `/api/results/{id}` | GET | Get single result by ID |
| `/api/results/search` | GET | Search results by title, portal, date |
| `/api/results/filter` | GET | Filter results by date range or portal |
| `/api/results/filter/with-details` | GET | Filter results with full details included |

## Admit Cards

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/admit-cards` | GET | List all admit cards (paginated) |
| `/api/admit-cards/{id}` | GET | Get single admit card by ID |
| `/api/admit-cards/search` | GET | Search admit cards by title, portal, date |
| `/api/admit-cards/filter` | GET | Filter admit cards by date range or portal |
| `/api/admit-cards/filter/with-details` | GET | Filter admit cards with full details included |

## Detail Extraction (Real-Time URL Crawling)

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/details/fetch` | GET | Fetch complete details from a URL (query params) |
| `/api/details/fetch` | POST | Fetch complete details from a URL (JSON body) |
| `/api/details/batch` | POST | Fetch details from multiple URLs at once |

**Parameters**:
- `url` (required): Full URL to crawl
- `content_type` (optional): "job", "result", "admit_card", or "auto" (default: "auto")
- `timeout` (optional): Request timeout in seconds (default: 30)

**Example**:
```bash
# GET with query params
curl "https://job-crawler-api-0885.onrender.com/api/details/fetch?url=https://sarkariresult.com.cm/upsssc-lekhpal-recruitment-2026&content_type=job"

# POST with JSON
curl -X POST https://job-crawler-api-0885.onrender.com/api/details/fetch \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/job","content_type":"auto"}'
```

## Data Refresh

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/refresh/info` | GET | Get last refresh time and next scheduled refresh |
| `/api/refresh/now` | POST | Trigger immediate data refresh |
| `/api/refresh/status` | GET | Get current refresh status |
| `/api/refresh/reset` | POST | Reset refresh scheduler |

## Response Format

All endpoints return JSON with this structure:
```json
{
  "success": true,
  "data": [...],
  "message": "Description",
  "timestamp": "2026-01-15T10:30:00Z"
}
```

For detail extraction:
```json
{
  "success": true,
  "url": "https://example.com",
  "content_type": "job",
  "details": {
    "full_description": "...",
    "important_dates": {...},
    "eligibility": "...",
    "application_fee": "...",
    "how_to_apply": "...",
    "important_links": [...],
    "key_details": {...},
    "tables": [...]
  },
  "message": "Details fetched successfully"
}
```

## Common Query Parameters

| Parameter | Use |
|-----------|-----|
| `page` | Page number (default: 1) |
| `limit` | Items per page (default: 10, max: 100) |
| `sort` | Sort by field (e.g., "date_desc", "date_asc") |
| `portal` | Filter by portal name |
| `search` | Search keyword in title |
| `date_from` | Filter from date (YYYY-MM-DD) |
| `date_to` | Filter to date (YYYY-MM-DD) |

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request / invalid parameters |
| 404 | Resource not found |
| 500 | Server error |
| 503 | Service unavailable |
