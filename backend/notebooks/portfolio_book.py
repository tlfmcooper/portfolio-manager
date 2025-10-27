# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair==5.5.0",
#     "marimo",
#     "numpy==2.3.4",
#     "polars==1.34.0",
#     "sqlalchemy==2.0.44",
# ]
# ///

import marimo

__generated_with = "0.17.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import sqlalchemy

    DATABASE_URL = "sqlite:///portfolio.db"
    engine = sqlalchemy.create_engine(DATABASE_URL)
    return (engine,)


@app.cell
def _(engine, mo):
    df = mo.sql(
        f"""
        SELECT * FROM transactions LIMIT 100
        """,
        engine=engine
    )
    return (df,)


@app.cell
def _(df):
    df
    return


@app.cell
def _(engine, mo):
    asset_df = mo.sql(
        f"""
        SELECT * FROM assets
        """,
        engine=engine
    )
    return (asset_df,)


@app.cell
def _(engine, mo):
    _df = mo.sql(
        f"""
        UPDATE holdings 
        SET quantity=33 , average_cost=22.78727273

        WHERE portfolio_id=1 and ticker='QBTS';
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM transactions;
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM holdings;
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM assets;
        """,
        engine=engine
    )
    return


@app.cell
def _():


    return


@app.cell
def _(asset_df):
    # Basic statistics and data quality assessment
    import polars as pl

    data_quality = pl.DataFrame({
        "Metric": ["Total Assets", "Active Assets", "Asset Types", "Unique Sectors", "Unique Industries", "USD Assets", "CAD Assets"],
        "Value": [
            asset_df.shape[0],
            asset_df.filter(pl.col("is_active") == 1).shape[0],
            asset_df["asset_type"].n_unique(),
            asset_df["sector"].drop_nulls().n_unique(),
            asset_df["industry"].drop_nulls().n_unique(),
            asset_df.filter(pl.col("currency") == "USD").shape[0],
            asset_df.filter(pl.col("currency") == "CAD").shape[0]
        ]
    })

    data_quality
    return (pl,)


@app.cell
def _(asset_df, pl):
    # Asset type distribution
    asset_type_dist = asset_df.group_by("asset_type").agg([
        pl.len().alias("count"),
        pl.col("current_price").mean().alias("avg_price"),
        pl.col("market_cap").mean().alias("avg_market_cap")
    ])

    asset_type_dist
    return


@app.cell
def _(asset_df, pl):
    # Sector analysis (excluding nulls)
    sector_analysis = asset_df.filter(pl.col("sector").is_not_null()).group_by("sector").agg([
        pl.len().alias("count"),
        pl.col("current_price").mean().alias("avg_price"),
        pl.col("pe_ratio").mean().alias("avg_pe_ratio"),
        pl.col("dividend_yield").mean().alias("avg_dividend_yield")
    ]).sort("count", descending=True)

    sector_analysis
    return


@app.cell
def _(asset_df, pl):
    # Valuation metrics summary (excluding nulls)
    valuation_metrics = asset_df.filter(
        pl.col("pe_ratio").is_not_null() | 
        pl.col("dividend_yield").is_not_null() | 
        pl.col("beta").is_not_null()
    ).select([
        pl.col("ticker"),
        pl.col("name"),
        pl.col("current_price"),
        pl.col("market_cap"),
        pl.col("pe_ratio"),
        pl.col("dividend_yield"),
        pl.col("beta")
    ]).sort("market_cap", descending=True)

    valuation_metrics
    return


@app.cell
def _(asset_df, pl):
    # Visualize market cap distribution
    import altair as alt

    market_cap_chart = alt.Chart(
        asset_df.filter(pl.col("market_cap").is_not_null())
    ).mark_bar().encode(
        x=alt.X("ticker:N", title="Ticker", sort="-y"),
        y=alt.Y("market_cap:Q", title="Market Cap (USD)", axis=alt.Axis(format="~s")),
        color=alt.Color("sector:N", title="Sector"),
        tooltip=[
            alt.Tooltip("ticker:N", title="Ticker"),
            alt.Tooltip("name:N", title="Name"),
            alt.Tooltip("market_cap:Q", title="Market Cap", format="$,.0f"),
            alt.Tooltip("sector:N", title="Sector")
        ]
    ).properties(
        title="Market Capitalization by Asset",
        width=600,
        height=400
    )

    market_cap_chart
    return (alt,)


