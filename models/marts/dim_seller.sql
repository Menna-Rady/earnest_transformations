{{ config(materialized='table') }}

SELECT
    md5(product_seller) AS seller_sk,
    product_seller,
    MAX(product_is_talabat_seller) AS product_is_talabat_seller
FROM 
    {{ source('raw_data', 'STG_ALL_SELLERS_PRODUCTS') }}
GROUP BY product_seller
