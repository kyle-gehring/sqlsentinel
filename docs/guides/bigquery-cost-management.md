# BigQuery Cost Management Guide

This guide helps you understand and optimize BigQuery query costs when using SQL Sentinel.

## Understanding BigQuery Costs

### Pricing Model

BigQuery charges for:
1. **Query costs** - Based on data processed (scanned)
2. **Storage costs** - Based on data stored (not relevant for SQL Sentinel)
3. **Streaming inserts** - Not used by SQL Sentinel

**SQL Sentinel only incurs query costs.**

### Query Pricing

- **$5 per TB** of data processed
- **First 1 TB per month is FREE**
- Only scanned data counts (not result size)

### Cost Examples

| Data Scanned | Monthly Queries | Cost/Query | Monthly Cost |
|--------------|-----------------|------------|--------------|
| 1 GB | 1000 | $0.005 | $5.00 |
| 100 MB | 10,000 | $0.0005 | $5.00 |
| 10 MB | 100,000 | $0.00005 | $5.00 |
| 1 MB | 1,000,000 | $0.000005 | $5.00 |

**Note:** 1 TB free tier means first ~205,000 queries scanning 5 GB each are FREE.

## Estimating Query Costs

### Using Dry-Run (Recommended)

SQL Sentinel's BigQuery adapter supports dry-run to estimate costs before execution:

```python
from sqlsentinel.database.bigquery_adapter import BigQueryAdapter

adapter = BigQueryAdapter(project_id="my-project")
adapter.connect()

# Dry-run (doesn't execute, only estimates)
result = adapter.dry_run("""
    SELECT *
    FROM `my-project.analytics.large_table`
    WHERE date >= '2024-01-01'
""")

print(f"Bytes to process: {result['bytes_processed']:,}")
print(f"TB to process: {result['tb_processed']:.4f}")
print(f"Estimated cost: ${result['estimated_cost_usd']:.4f}")
```

**Output:**
```
Bytes to process: 5,368,709,120
TB to process: 0.0050
Estimated cost: $0.0000  # Within free tier
```

### Using BigQuery Console

1. Write your query in BigQuery Console
2. Look for the query validator message:
   - "This query will process X GB when run"
3. Calculate: `Cost = (X GB / 1024) * $5`

### Monthly Cost Estimation

```
Monthly Cost = (Queries per Month) × (GB per Query) / 1024 × $5
```

**Example:**
- 10,000 queries/month
- 100 MB per query
- Cost = 10,000 × 0.1 GB / 1024 × $5 = **$4.88/month**

## Cost Optimization Strategies

### 1. Use Partitioned Tables

**Before (Scans entire table):**
```sql
SELECT COUNT(*)
FROM `project.dataset.events`
WHERE event_date = '2024-01-15'
-- Scans: 500 GB → Cost: ~$2.50
```

**After (Scans only one partition):**
```sql
SELECT COUNT(*)
FROM `project.dataset.events`
WHERE _PARTITIONDATE = '2024-01-15'
-- Scans: 2 GB → Cost: ~$0.01
```

**Savings: 99%**

### 2. Use Clustering

```sql
-- Table clustered by user_id
SELECT *
FROM `project.dataset.user_events`
WHERE user_id = 12345
-- Only scans relevant clusters, not entire table
```

### 3. Select Only Needed Columns

**Before:**
```sql
SELECT *
FROM `project.dataset.wide_table`
-- Scans: 100 GB (all columns)
```

**After:**
```sql
SELECT user_id, event_type, timestamp
FROM `project.dataset.wide_table`
-- Scans: 5 GB (only 3 columns)
```

**Savings: 95%**

### 4. Use WHERE Clauses Effectively

```sql
-- Good - filters early
SELECT COUNT(*)
FROM `project.dataset.events`
WHERE date >= CURRENT_DATE() - 7  -- Last 7 days only
  AND region = 'US'

-- Bad - scans everything
SELECT COUNT(*)
FROM `project.dataset.events`
```

### 5. Use Query Caching

BigQuery automatically caches query results for 24 hours:

```sql
-- First run: Scans data, incurs cost
SELECT COUNT(*) FROM `project.dataset.table` WHERE date = CURRENT_DATE()

-- Second run within 24 hours: Uses cache, FREE!
SELECT COUNT(*) FROM `project.dataset.table` WHERE date = CURRENT_DATE()
```

**Note:** Cache invalidated if:
- Table data changes
- Query text changes (even spacing!)
- Cache expires (24 hours)

### 6. Use LIMIT for Testing

```sql
-- Testing query
SELECT *
FROM `project.dataset.large_table`
LIMIT 100  -- Still scans full table!

-- Better for testing
SELECT *
FROM `project.dataset.large_table`
WHERE _PARTITIONDATE = CURRENT_DATE()  -- Scan less data
LIMIT 100
```