@app.cell
def _(alt, asset_df, pl):
    # P/E Ratio vs Beta scatter plot
    pe_beta_chart = alt.Chart(
        asset_df.filter(
            pl.col("pe_ratio").is_not_null() & 
            pl.col("beta").is_not_null()
        )
    ).mark_circle(size=200, opacity=0.7).encode(
        x=alt.X("beta:Q", title="Beta (Volatility)", scale=alt.Scale(zero=False)),
        y=alt.Y("pe_ratio:Q", title="P/E Ratio", scale=alt.Scale(zero=False)),
        color=alt.Color("sector:N", title="Sector"),
        size=alt.Size("market_cap:Q", title="Market Cap", scale=alt.Scale(range=[100, 1000])),
        tooltip=[
            alt.Tooltip("ticker:N", title="Ticker"),
            alt.Tooltip("name:N", title="Name"),
            alt.Tooltip("pe_ratio:Q", title="P/E Ratio", format=".2f"),
            alt.Tooltip("beta:Q", title="Beta", format=".3f"),
            alt.Tooltip("market_cap:Q", title="Market Cap", format="$,.0f")
        ]
    ).properties(
        title="P/E Ratio vs Beta (sized by Market Cap)",
        width=600,
        height=400
    )

    pe_beta_chart
    return


@app.cell
def _(asset_df, pl):
    # Data completeness analysis
    import numpy as np

    completeness = pl.DataFrame({
        "Column": ["current_price", "market_cap", "dividend_yield", "pe_ratio", "beta", "sector", "industry"],
        "Complete": [
            asset_df["current_price"].is_not_null().sum(),
            asset_df["market_cap"].is_not_null().sum(),
            asset_df["dividend_yield"].is_not_null().sum(),
            asset_df["pe_ratio"].is_not_null().sum(),
            asset_df["beta"].is_not_null().sum(),
            asset_df["sector"].is_not_null().sum(),
            asset_df["industry"].is_not_null().sum()
        ],
        "Missing": [
            asset_df["current_price"].is_null().sum(),
            asset_df["market_cap"].is_null().sum(),
            asset_df["dividend_yield"].is_null().sum(),
            asset_df["pe_ratio"].is_null().sum(),
            asset_df["beta"].is_null().sum(),
            asset_df["sector"].is_null().sum(),
            asset_df["industry"].is_null().sum()
        ]
    }).with_columns(
        (pl.col("Complete") / (pl.col("Complete") + pl.col("Missing")) * 100).alias("Completeness %")
    )

    completeness
    return


@app.cell
def _(asset_df, mo, pl):
    # Key insights summary
    mo.md(f"""
    ## Asset Portfolio Analysis Summary

    ### Portfolio Composition
    - **Total Assets**: {asset_df.shape[0]}
    - **Asset Types**: {asset_df['asset_type'].n_unique()}
    - **Sectors Represented**: {asset_df['sector'].drop_nulls().n_unique()}
    - **Currencies**: {asset_df['currency'].n_unique()} (USD, CAD)

    ### Valuation Highlights
    - **Market Cap Range**: ${asset_df.filter(pl.col('market_cap').is_not_null())['market_cap'].min():,.0f} - ${asset_df.filter(pl.col('market_cap').is_not_null())['market_cap'].max():,.0f}
    - **Average P/E Ratio**: {asset_df.filter(pl.col('pe_ratio').is_not_null())['pe_ratio'].mean():.2f}
    - **Average Beta**: {asset_df.filter(pl.col('beta').is_not_null())['beta'].mean():.3f}

    ### Data Quality
    - Most assets have complete price data
    - Some assets (particularly crypto-related) lack fundamental metrics
    - All assets are currently marked as active

    ### Observations
    - Portfolio is dominated by large-cap technology stocks (Apple, Amazon)
    - Mix of high-growth and dividend-paying stocks
    - Presence of cryptocurrency exposure through ETF products
    - Beta values suggest moderate to high volatility in the portfolio
    """)
    return


@app.cell
def _():
    #
    return


@app.cell
def _(engine, mo):
    current_sol_holding = mo.sql(
        f"""
        SELECT ticker, quantity, average_cost, portfolio_id
        FROM holdings
        WHERE ticker='QBTS';
        """,
        engine=engine
    )
    return


@app.cell
def _():
    return


@app.cell
def _(engine, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM transactions;
        """,
        engine=engine
    )
    return


@app.cell
def _():
    eval("sum([0.1, 0.61, 0.001, 0.2, 0.05, 0.0081, 0.0009, 0.03])")
    return


if __name__ == "__main__":
    app.run()
