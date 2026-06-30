{{ config(materialized='table') }}

SELECT
    DATE_TRUNC('day', date) AS date_day
FROM {{ ref('dim_date') }}