**Important:** `LIMIT` does NOT reduce data scanned, only results returned!

### 7. Avoid SELECT DISTINCT on Large Datasets

```sql
-- Expensive - scans and processes all data
SELECT DISTINCT user_id
FROM `project.dataset.billion_row_table`

-- Better - use GROUP BY with filtering
SELECT user_id
FROM `project.dataset.billion_row_table`
WHERE date >= CURRENT_DATE() - 1
GROUP BY user_id
```

### 8. Use Approximate Aggregation

```sql
-- Exact (expensive)
SELECT COUNT(DISTINCT user_id)
FROM `project.dataset.large_table`

-- Approximate (cheaper, 98%+ accurate)
SELECT APPROX_COUNT_DISTINCT(user_id)
FROM `project.dataset.large_table`
-- Can be 10-100x cheaper!
```

## Cost-Effective Alert Patterns

### Pattern 1: Incremental Checks

**Instead of scanning all data:**
```sql
-- Scans entire table daily
SELECT COUNT(*) as row_count
FROM `project.dataset.events`
```

**Scan only new data:**
```sql
-- Scans only today's partition
SELECT COUNT(*) as row_count
FROM `project.dataset.events`
WHERE _PARTITIONDATE = CURRENT_DATE()
```

### Pattern 2: Aggregate Tables

Create summary tables for frequent checks:

```sql
-- Expensive - run daily on raw data
SELECT
  DATE(timestamp) as date,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_id) as unique_users
FROM `project.dataset.raw_events`
GROUP BY date

-- Better - create and maintain aggregates
-- Run once to create
CREATE TABLE `project.dataset.daily_metrics` AS
SELECT
  DATE(timestamp) as date,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_id) as unique_users
FROM `project.dataset.raw_events`
GROUP BY date;

-- Alert queries use pre-aggregated data (cheap!)
SELECT *
FROM `project.dataset.daily_metrics`
WHERE date = CURRENT_DATE()
```

### Pattern 3: Sample Large Datasets

```sql
-- For data quality checks, sampling is often sufficient
SELECT
  COUNTIF(email IS NULL) * 100.0 / COUNT(*) as null_percentage
FROM `project.dataset.users`
TABLESAMPLE SYSTEM (10 PERCENT)  -- Sample 10% of data
-- 90% cost reduction with statistically valid results!
```

### Pattern 4: Use Views

```sql
-- Create view with common filters
CREATE VIEW `project.dataset.recent_events` AS
SELECT *
FROM `project.dataset.events`
WHERE _PARTITIONDATE >= CURRENT_DATE() - 7;

-- Alerts query the view (always scoped)
SELECT COUNT(*)
FROM `project.dataset.recent_events`
WHERE event_type = 'error'
```

## SQL Sentinel Cost Optimization

### Configure Alert Schedules Wisely

```yaml
alerts:
  # High-cost query - run less frequently
  - name: "expensive_monthly_report"
    query: "SELECT * FROM huge_table"  # Scans TBs
    schedule: "0 0 1 * *"  # Monthly, not daily!

  # Low-cost query - can run frequently
  - name: "cheap_partition_check"
    query: "SELECT * FROM table WHERE _PARTITIONDATE = CURRENT_DATE()"
    schedule: "*/15 * * * *"  # Every 15 minutes is fine
```

### Cost Budget Example

**Scenario:** 10 alerts, $20/month budget

```yaml
alerts:
  # 5 high-frequency, low-cost alerts
  # 100 MB/query × 8,640 queries/month (every 5 min) = 864 GB → $4.32
  - name: "partition_check"
    query: "SELECT COUNT(*) FROM table WHERE date = CURRENT_DATE()"
    schedule: "*/5 * * * *"

  # 3 medium-frequency, medium-cost alerts
  # 1 GB/query × 720 queries/month (hourly) = 720 GB → $3.60
  - name: "hourly_aggregates"
    query: "SELECT SUM(amount) FROM table WHERE date >= CURRENT_DATE() - 7"
    schedule: "0 * * * *"

  # 2 low-frequency, high-cost alerts
  # 50 GB/query × 30 queries/month (daily) = 1.5 TB → $7.50
  - name: "daily_full_scan"
    query: "SELECT * FROM large_table WHERE date = CURRENT_DATE() - 1"
    schedule: "0 1 * * *"

# Total: $15.42/month (within $20 budget)
```

## Monitoring Costs

### Query BigQuery Job History

