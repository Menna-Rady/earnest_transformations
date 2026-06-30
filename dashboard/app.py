"""
DEPI E-Commerce Price Tracker
Egyptian market price intelligence dashboard.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import snowflake.connector
from dash import Input, Output, State, dcc, html


NAVY = "#0D1B2A"
NAVY_2 = "#0F2035"
NAVY_3 = "#07111A"
GRID = "#1E3A5F"
PRIMARY = "#C8973A"
SECONDARY = "#8B0000"
ACCENT = "#E8B86D"
WHITE = "#F5F0E8"
MUTED = "#B7B0A4"
GREEN = "#3DBE7A"
RED = "#CC3333"
ORANGE = "#D98A28"

PALETTE = [PRIMARY, SECONDARY, ACCENT, "#A35D1D", "#D4A853", "#5AA469", "#B94747"]

SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
    "user": os.getenv("SNOWFLAKE_USER", ""),
    "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", ""),
    "database": os.getenv("SNOWFLAKE_DATABASE", ""),
    "schema": os.getenv("SNOWFLAKE_SCHEMA", ""),
    "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
}


@dataclass
class DataBundle:
    products: pd.DataFrame
    min_date: pd.Timestamp | None
    max_date: pd.Timestamp | None


def parse_bool(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"true", "t", "yes", "y", "1"}


def load_data() -> DataBundle:
    print("Loading all dashboard data from Snowflake...")
    missing = [name for name, value in SNOWFLAKE_CONFIG.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing Snowflake dashboard settings: " + ", ".join(missing)
        )
    sql = """
        SELECT
            f.fact_id,
            f.product_sk,
            f.seller_sk,
            f.product_current_price,
            f.product_old_price,
            f.product_discount_amount,
            f.product_discount_percentage,
            f.product_has_discount,
            f.product_availability,
            f.product_count,
            f.product_weight,
            f.product_measuring_unit,
            p.product_name,
            p.product_brand,
            p.product_category,
            p.product_subcategory,
            p.product_url,
            p.product_has_image_url,
            p.product_image_url,
            p.product_has_ram,
            p.product_has_storage,
            s.product_seller,
            s.product_is_talabat_seller,
            d.date,
            d.day,
            d.month,
            d.year,
            d.quarter,
            d.month_name,
            d.day_name,
            d.season,
            d.is_weekend,
            t.hour_24,
            t.hour_12,
            t.minute,
            t.part_of_day
        FROM FACT_PRODUCT f
        LEFT JOIN DIM_PRODUCT p ON f.product_sk = p.product_sk
        LEFT JOIN DIM_SELLER s ON f.seller_sk = s.seller_sk
        LEFT JOIN DIM_DATE d ON f.date_id = d.date_id
        LEFT JOIN DIM_TIME t ON f.time_id = t.time_id
    """
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    try:
        df = pd.read_sql(sql, conn)
    finally:
        conn.close()

    df.columns = [c.lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bool_cols = [
        "product_has_discount",
        "product_availability",
        "product_is_talabat_seller",
        "product_has_image_url",
        "product_has_ram",
        "product_has_storage",
        "is_weekend",
    ]
    for col in bool_cols:
        if col in df:
            df[col] = df[col].map(parse_bool)

    seller_text = df["product_seller"].fillna("").astype(str).str.lower()
    df["product_is_talabat_source"] = df["product_is_talabat_seller"] | seller_text.str.contains("talabat|طلبات", regex=True)

    numeric_cols = [
        "product_current_price",
        "product_old_price",
        "product_discount_amount",
        "product_discount_percentage",
        "product_count",
        "product_weight",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    min_date = df["date"].min()
    max_date = df["date"].max()
    print(f"Loaded {len(df):,} listings from Snowflake.")
    return DataBundle(products=df, min_date=min_date, max_date=max_date)


DATA = load_data()


def dropdown_options(column: str, fallback: str, limit: int = 120) -> list[dict[str, str]]:
    values = DATA.products[column].map(lambda v: clean_label(v, fallback)).dropna()
    ranked = values.value_counts().head(limit)
    return [{"label": name, "value": name, "title": f"{count:,} listings"} for name, count in ranked.items()]


def platform_filter_options(source_df: pd.DataFrame | None = None) -> list[dict[str, object]]:
    df = DATA.products if source_df is None else source_df
    talabat_count = int(df["product_is_talabat_source"].sum())
    other_count = int((~df["product_is_talabat_source"]).sum())
    return [
        {"label": f"All Seller Sources ({len(df):,})", "value": "all"},
        {"label": f"Talabat ({talabat_count:,})", "value": "talabat", "disabled": talabat_count == 0},
        {"label": f"Other Sources ({other_count:,})", "value": "other", "disabled": other_count == 0},
    ]


def filter_data(
    start_date: str | None,
    end_date: str | None,
    categories: list[str] | None = None,
    brands: list[str] | None = None,
    sellers: list[str] | None = None,
    platform: str | None = None,
    availability: str | None = None,
    discount_state: str | None = None,
) -> pd.DataFrame:
    df = DATA.products
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    if categories:
        df = df[df["product_category"].map(lambda v: clean_label(v, "Unknown")).isin(categories)]
    if brands:
        df = df[df["product_brand"].map(lambda v: clean_label(v, "Unbranded")).isin(brands)]
    if sellers:
        df = df[df["product_seller"].map(lambda v: clean_label(v, "Unknown Seller")).isin(sellers)]
    if platform == "talabat":
        df = df[df["product_is_talabat_source"]]
    elif platform == "other":
        df = df[~df["product_is_talabat_source"]]
    if availability == "in_stock":
        df = df[df["product_availability"]]
    elif availability == "out_of_stock":
        df = df[~df["product_availability"]]
    if discount_state == "discounted":
        df = df[df["product_has_discount"]]
    elif discount_state == "no_discount":
        df = df[~df["product_has_discount"]]
    return df.copy()


def fmt_int(value: float | int) -> str:
    return f"{int(value):,}"


def fmt_money(value: float) -> str:
    return f"{value:,.0f} EGP"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def clean_label(value: object, fallback: str = "Unknown") -> str:
    if pd.isna(value) or str(value).strip() == "":
        return fallback
    return str(value)


def page_title(icon: str, title: str, subtitle: str) -> html.Div:
    return html.Div(
        [
            html.Div(icon, className="page-icon"),
            html.Div([html.Div(title, className="page-title"), html.Div(subtitle, className="page-subtitle")]),
        ],
        className="page-header",
    )


def kpi_card(icon: str, label: str, value: str, trend: str, trend_class: str = "trend-up") -> html.Div:
    return html.Div(
        [
            html.Div(icon, className="kpi-icon"),
            html.Div(
                [
                    html.Div(value, className="kpi-value"),
                    html.Div(label, className="kpi-label"),
                    html.Div(trend, className=f"kpi-trend {trend_class}"),
                ],
                className="kpi-body",
            ),
        ],
        className="kpi-card",
    )


def chart_card(title: str, figure: go.Figure, class_name: str = "") -> html.Div:
    return html.Div(
        [
            html.Div(title, className="chart-title"),
            dcc.Graph(figure=figure, config={"displayModeBar": False}, className="chart-graph"),
        ],
        className=f"chart-card {class_name}".strip(),
    )


def theme_colors(theme: str | None) -> dict[str, str]:
    if theme == "light":
        return {
            "text": "#0D1B2A",
            "muted": "#48566A",
            "title": "#91631B",
            "grid": "rgba(13,27,42,.28)",
            "axis": "rgba(13,27,42,.82)",
            "hover_bg": "#FFF9EF",
            "hover_text": "#0D1B2A",
            "bar_text": "#0D1B2A",
        }
    return {
        "text": WHITE,
        "muted": MUTED,
        "title": PRIMARY,
        "grid": "rgba(30,58,95,.65)",
        "axis": "rgba(245,240,232,.35)",
        "hover_bg": NAVY_3,
        "hover_text": WHITE,
        "bar_text": WHITE,
    }


def empty_figure(title: str = "No data", theme: str | None = "dark") -> go.Figure:
    fig = go.Figure()
    colors = theme_colors(theme)
    fig.add_annotation(text=title, showarrow=False, font={"color": colors["muted"], "size": 16})
    return finish_figure(fig, theme=theme)


def finish_figure(fig: go.Figure, height: int = 330, theme: str | None = "dark") -> go.Figure:
    colors = theme_colors(theme)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=18, r=30, t=18, b=44),
        font=dict(color=colors["text"], family="Inter, Arial, sans-serif", size=11),
        hoverlabel=dict(bgcolor=colors["hover_bg"], bordercolor=PRIMARY, font=dict(color=colors["hover_text"])),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=colors["text"]), orientation="h", x=1, xanchor="right", y=1.12),
    )
    fig.update_xaxes(
        gridcolor=colors["grid"],
        zeroline=True,
        zerolinecolor=colors["axis"],
        rangemode="tozero",
        color=colors["text"],
        title_font=dict(color=colors["title"]),
        showline=True,
        linecolor=colors["axis"],
        linewidth=1,
    )
    fig.update_yaxes(
        gridcolor=colors["grid"],
        zeroline=False,
        color=colors["text"],
        title_font=dict(color=colors["title"]),
        showline=True,
        linecolor=colors["axis"],
        linewidth=1,
    )
    return fig


def value_labels(values: pd.Series, kind: str = "number") -> list[str]:
    if kind == "money":
        return [fmt_money(v) for v in values]
    if kind == "pct":
        return [fmt_pct(v) for v in values]
    return [fmt_int(v) for v in values]


def comparison_bar(
    df: pd.DataFrame,
    category: str,
    value: str,
    title: str,
    x_title: str,
    y_title: str,
    value_kind: str = "number",
    limit: int | None = None,
    highlight: str = "max",
    height: int = 360,
    theme: str | None = "dark",
) -> go.Figure:
    if df.empty:
        return empty_figure(theme=theme)
    theme_set = theme_colors(theme)
    data = df[[category, value]].dropna().copy()
    data[value] = pd.to_numeric(data[value], errors="coerce").fillna(0)
    data = data.sort_values(value, ascending=True)
    if limit:
        data = data.tail(limit)
    colors = [ACCENT] * len(data)
    if len(data) > 1:
        idx = data[value].idxmax() if highlight == "max" else data[value].idxmin()
        colors[data.index.get_loc(idx)] = GREEN if highlight == "max" else RED
    fig = go.Figure(
        go.Bar(
            x=data[value],
            y=data[category],
            orientation="h",
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,.95)", width=1)),
            text=value_labels(data[value], value_kind),
            textposition="outside",
            textfont=dict(color=theme_set["bar_text"], size=10),
            cliponaxis=False,
            hovertemplate=f"<b>%{{y}}</b><br>{x_title}: %{{x:,.2f}}<extra></extra>",
            name=x_title,
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(color=theme_set["title"], size=15, family="Cinzel")),
        xaxis_title=x_title,
        yaxis_title=y_title,
        showlegend=True,
        margin=dict(l=170, r=92, t=72, b=58),
    )
    return finish_figure(fig, height=height, theme=theme)


def distribution_bar(df: pd.DataFrame, category: str, value: str, title: str, x_title: str, y_title: str, height: int = 340, theme: str | None = "dark") -> go.Figure:
    if df.empty:
        return empty_figure(theme=theme)
    theme_set = theme_colors(theme)
    data = df[[category, value]].copy()
    fig = go.Figure(
        go.Bar(
            x=data[category],
            y=data[value],
            marker=dict(color=ACCENT, line=dict(color="rgba(0,0,0,.95)", width=1)),
            text=value_labels(data[value], "number"),
            textposition="outside",
            textfont=dict(color=theme_set["bar_text"], size=10),
            cliponaxis=False,
            hovertemplate=f"<b>%{{x}}</b><br>{y_title}: %{{y:,}}<extra></extra>",
            name=y_title,
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(color=theme_set["title"], size=15, family="Cinzel")),
        xaxis_title=x_title,
        yaxis_title=y_title,
        showlegend=True,
        margin=dict(l=70, r=50, t=72, b=80),
    )
    return finish_figure(fig, height=height, theme=theme)


def donut(labels, values, colors, center_text: str, height: int = 330, theme: str | None = "dark") -> go.Figure:
    theme_set = theme_colors(theme)
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color=NAVY, width=2)),
            textinfo="percent",
            textfont=dict(color=theme_set["text"], size=11),
            hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
        )
    )
    fig.add_annotation(text=center_text, showarrow=False, font=dict(color=theme_set["title"], size=18, family="Cinzel"))
    return finish_figure(fig, height=height, theme=theme)


def summary_metrics(df: pd.DataFrame) -> dict[str, float]:
    total = len(df)
    return {
        "total_listings": total,
        "unique_products": df["product_sk"].nunique(),
        "total_sellers": df["seller_sk"].nunique(),
        "avg_price": df["product_current_price"].mean() if total else 0,
        "max_price": df["product_current_price"].max() if total else 0,
        "min_price": df["product_current_price"].min() if total else 0,
        "avg_discount": df["product_discount_percentage"].mean() if total else 0,
        "discounted": int(df["product_has_discount"].sum()) if total else 0,
        "availability_rate": df["product_availability"].mean() * 100 if total else 0,
        "out_of_stock": int((~df["product_availability"]).sum()) if total else 0,
        "talabat_sellers": df.loc[df["product_is_talabat_source"], "seller_sk"].nunique() if total else 0,
    }


def by_category(df: pd.DataFrame) -> pd.DataFrame:
    work = df.assign(category=df["product_category"].map(clean_label))
    return (
        work.groupby("category", as_index=False)
        .agg(
            total_listings=("fact_id", "count"),
            avg_price=("product_current_price", "mean"),
            avg_discount=("product_discount_percentage", "mean"),
            availability_rate=("product_availability", lambda s: s.mean() * 100),
            discounted_count=("product_has_discount", "sum"),
        )
        .sort_values("total_listings", ascending=False)
    )


def by_seller(df: pd.DataFrame) -> pd.DataFrame:
    work = df.assign(seller=df["product_seller"].map(lambda v: clean_label(v, "Unknown Seller")))
    return (
        work.groupby(["seller", "product_is_talabat_source"], as_index=False)
        .agg(
            total_listings=("fact_id", "count"),
            unique_products=("product_sk", "nunique"),
            avg_price=("product_current_price", "mean"),
            avg_discount=("product_discount_percentage", "mean"),
            availability_rate=("product_availability", lambda s: s.mean() * 100),
        )
        .sort_values("total_listings", ascending=False)
    )


def top_brands(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    work = df.assign(brand=df["product_brand"].map(lambda v: clean_label(v, "Unbranded")))
    return (
        work.groupby("brand", as_index=False)
        .agg(total_listings=("fact_id", "count"), avg_price=("product_current_price", "mean"))
        .sort_values("total_listings", ascending=False)
        .head(limit)
    )


def price_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bins = [-np.inf, 50, 100, 250, 500, 1000, np.inf]
    labels = ["Under 50 EGP", "50-100 EGP", "100-250 EGP", "250-500 EGP", "500-1000 EGP", "Over 1000 EGP"]
    return (
        df.assign(price_range=pd.cut(df["product_current_price"], bins=bins, labels=labels))
        .groupby("price_range", observed=False)
        .size()
        .reindex(labels, fill_value=0)
        .reset_index(name="count")
    )


def discount_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bins = [-0.001, 0, 10, 25, 50, np.inf]
    labels = ["No Discount", "1-10%", "10-25%", "25-50%", "50%+"]
    return (
        df.assign(discount_range=pd.cut(df["product_discount_percentage"], bins=bins, labels=labels))
        .groupby("discount_range", observed=False)
        .size()
        .reindex(labels, fill_value=0)
        .reset_index(name="count")
    )


def seller_source_split(df: pd.DataFrame, limit: int = 6) -> pd.DataFrame:
    work = df.assign(
        source=np.where(
            df["product_is_talabat_source"],
            "Talabat",
            df["product_seller"].map(lambda v: clean_label(v, "Unknown Seller")),
        )
    )
    grouped = work.groupby("source", as_index=False).agg(total_listings=("fact_id", "count"))
    talabat = grouped[grouped["source"] == "Talabat"]
    others = grouped[grouped["source"] != "Talabat"].sort_values("total_listings", ascending=False)
    top_others = others.head(limit)
    remaining = others.iloc[limit:]["total_listings"].sum()
    result = pd.concat([talabat, top_others], ignore_index=True)
    if remaining > 0:
        result = pd.concat(
            [result, pd.DataFrame([{"source": "Other Sellers", "total_listings": remaining}])],
            ignore_index=True,
        )
    return result.sort_values("total_listings", ascending=False)


def overview_page(df: pd.DataFrame, theme: str = "dark") -> html.Div:
    metrics = summary_metrics(df)
    cats = by_category(df).head(12)
    sellers = by_seller(df)
    brands = top_brands(df, 5)
    price_dist = price_distribution(df)
    source_split = seller_source_split(df)
    has_talabat = bool(df["product_is_talabat_source"].any())
    platform_title = "Seller Source Split"
    platform_center = "Platforms" if has_talabat else "No Talabat"
    platform_colors = [
        SECONDARY if label == "Talabat" else PRIMARY if i == 0 else PALETTE[(i + 1) % len(PALETTE)]
        for i, label in enumerate(source_split["source"])
    ]

    return html.Div(
        [
            page_title("⌂", "Overview", "Market pulse across listings, categories, platforms, and brands"),
            html.Div(
                [
                    kpi_card("◈", "Total Listings", fmt_int(metrics["total_listings"]), "▲ live Snowflake rows"),
                    kpi_card("▣", "Unique Products", fmt_int(metrics["unique_products"]), "▲ tracked SKUs"),
                    kpi_card("♚", "Total Sellers", fmt_int(metrics["total_sellers"]), "▲ active sellers"),
                    kpi_card("£", "Avg Price", fmt_money(metrics["avg_price"]), "▼ current mean", "trend-dn"),
                    kpi_card("%", "Avg Discount", fmt_pct(metrics["avg_discount"]), "▲ blended rate"),
                    kpi_card("✓", "In-stock Rate", fmt_pct(metrics["availability_rate"]), "▲ available now"),
                ],
                className="kpi-grid",
            ),
            html.Div(
                [
                    chart_card(
                        "Products by Category",
                        comparison_bar(
                            cats,
                            "category",
                            "total_listings",
                            "Products by Category - Ranking",
                            "Total Listings",
                            "Product Category",
                            limit=12,
                            highlight="max",
                            theme=theme,
                        ),
                        "wide",
                    ),
                    chart_card(platform_title, donut(source_split["source"], source_split["total_listings"], platform_colors, platform_center, theme=theme)),
                    chart_card(
                        "Price Distribution by Range",
                        distribution_bar(price_dist, "price_range", "count", "Price Distribution by Range", "Price Range", "Listing Count", theme=theme),
                    ),
                    chart_card(
                        "Top 5 Brands",
                        comparison_bar(brands, "brand", "total_listings", "Top 5 Brands - Ranking", "Total Listings", "Brand", limit=5, theme=theme),
                        "wide",
                    ),
                ],
                className="charts-grid",
            ),
        ]
    )


def price_page(df: pd.DataFrame, theme: str = "dark") -> html.Div:
    metrics = summary_metrics(df)
    cats = by_category(df)
    sellers = by_seller(df).sort_values("avg_price", ascending=False).head(12)
    expensive = cats.sort_values("avg_price", ascending=False).head(5)
    cheap = cats[cats["avg_price"] > 0].sort_values("avg_price", ascending=True).head(5)
    price_dist = price_distribution(df)
    price_range = metrics["max_price"] - metrics["min_price"]

    return html.Div(
        [
            page_title("⌁", "Price Analysis", "Price bands, category economics, and seller price positioning"),
            html.Div(
                [
                    kpi_card("£", "Avg Price", fmt_money(metrics["avg_price"]), "▲ market mean"),
                    kpi_card("▲", "Max Price", fmt_money(metrics["max_price"]), "▲ highest listing"),
                    kpi_card("▼", "Min Price", fmt_money(metrics["min_price"]), "▼ lowest listing", "trend-dn"),
                    kpi_card("↔", "Price Range", fmt_money(price_range), "▲ max-min spread"),
                ],
                className="kpi-grid compact",
            ),
            html.Div(
                [
                    chart_card(
                        "Average Price by Category",
                        comparison_bar(cats, "category", "avg_price", "Average Price by Category - Ranking", "Average Price (EGP)", "Product Category", "money", limit=14, theme=theme),
                        "wide",
                    ),
                    chart_card(
                        "Average Price by Seller",
                        comparison_bar(sellers, "seller", "avg_price", "Average Price by Seller - Ranking", "Average Price (EGP)", "Seller", "money", limit=12, theme=theme),
                    ),
                    chart_card(
                        "Top 5 Most Expensive Categories",
                        comparison_bar(expensive, "category", "avg_price", "Most Expensive Categories", "Average Price (EGP)", "Product Category", "money", limit=5, theme=theme),
                    ),
                    chart_card(
                        "Top 5 Cheapest Categories",
                        comparison_bar(cheap, "category", "avg_price", "Cheapest Categories", "Average Price (EGP)", "Product Category", "money", limit=5, highlight="min", theme=theme),
                    ),
                    chart_card("Price Range Distribution", donut(price_dist["price_range"], price_dist["count"], PALETTE, "Price", theme=theme)),
                ],
                className="charts-grid",
            ),
        ]
    )


def discount_page(df: pd.DataFrame, theme: str = "dark") -> html.Div:
    metrics = summary_metrics(df)
    cats = by_category(df)
    sellers = by_seller(df)
    disc_sellers = sellers.sort_values("avg_discount", ascending=False).head(12)
    avail_sellers = sellers.sort_values("availability_rate", ascending=False).head(12)
    disc_dist = discount_distribution(df)
    avail_cats = cats.sort_values("availability_rate", ascending=False).head(14)

    return html.Div(
        [
            page_title("◇", "Discount & Availability", "Promotion depth and stock health by category and seller"),
            html.Div(
                [
                    kpi_card("%", "Avg Discount %", fmt_pct(metrics["avg_discount"]), "▲ weighted listings"),
                    kpi_card("◆", "Discounted Products", fmt_int(metrics["discounted"]), "▲ products on sale"),
                    kpi_card("✓", "Avg Availability Rate", fmt_pct(metrics["availability_rate"]), "▲ in-stock share"),
                    kpi_card("!", "Out of Stock Count", fmt_int(metrics["out_of_stock"]), "▼ unavailable rows", "trend-dn"),
                ],
                className="kpi-grid compact",
            ),
            html.Div(
                [
                    chart_card(
                        "Discount % by Category",
                        comparison_bar(cats, "category", "avg_discount", "Discount % by Category - Ranking", "Average Discount (%)", "Product Category", "pct", limit=14, theme=theme),
                        "wide",
                    ),
                    chart_card(
                        "Discount Rate by Seller",
                        comparison_bar(disc_sellers, "seller", "avg_discount", "Discount Rate by Seller - Ranking", "Average Discount (%)", "Seller", "pct", limit=12, theme=theme),
                    ),
                    chart_card("Discount Distribution", donut(disc_dist["discount_range"], disc_dist["count"], ["#2A3442", ACCENT, PRIMARY, ORANGE, SECONDARY], "Discount", theme=theme)),
                    chart_card(
                        "Availability Rate by Category",
                        comparison_bar(avail_cats, "category", "availability_rate", "Availability Rate by Category - Ranking", "Availability Rate (%)", "Product Category", "pct", limit=14, theme=theme),
                    ),
                    chart_card(
                        "Availability by Seller",
                        comparison_bar(avail_sellers, "seller", "availability_rate", "Availability by Seller - Ranking", "Availability Rate (%)", "Seller", "pct", limit=12, theme=theme),
                    ),
                ],
                className="charts-grid",
            ),
        ]
    )


def seller_page(df: pd.DataFrame, theme: str = "dark") -> html.Div:
    metrics = summary_metrics(df)
    sellers = by_seller(df)
    brands = top_brands(df, 10)
    global_talabat_sellers = DATA.products.loc[DATA.products["product_is_talabat_source"], "seller_sk"].nunique()
    top_seller = sellers.iloc[0]["seller"] if not sellers.empty else "N/A"
    avg_products = sellers["unique_products"].mean() if not sellers.empty else 0
    listings = sellers.sort_values("total_listings", ascending=False).head(12)
    unique = sellers.sort_values("unique_products", ascending=False).head(12)
    avail = sellers.sort_values("availability_rate", ascending=False).head(12)

    scatter = go.Figure(
        go.Scatter(
            x=sellers["avg_price"],
            y=sellers["avg_discount"],
            mode="markers+text",
            text=sellers["seller"],
            textposition="top center",
            textfont=dict(color=theme_colors(theme)["muted"], size=9),
            marker=dict(
                size=(sellers["total_listings"] / max(sellers["total_listings"].max(), 1) * 42) + 10,
                color=[SECONDARY if v else PRIMARY for v in sellers["product_is_talabat_source"]],
                opacity=0.82,
                line=dict(color=ACCENT, width=1),
            ),
            hovertemplate="<b>%{text}</b><br>Avg price: %{x:,.0f} EGP<br>Avg discount: %{y:.1f}%<extra></extra>",
        )
    )
    scatter.update_layout(xaxis_title="Average Price (EGP)", yaxis_title="Average Discount (%)")

    return html.Div(
        [
            page_title("♛", "Seller Intelligence", "Seller scale, catalog breadth, availability, and price posture"),
            html.Div(
                [
                    kpi_card("♚", "Total Sellers", fmt_int(metrics["total_sellers"]), "▲ marketplace breadth"),
                    kpi_card("★", "Talabat-Flagged Sellers", fmt_int(global_talabat_sellers), "all seller dimension"),
                    kpi_card("◆", "Top Seller by Listings", str(top_seller)[:24], "▲ highest volume"),
                    kpi_card("▦", "Avg Products per Seller", fmt_int(avg_products), "▲ unique products"),
                ],
                className="kpi-grid compact",
            ),
            html.Div(
                [
                    chart_card(
                        "Total Listings per Seller",
                        comparison_bar(listings, "seller", "total_listings", "Total Listings per Seller - Ranking", "Total Listings", "Seller", limit=12, theme=theme),
                    ),
                    chart_card(
                        "Unique Products per Seller",
                        comparison_bar(unique, "seller", "unique_products", "Unique Products per Seller - Ranking", "Unique Products", "Seller", limit=12, theme=theme),
                    ),
                    chart_card("Seller Intelligence Map", finish_figure(scatter, 390, theme=theme), "wide"),
                    chart_card(
                        "Availability Rate by Seller",
                        comparison_bar(avail, "seller", "availability_rate", "Availability Rate by Seller - Ranking", "Availability Rate (%)", "Seller", "pct", limit=12, theme=theme),
                    ),
                    chart_card(
                        "Top 10 Brands",
                        comparison_bar(brands, "brand", "total_listings", "Top 10 Brands - Ranking", "Total Listings", "Brand", limit=10, theme=theme),
                    ),
                ],
                className="charts-grid",
            ),
        ]
    )


PAGES: list[tuple[str, str, Callable[[pd.DataFrame, str], html.Div]]] = [
    ("Overview", "⌂", overview_page),
    ("Price Analysis", "⌁", price_page),
    ("Discount & Availability", "%", discount_page),
    ("Seller Intelligence", "♚", seller_page),
]

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "DEPI E-Commerce Price Tracker"


def sidebar() -> html.Div:
    return html.Div(
        [
            html.Div([html.Div("𓅃", className="sidebar-eagle"), html.Div("DEPI PRICE TRACKER", className="sidebar-name")], className="sidebar-brand"),
            html.Div("Navigation", className="nav-section-label"),
            html.Div(
                [
                    html.Button([html.Span(icon, className="nav-icon"), html.Span(label)], id=f"nav-{i}", n_clicks=0, className="nav-btn")
                    for i, (label, icon, _) in enumerate(PAGES)
                ],
                className="nav-list",
            ),
            html.Div(className="sidebar-divider"),
            html.Div("Snowflake • New_N.NEW_DEV", className="sidebar-footer"),
        ],
        className="sidebar",
    )


def header() -> html.Div:
    min_date = DATA.min_date.date() if pd.notna(DATA.min_date) else None
    max_date = DATA.max_date.date() if pd.notna(DATA.max_date) else None
    return html.Div(
        [
            html.Div(className="flag-band"),
            html.Div(className="pyramid-line"),
            html.Div(
                [
                    html.Div("𓅃", className="header-eagle"),
                    html.H1("EGYPT", className="hero-word"),
                    html.Div("DEPI E-COMMERCE PRICE TRACKER", className="header-title"),
                    html.Div("Egyptian Market — Price Intelligence Dashboard", className="header-subtitle"),
                ],
                className="header-center",
            ),
            html.Div(
                [
                    html.Button("sun", id="theme-toggle", n_clicks=0, className="theme-toggle", title="Toggle dark or light theme"),
                    html.Button("bell", className="theme-toggle ghost", title="Notifications"),
                    dcc.DatePickerRange(
                        id="date-range",
                        min_date_allowed=min_date,
                        max_date_allowed=max_date,
                        start_date=min_date,
                        end_date=max_date,
                        display_format="YYYY-MM-DD",
                        className="date-range",
                    ),
                ],
                className="header-right",
            ),
        ],
        className="header",
    )


def filter_panel() -> html.Div:
    return html.Div(
        [
            html.Div("Filters", className="filter-title"),
            dcc.Dropdown(
                id="category-filter",
                options=dropdown_options("product_category", "Unknown"),
                multi=True,
                placeholder="Category",
                optionHeight=44,
                maxHeight=260,
                className="filter-control",
            ),
            dcc.Dropdown(
                id="brand-filter",
                options=dropdown_options("product_brand", "Unbranded"),
                multi=True,
                placeholder="Brand",
                optionHeight=44,
                maxHeight=260,
                className="filter-control",
            ),
            dcc.Dropdown(
                id="seller-filter",
                options=dropdown_options("product_seller", "Unknown Seller"),
                multi=True,
                placeholder="Seller",
                optionHeight=44,
                maxHeight=260,
                className="filter-control",
            ),
            dcc.Dropdown(
                id="platform-filter",
                options=platform_filter_options(),
                value="all",
                clearable=False,
                className="filter-control",
            ),
            dcc.Dropdown(
                id="availability-filter",
                options=[
                    {"label": "All Availability", "value": "all"},
                    {"label": "In Stock", "value": "in_stock"},
                    {"label": "Out of Stock", "value": "out_of_stock"},
                ],
                value="all",
                clearable=False,
                className="filter-control",
            ),
            dcc.Dropdown(
                id="discount-filter",
                options=[
                    {"label": "All Discounts", "value": "all"},
                    {"label": "Discounted", "value": "discounted"},
                    {"label": "No Discount", "value": "no_discount"},
                ],
                value="all",
                clearable=False,
                className="filter-control",
            ),
            html.Button("Clear Filters", id="clear-filters", n_clicks=0, className="clear-filters"),
        ],
        className="filter-panel",
    )


app.layout = html.Div(
    [
        dcc.Store(id="current-page", data=0),
        dcc.Store(id="theme-store", data="dark"),
        sidebar(),
        html.Div(
            [
                header(),
                filter_panel(),
                dcc.Loading(html.Main(id="page-content", className="page-content"), color=PRIMARY, type="circle", fullscreen=False),
                html.Div(
                    [
                        html.Div("𓂀 𓋹 𓆣 𓇳 𓊖 𓏏", className="hieroglyph-left"),
                        html.Div("𓆣", className="bottom-center-icon"),
                        html.Div("Know the market before the market moves.", className="bottom-quote"),
                        html.Div("𓏏 𓊖 𓇳 𓆣 𓋹 𓂀", className="hieroglyph-right"),
                    ],
                    className="bottom-strip",
                ),
            ],
            className="main-area",
        ),
    ],
    id="app-shell",
    className="app-wrapper theme-dark",
)


@app.callback(Output("current-page", "data"), [Input(f"nav-{i}", "n_clicks") for i in range(len(PAGES))], prevent_initial_call=True)
def set_page(*_: int) -> int:
    ctx = dash.callback_context
    if not ctx.triggered:
        return 0
    return int(ctx.triggered[0]["prop_id"].split(".")[0].split("-")[1])


@app.callback(Output("theme-store", "data"), Input("theme-toggle", "n_clicks"), State("theme-store", "data"))
def toggle_theme(n_clicks: int, current: str) -> str:
    if not n_clicks:
        return current
    return "light" if current == "dark" else "dark"


@app.callback(Output("app-shell", "className"), Input("theme-store", "data"))
def shell_class(theme: str) -> str:
    return f"app-wrapper theme-{theme}"


@app.callback([Output(f"nav-{i}", "className") for i in range(len(PAGES))], Input("current-page", "data"))
def nav_classes(current: int) -> list[str]:
    return ["nav-btn active" if i == current else "nav-btn" for i in range(len(PAGES))]


@app.callback(
    Output("category-filter", "value"),
    Output("brand-filter", "value"),
    Output("seller-filter", "value"),
    Output("platform-filter", "value"),
    Output("availability-filter", "value"),
    Output("discount-filter", "value"),
    Input("clear-filters", "n_clicks"),
    prevent_initial_call=True,
)
def clear_filters(_: int):
    return [], [], [], "all", "all", "all"


@app.callback(
    Output("platform-filter", "options"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("category-filter", "value"),
    Input("brand-filter", "value"),
    Input("seller-filter", "value"),
    Input("availability-filter", "value"),
    Input("discount-filter", "value"),
)
def update_platform_options(
    start_date: str | None,
    end_date: str | None,
    categories: list[str] | None,
    brands: list[str] | None,
    sellers: list[str] | None,
    availability: str | None,
    discount_state: str | None,
):
    df = filter_data(
        start_date,
        end_date,
        categories,
        brands,
        sellers,
        None,
        None if availability == "all" else availability,
        None if discount_state == "all" else discount_state,
    )
    return platform_filter_options(df)


@app.callback(
    Output("page-content", "children"),
    Input("current-page", "data"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("category-filter", "value"),
    Input("brand-filter", "value"),
    Input("seller-filter", "value"),
    Input("platform-filter", "value"),
    Input("availability-filter", "value"),
    Input("discount-filter", "value"),
    Input("theme-store", "data"),
)
def render_page(
    page: int,
    start_date: str | None,
    end_date: str | None,
    categories: list[str] | None,
    brands: list[str] | None,
    sellers: list[str] | None,
    platform: str | None,
    availability: str | None,
    discount_state: str | None,
    theme: str | None,
):
    df = filter_data(
        start_date,
        end_date,
        categories,
        brands,
        sellers,
        None if platform == "all" else platform,
        None if availability == "all" else availability,
        None if discount_state == "all" else discount_state,
    )
    if df.empty:
        return html.Div(
            [
                page_title("!", "No Data", "Try expanding the date range"),
                html.Div("No Snowflake rows are available for the selected dates.", className="error-banner"),
            ]
        )
    return PAGES[page][2](df, theme or "dark")


if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  DEPI E-Commerce Price Tracker is running")
    print("  URL: http://127.0.0.1:8050")
    print("=" * 62 + "\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
