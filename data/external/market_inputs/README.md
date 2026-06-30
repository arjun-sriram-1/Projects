# Staged Market Inputs

Use this folder for free market datasets that are easier to download as CSV than call through an API.

The ingestion pipeline automatically reads every `*.csv` file in this folder when `csv` or `staged_csv` is included in the provider list. The live market refresh includes this folder by default.

## Required Columns

```csv
date,asset,price
2024-01-31,global_pmi,50.4
2024-01-31,opec_production,26650
2024-01-31,iata_passenger_traffic,102.1
```

You may use `value` instead of `price`.

## Optional Columns

```csv
source_id,asset_name,data_source,frequency,units
```

Example:

```csv
date,asset,price,source_id,asset_name,data_source,frequency,units
2024-01-31,global_pmi,50.4,JPM_GLOBAL_PMI,Global PMI,staged_csv:global_pmi,monthly,index
2024-01-31,opec_production,26650,JODI_OPEC_CRUDE,OPEC Crude Production,staged_csv:opec,monthly,thousand_barrels_per_day
2024-01-31,iata_passenger_traffic,102.1,IATA_RPK,Air Passenger Traffic,staged_csv:iata,monthly,index
```

## Canonical Asset Names

- `global_pmi`
- `opec_production`
- `iata_passenger_traffic`
- `eia_crude_inventories`
- `jet_crack_spread`

`jet_crack_spread` is normally calculated automatically from `jet_fuel_proxy * 42 - brent_oil`, so you only need to stage it if you have a better source.

## Free Source Fit

- FRED API: Brent, WTI, S&P 500, VIX, DXY proxy, US 10Y, US 2Y, yield curve, CPI, PMI proxy.
- EIA API: Jet fuel spot price, heating oil proxy, Brent/WTI petroleum series, crude inventories.
- Staged CSV: OPEC production from JODI/OPEC downloads, IATA passenger traffic, third-party/global PMI files.