```sql
-- Check your actual costs from last 30 days
SELECT
  DATE(creation_time) as date,
  SUM(total_bytes_processed) / POW(10, 12) as tb_processed,
  SUM(total_bytes_processed) / POW(10, 12) * 5 as estimated_cost_usd,
  COUNT(*) as query_count
FROM `project.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
GROUP BY date
ORDER BY date DESC
```

### Set Up Cost Alert

```yaml
alerts:
  - name: "bigquery_cost_alert"
    description: "Alert when daily BigQuery costs exceed budget"
    enabled: true
    query: |
      WITH daily_usage AS (
        SELECT
          SUM(total_bytes_processed) / POW(10, 12) as tb_processed,
          SUM(total_bytes_processed) / POW(10, 12) * 5 as cost_usd
        FROM `project.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
        WHERE DATE(creation_time) = CURRENT_DATE()
          AND job_type = 'QUERY'
          AND state = 'DONE'
      )
      SELECT
        CASE WHEN cost_usd > 10 THEN 'ALERT' ELSE 'OK' END as status,
        ROUND(cost_usd, 2) as actual_value,
        10 as threshold,
        ROUND(tb_processed, 3) as tb_processed
      FROM daily_usage
    schedule: "0 */6 * * *"  # Every 6 hours
    notify:
      - channel: email
        recipients: ["bigquery-admins@company.com"]
```

### Use Budget Alerts (GCP Console)

1. Go to **Billing** > **Budgets & alerts**
2. Create budget for BigQuery
3. Set threshold amounts
4. Configure email alerts

## Cost Comparison: BigQuery vs Traditional DB

| Scenario | Traditional DB | BigQuery | Winner |
|----------|---------------|----------|---------|
| 1000 queries/day on 100 GB | $100/month (instance) | $5/month | BigQuery |
| Complex analytics on TB-scale | $1000+/month (big instance) | $20-50/month | BigQuery |
| Simple row lookups (millions/day) | $50/month (small instance) | $100+/month | Traditional |
| Ad-hoc analysis | Always-on cost | Pay only when queried | BigQuery |

## Real-World Cost Examples

### Example 1: E-commerce Data Quality

**Setup:**
- 5 data quality alerts
- Run hourly
- Scan yesterday's partition (~10 GB)

**Cost:**
- Queries/month: 5 × 24 × 30 = 3,600
- Data/month: 3,600 × 10 GB = 36 TB
- **Cost: (36-1) × $5 = $175/month**

**Optimization:**
- Use clustering on frequently filtered columns
- Query only changed rows (CDC pattern)
- **Optimized cost: ~$20/month (88% savings)**

### Example 2: SaaS Metrics Dashboard

**Setup:**
- 20 metric alerts
- Run every 5 minutes
- Each scans ~50 MB (well-partitioned)

**Cost:**
- Queries/month: 20 × 288 × 30 = 172,800
- Data/month: 172,800 × 0.05 GB = 8,640 GB = 8.44 TB
- **Cost: (8.44-1) × $5 = $37.20/month**

**Within free tier alternatives:**
- Pre-aggregate to materialized views
- Reduce frequency for non-critical alerts
- **Optimized: <$10/month**

## FAQ

### Q: Do failed queries cost money?

**A:** Yes, if they scan data before failing. Use syntax validation and dry-run to avoid this.

### Q: Does caching work with scheduled queries?

**A:** Yes, if the exact query runs within 24 hours and the table hasn't changed.

### Q: Can I set hard limits on query costs?

**A:** Not directly, but you can:
1. Use GCP budgets and alerts
2. Add custom cost checks in your queries
3. Use quotas to limit query size

### Q: What about querying public datasets?

**A:** Public datasets are FREE to query! No cost at all.

### Q: Does SELECT * always scan all columns?

**A:** Yes, but BigQuery is columnar, so unused columns in WHERE/GROUP BY don't cost much. Still, best to specify columns.

## Best Practices Summary

✅ **DO:**
- Use partitioned tables and partition filters
- Select only needed columns
- Use WHERE clauses to filter data
- Leverage query caching (reuse exact queries)
- Test queries with dry-run
- Create aggregate tables for frequent queries
- Use approximate functions when exact isn't needed
- Monitor costs regularly

❌ **DON'T:**
- Run `SELECT *` on large tables frequently
- Query entire tables when you need recent data
- Use LIMIT without WHERE (still scans all data)
- Run expensive queries on high-frequency schedules
- Ignore the query validator estimates
- Query raw data when aggregates exist

## Resources

- [BigQuery Pricing](https://cloud.google.com/bigquery/pricing)
- [Query Plan Explanation](https://cloud.google.com/bigquery/query-plan-explanation)
- [Optimizing Query Performance](https://cloud.google.com/bigquery/docs/best-practices-performance-overview)
- [Controlling Costs](https://cloud.google.com/bigquery/docs/best-practices-costs)

## Support

For cost optimization help specific to your use case, please open an issue on [GitHub](https://github.com/kyle-gehring/sqlsentinel/issues) with:
- Your query patterns
- Current costs
- Optimization goals
