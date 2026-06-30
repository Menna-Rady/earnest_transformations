from pyspark.sql import SparkSession

from transformers.llm_imputer import fill_na_with_llm


def test_skip_llm_uses_deterministic_fallbacks():
    spark = SparkSession.builder.master("local[1]").appName("llm-skip-test").getOrCreate()
    try:
        source = spark.createDataFrame(
            [("Example Product", None, "", None)],
            "product_name STRING, product_brand STRING, "
            "product_category STRING, product_subcategory STRING",
        )
        result = source.transform(
            fill_na_with_llm({"seller_name": "fixture", "skip_llm": True})
        ).first()
        assert result.product_brand == "unbranded"
        assert result.product_category == "unknown"
        assert result.product_subcategory == "unknown"
    finally:
        spark.stop()
