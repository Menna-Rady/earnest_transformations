# Semantic Layer â€” depi_dbt

This document explains the semantic layer added to the `earnest-transformations` dbt project as part of the DEPI Data Engineering program.

---

## What is a Semantic Layer?

A semantic layer is a business-friendly translation layer that sits on top of the data warehouse tables. Instead of writing raw SQL, analysts and BI tools can query pre-defined business metrics using plain language.

Without it, every analyst needs to know table names, join keys, and business logic. With it, they just pick a metric like "Average Product Price" and the engine handles the rest.

```
Raw Tables (Snowflake)
       â†“
Semantic Layer (this layer)
       â†“
BI Tools / Dashboards / Analysts
```

---

## Project Context

This semantic layer was built on top of a **star schema** data warehouse that tracks product prices scraped from Egyptian e-commerce platforms (Noon, Amazon Egypt, Talabat, and others).

### Underlying tables

| Table | Description | Rows |
|---|---|---|
| `fact_product` | One row per price observation event | 336,261 |
| `dim_product` | One row per unique product | 335,773 |
| `dim_seller` | One row per unique seller/platform | 64 |
| `dim_date` | Calendar attributes per scraping date | 5 |
| `dim_time` | Time-of-day attributes per scraping time | 16,707 |
| `metricflow_time_spine` | Required calendar table for MetricFlow | 5 |

---

## Files Changed

```
models/
â””â”€â”€ marts/
    â”œâ”€â”€ schema.yml                  â†گ semantic models + metrics added here
    â””â”€â”€ metricflow_time_spine.sql   â†گ new file: required time spine model
```

---

## Semantic Models

Semantic models map physical tables to business entities. Three semantic models were defined:

### 1. `product_pricing`
Maps to `fact_product`. This is the core semantic model â€” it defines all measures and the time dimension.

**Entities (join keys):**
| Entity | Type | Column |
|---|---|---|
| `fact` | primary | `fact_id` |
| `product` | foreign | `product_sk` |
| `seller` | foreign | `seller_sk` |

**Dimensions (grouping attributes):**
| Dimension | Type | Column |
|---|---|---|
| `scrape_date` | time | `date_id` |
| `has_discount` | categorical | `product_has_discount` |
| `availability` | categorical | `product_availability` |
| `measuring_unit` | categorical | `product_measuring_unit` |

**Measures (aggregations):**
| Measure | Aggregation | Column |
|---|---|---|
| `total_listings` | count | `fact_id` |
| `avg_current_price` | average | `product_current_price` |
| `avg_discount_percentage` | average | `product_discount_percentage` |
| `in_stock_count` | sum | `product_availability` |
| `discounted_count` | sum | `product_has_discount` |

---

### 2. `products`
Maps to `dim_product`. Enables grouping metrics by product attributes.

**Dimensions:** `product_name`, `product_category`, `product_subcategory`, `product_brand`

---

### 3. `sellers`
Maps to `dim_seller`. Enables grouping metrics by seller/platform.

**Dimensions:** `seller_name`, `is_talabat`

---

## Metrics

Five business metrics are defined on top of the measures:

| Metric Name | Label | Type | Description |
|---|---|---|---|
| `average_product_price` | Average Product Price (EGP) | simple | Mean current listed price across all scraped products |
| `discount_rate` | Average Discount Rate (%) | simple | Mean discount percentage across all listings |
| `total_product_listings` | Total Product Listings | simple | Total number of price observations scraped |
| `in_stock_listings` | In-stock Listings | simple | Total listings where product is available |
| `discounted_listings` | Discounted Listings | simple | Total listings that have a discount applied |

---

## MetricFlow Time Spine

MetricFlow requires a time spine table to perform time-based aggregations (by day, week, month, etc.).

**File:** `models/marts/metricflow_time_spine.sql`

```sql
{{ config(
    materialized='table',
    meta={
        'time_spine': {
            'standard_granularity_column': 'date_day'
        }
    }
) }}

SELECT
    DATE_TRUNC('day', date) AS date_day
FROM {{ ref('dim_date') }}
```

This table provides the calendar backbone that MetricFlow uses to group metrics across time periods.

---

## How the Three Layers Work Together

```
Layer 1 â€” Semantic Models
"Where is the data and how does it connect?"
Maps tables, defines join keys and dimensions.
        â†“
Layer 2 â€” Measures
"What calculations can be done on the raw data?"
Direct aggregations: avg, sum, count on columns.
        â†“
Layer 3 â€” Metrics
"What business questions can be answered?"
Business-friendly KPIs built on top of measures.
```

Each layer builds on the one before it. Measures cannot exist without semantic models. Metrics cannot exist without measures.

---

## Validation

The semantic layer was validated using:

```bash
dbt parse
```

Output confirmed:
```
Found 6 models, 276 data tests, 1 source,
5 metrics, 542 macros, 3 semantic models
```

All models built successfully with `dbt run`:
```
PASS=6  WARN=0  ERROR=0  SKIP=0  TOTAL=6
```

---

## Example Queries (MetricFlow CLI)

Once connected, metrics can be queried without writing SQL:

```bash
# Average price by product category
mf query --metrics average_product_price \
         --group-by product__product_category

# Discount rate by seller
mf query --metrics discount_rate \
         --group-by seller__seller_name

# Total listings over time
mf query --metrics total_product_listings \
         --group-by metric_time__month
```

---

## Environment

| Tool | Version |
|---|---|
| dbt-core | 1.11.11 |
| dbt-snowflake | 1.11.6 |
| Snowflake | Enterprise (Azure) |
| Database | `New_N` |
| Schema | `NEW_DEV` |
| Source database | `DEPI_DB.PUBLIC` |

---
