# Traffic Manager — Google Ads API Tool Design Document

## 1. Company Overview

**Company Name:** Blossom Boost
**Website:** https://www.blossomboost.com.br/
**Industry:** Custom Software Development
**Location:** Brazil

Blossom Boost is a custom software development company that builds tailored software solutions for clients. We use Google Ads to run paid advertising campaigns to acquire new clients for our services.

## 2. Tool Overview

**Tool Name:** Traffic Manager
**Purpose:** Internal multi-platform ad campaign management tool
**Users:** Internal marketing team only (2-5 employees)
**Platforms Integrated:** Google Ads, Meta Ads, LinkedIn Ads

Traffic Manager is an internal tool that consolidates advertising data from multiple platforms (Google Ads, Meta Ads, LinkedIn Ads) into a single dashboard. It allows our marketing team to monitor campaign performance, manage campaign status, and generate cross-platform reports without switching between multiple ad platform interfaces.

## 3. Google Ads API Usage

### 3.1 Features Using the API

| Feature | API Resources Used | Read/Write |
|---------|-------------------|------------|
| Campaign data sync | GoogleAdsService (campaign, ad_group, ad_group_ad) | Read |
| Performance metrics | GoogleAdsService (metrics, segments) | Read |
| Campaign status management | CampaignService (mutate) | Write |
| Budget adjustments | CampaignBudgetService (mutate) | Write |
| Reporting | GoogleAdsService (search/searchStream) | Read |

### 3.2 API Operations

**Read Operations (Primary Use — ~90% of API calls):**
- Fetch campaign structures (campaigns, ad groups, ads)
- Pull daily performance metrics (impressions, clicks, spend, conversions, CTR, CPC, CPM, CPA, ROAS)
- Generate performance reports for date ranges

**Write Operations (~10% of API calls):**
- Update campaign status (ENABLED, PAUSED)
- Update campaign budget amounts

### 3.3 API Call Frequency
- Automated metrics sync: Every 6 hours (4 times per day)
- Manual data refresh: On-demand by team members (estimated 5-10 times per day)
- Campaign updates: Occasional (estimated 2-5 per week)
- Total estimated daily API calls: Under 1,000

## 4. Technical Architecture

### 4.1 System Diagram

```
+------------------+     +-------------------+     +----------------+
|                  |     |                   |     |                |
|  Google Ads API  |<--->|  Traffic Manager   |<--->|  SQLite DB     |
|                  |     |  (Python/FastAPI)  |     |  (Local)       |
+------------------+     |                   |     +----------------+
                         |  Connectors:      |
+------------------+     |  - Google Ads     |     +----------------+
|  Meta Ads API    |<--->|  - Meta           |<--->|  React         |
+------------------+     |  - LinkedIn       |     |  Dashboard     |
                         |                   |     |  (Frontend)    |
+------------------+     +-------------------+     +----------------+
|  LinkedIn API    |<--->|                   |
+------------------+     +-------------------+
```

### 4.2 Technology Stack
- **Backend:** Python 3.12, FastAPI
- **Google Ads SDK:** google-ads Python client library (v29+)
- **Database:** SQLite (local storage for metrics history)
- **Frontend:** React (dashboard for data visualization)
- **Authentication:** OAuth 2.0 (Desktop application flow)

### 4.3 Data Flow

1. **Sync Process:** Scheduled job connects to Google Ads API via `google-ads` Python SDK
2. **Data Retrieval:** Uses GoogleAdsService.SearchStream to fetch campaign data and metrics
3. **Normalization:** Campaign data is normalized into a unified schema (shared with Meta and LinkedIn data)
4. **Storage:** Normalized data is stored in local SQLite database
5. **Display:** React dashboard reads from the API and displays consolidated metrics
6. **Actions:** Campaign status changes and budget updates are sent back to Google Ads API via CampaignService.Mutate

### 4.4 Authentication Flow
- OAuth 2.0 Desktop Application flow
- Refresh token stored securely in environment variables
- Access tokens refreshed automatically by the google-ads SDK
- Single Google Ads account (Customer ID: 743-337-0539) managed through MCC (207-592-5672)

## 5. Data Handling

### 5.1 Data Stored
- Campaign metadata (name, status, objective, budget)
- Ad group metadata (name, status, targeting)
- Ad metadata (name, status, creative info)
- Daily performance metrics (impressions, clicks, spend, conversions, revenue)
- Calculated metrics (CTR, CPC, CPM, CPA, ROAS)

### 5.2 Data Retention
- Performance metrics: Retained for 180 days for trend analysis
- Campaign metadata: Updated on each sync, current state only

### 5.3 Data Security
- All credentials stored in environment variables (never in code)
- Application runs on internal infrastructure only
- No data shared with third parties
- SQLite database stored locally with filesystem permissions

## 6. Compliance

- The tool is used exclusively by Blossom Boost internal employees
- No customer data from Google Ads end users is collected or stored
- The tool does not resell or redistribute Google Ads data
- All API usage complies with Google Ads API Terms and Conditions
- API contact email is monitored and kept up-to-date

## 7. Rate Limiting and Error Handling

- API calls are batched and throttled to stay within rate limits
- Exponential backoff retry logic for transient errors
- Failed syncs are logged with error details for debugging
- Metrics sync runs on a fixed schedule (every 6 hours) to avoid excessive API calls

## 8. Screenshots

The tool is currently in development (Phase 0). The dashboard will display:
- Campaign performance overview (spend, conversions, CPA, ROAS)
- Cross-platform comparison charts (Google Ads vs Meta vs LinkedIn)
- Campaign status management interface
- Automated alert notifications for performance anomalies
