import marimo

__generated_with = "0.16.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import sqlalchemy

    DATABASE_URL = "sqlite:///../portfolio.db"
    engine = sqlalchemy.create_engine(DATABASE_URL)
    return (engine,)


@app.cell
def _(engine, holdings, mo):
    df = mo.sql(
        f"""
        SELECT * FROM holdings LIMIT 100
        """,
        engine=engine
    )
    return (df,)


@app.cell
def _(df):
    df.head()
    return


@app.cell
def _():
    return


@app.cell
def _():
    from vega_datasets import data

    stocks = data.stocks()

    import altair as alt

    alt.Chart(stocks).mark_line().encode(
        x="date:T", y="price", color="symbol"
    ).interactive(bind_y=False)
    return


if __name__ == "__main__":
    app.run()
