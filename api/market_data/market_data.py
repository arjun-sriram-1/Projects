# ============================================================
# FILE: models/market/market_data.py
# FULL FINAL REPLACEMENT
# Production-ready live market parameter loader
# Seamlessly integrated with:
# - yfinance
# - GBM
# - feature engineering
# - Monte Carlo
# ============================================================

import yfinance as yf
import pandas as pd
import numpy as np

# ------------------------------------------------
# DATABASE
# ------------------------------------------------
from api.db.session import SessionLocal

from sqlalchemy import text


MARKET_TICKERS = {
    "crude_oil": "CL=F",
    "brent_oil": "BZ=F",
    "heating_oil_proxy": "HO=F",
    "natural_gas": "NG=F",
    "vix": "^VIX",
    "sp500": "^GSPC",
    "usd_inr": "USDINR=X",
    "eur_usd": "EURUSD=X",
    "dxy": "DX-Y.NYB",
    "gold": "GC=F",
    "us_10y_yield": "^TNX",
    "freight_proxy": "BDRY",
}


def get_market_tickers():

    return MARKET_TICKERS.copy()


# ============================================================
# SAVE RAW MARKET PRICES TO POSTGRESQL
# ============================================================

def save_market_prices_to_db(

    asset_name,
    ticker,
    df

):

    db = SessionLocal()

    try:

        for idx, row in df.iterrows():

            query = text(
                """
                INSERT INTO market_prices (

                    date,
                    price,
                    asset,
                    ticker,
                    source_id,
                    asset_name,
                    data_source,
                    frequency

                )
                VALUES (

                    :date,
                    :price,
                    :asset,
                    :ticker,
                    :source_id,
                    :asset_name,
                    :data_source,
                    :frequency

                )
                """
            )

            db.execute(

                query,

                {

                    "date": idx.to_pydatetime(),

                    "price": float(row["Close"]),

                    "asset": asset_name,

                    "ticker": ticker,

                    "source_id": ticker,

                    "asset_name": asset_name,

                    "data_source": "yfinance",

                    "frequency": "daily"
                }
            )

        db.commit()

        print(f"{asset_name} prices saved to PostgreSQL")

    except Exception as e:

        print(f"DB INSERT ERROR ({asset_name}):", e)

        db.rollback()

    finally:

        db.close()


# ============================================================
# SAVE MARKET FEATURES TO POSTGRESQL
# ============================================================

def save_market_features_to_db(df):

    db = SessionLocal()

    try:

        for _, row in df.iterrows():

            query = text(
                """
                INSERT INTO market_features (

                    asset,
                    ticker,
                    source_id,
                    data_source,
                    mu,
                    sigma,
                    latest_price

                )
                VALUES (

                    :asset,
                    :ticker,
                    :source_id,
                    :data_source,
                    :mu,
                    :sigma,
                    :latest_price

                )
                """
            )

            db.execute(

                query,

                {

                    "asset": row["asset"],

                    "ticker": row["ticker"],
                    
                    "source_id": row.get("source_id", row["ticker"]),
                    
                    "data_source": row.get("data_source", "yfinance"),

                    "mu": float(row["mu"]),

                    "sigma": float(row["sigma"]),

                    "latest_price": float(
                        row["latest_price"]
                    )
                }
            )

        db.commit()

        print("Market features saved to PostgreSQL")

    except Exception as e:

        print("MARKET FEATURES INSERT ERROR:", e)

        db.rollback()

    finally:

        db.close()


# ============================================================
# DOWNLOAD RAW MARKET DATA
# ============================================================

def download_market_data(
    ticker,
    period="2y",
    interval="1d"
):
    """
    Download raw market data from Yahoo Finance
    """

    data = yf.download(

        ticker,

        period=period,

        interval=interval,

        auto_adjust=True,

        progress=False
    )

    if data.empty:

        raise ValueError(
            f"No data downloaded for {ticker}"
        )

    return data


# ============================================================
# COMPUTE LOG RETURNS
# ============================================================

def compute_log_returns(price_series):
    """
    Compute log returns
    """

    returns = np.log(

        price_series / price_series.shift(1)

    )

    returns = returns.dropna()

    return returns


# ============================================================
# COMPUTE MARKET PARAMETERS
# ============================================================

def compute_market_parameters(
    ticker,
    period="2y"
):
    """
    Returns:
    - annualized drift (mu)
    - annualized volatility (sigma)
    - latest price
    """

    data = download_market_data(

        ticker=ticker,

        period=period
    )

    # ------------------------------------------------
    # FIX MULTIINDEX ISSUES
    # ------------------------------------------------
    if isinstance(data.columns, pd.MultiIndex):

        data.columns = (
            data.columns.get_level_values(0)
        )

    # ------------------------------------------------
    # CLOSE SERIES
    # ------------------------------------------------
    close_prices = data["Close"]

    # Ensure Series
    if isinstance(close_prices, pd.DataFrame):

        close_prices = close_prices.iloc[:, 0]

    # ------------------------------------------------
    # RETURNS
    # ------------------------------------------------
    returns = compute_log_returns(
        close_prices
    )

    # ------------------------------------------------
    # ANNUALIZED PARAMETERS
    # ------------------------------------------------
    mu = float(

        returns.mean() * 252

    )

    sigma = float(

        returns.std() * np.sqrt(252)

    )

    latest_price = float(

        close_prices.iloc[-1]

    )

    return {

        "ticker": ticker,

        "mu": mu,

        "sigma": sigma,

        "latest_price": latest_price,

        "raw_data": data
    }


# ============================================================
# MULTI-ASSET MARKET PIPELINE
# ============================================================

def get_all_market_features():
    """
    Fetch all required market assets
    """

    rows = []

    for asset_name, ticker in MARKET_TICKERS.items():

        try:

            params = compute_market_parameters(
                ticker
            )

            # ------------------------------------------------
            # SAVE RAW PRICES TO DB
            # ------------------------------------------------
            save_market_prices_to_db(

                asset_name=asset_name,

                ticker=ticker,

                df=params["raw_data"]
            )

            rows.append({

                "asset": asset_name,

                "ticker": ticker,
                
                "source_id": ticker,
                
                "data_source": "yfinance",

                "mu": params["mu"],

                "sigma": params["sigma"],

                "latest_price":
                    params["latest_price"]
            })

            print(f"SUCCESS: {asset_name}")

        except Exception as e:

            print(f"FAILED: {asset_name} -> {e}")

    df = pd.DataFrame(rows)

    # ------------------------------------------------
    # SAVE FEATURES TO DB
    # ------------------------------------------------
    save_market_features_to_db(df)

    return df


# ============================================================
# SAVE MARKET FEATURES CSV
# ============================================================

def save_market_features(

    output_path=
    "data/processed/market_features.csv"
):
    """
    Save processed market params
    """

    df = get_all_market_features()

    df.to_csv(

        output_path,

        index=False
    )

    print(
        f"\nSaved market features to:\n{output_path}"
    )

    return df


# ============================================================
# SINGLE ASSET WRAPPER
# ============================================================

def get_market_data(ticker):
    """
    Backward-compatible wrapper
    Returns:
        mu, sigma
    """

    params = compute_market_parameters(
        ticker
    )

    return (

        params["mu"],

        params["sigma"]
    )


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    print("\nFetching Market Features...\n")

    df = get_all_market_features()

    print(df)

    save_market_features()

