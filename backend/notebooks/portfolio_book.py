import marimo

__generated_with = "0.16.5"
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
def _(engine, mo, transactions):
    _df = mo.sql(
        f"""
        DELETE FROM transactions WHERE id=11;
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, mo, transactions):
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
def _(assets, engine, mo):
    asset_df = mo.sql(
        f"""
        SELECT * FROM assets
        """,
        engine=engine
    )
    return (asset_df,)


@app.cell
def _(assets, engine, mo):
    _df = mo.sql(
        f"""
        UPDATE assets 
            SET currency='CAD'
            WHERE ticker='MAU.TO'
        """,
        engine=engine
    )
    return


@app.cell
def _(asset_df):
    asset_df.currency
    return


@app.cell
def _(engine, holdings, mo):
    _df = mo.sql(
        f"""
        UPDATE holdings 
        SET quantity=80 , average_cost=6.49
        WHERE portfolio_id=2 and ticker='MAU.TO';
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, holdings, mo):
    _df = mo.sql(
        f"""
        UPDATE holdings 
        SET quantity=108.10
        WHERE ticker='MU';
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, mo, transactions):
    _df = mo.sql(
        f"""
        UPDATE transactions 
        SET price=69.77
        WHERE id=1;
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, holdings, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM holdings;
        """,
        engine=engine
    )
    return


@app.cell
def _(engine, holdings, mo):
    _df = mo.sql(
        f"""
        UPDATE holdings 
        SET average_cost=69.77
        WHERE ticker='AAPL';
        """,
        engine=engine
    )
    return


@app.cell
def _(assets, engine, mo):
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


if __name__ == "__main__":
    app.run()
