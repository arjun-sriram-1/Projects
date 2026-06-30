"""Run the free-source calibration pipeline from staged/downloaded CSV files."""

from __future__ import annotations

import argparse
import json

from api.calibration.build_datasets import build_all
from api.calibration.free_sources import run_downloads
from api.calibration.paths import ensure_calibration_dirs
from api.calibration.registry import build_artifact_manifest
from api.calibration.synthetic_trade_history import generate_synthetic_trade_history
from api.calibration.train_models import train_all
from api.calibration.validation import build_validation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run free-source calibration pipeline.")
    parser.add_argument("--download", action="store_true", help="Download light free sources before building datasets.")
    parser.add_argument("--sec-quarterly", action="store_true")
    parser.add_argument("--world-bank", action="store_true")
    parser.add_argument("--yfinance", action="store_true")
    parser.add_argument("--sec-companyfacts", action="store_true")
    parser.add_argument("--all-light", action="store_true")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument("--market-start", default="2010-01-01")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-proxy-labels", action="store_true")
    parser.add_argument("--no-proxy-lgd", action="store_true")
    parser.add_argument("--generate-synthetic-trades", action="store_true")
    parser.add_argument("--synthetic-trade-rows", type=int, default=5000)
    parser.add_argument("--synthetic-trade-seed", type=int, default=42)
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    ensure_calibration_dirs()
    downloaded = []
    if args.download:
        if args.all_light:
            args.sec_quarterly = True
            args.world_bank = True
            args.yfinance = True
        downloaded = [str(path) for path in run_downloads(args)]
    synthetic_summary = None
    if args.generate_synthetic_trades:
        synthetic_summary = generate_synthetic_trade_history(
            rows=args.synthetic_trade_rows,
            seed=args.synthetic_trade_seed,
            overwrite=args.overwrite,
        )
    dataset_summary = build_all(
        use_proxy_labels=not args.no_proxy_labels,
        use_proxy_lgd=not args.no_proxy_lgd,
    )
    training_summary = train_all()
    validation_summary = None if args.skip_validation else build_validation_report()
    manifest_summary = None if args.skip_manifest else build_artifact_manifest()
    print(json.dumps({
        "downloaded": downloaded,
        "synthetic_trade_history": synthetic_summary,
        "datasets": dataset_summary,
        "training": training_summary,
        "validation": validation_summary,
        "manifest": manifest_summary,
    }, indent=2))


if __name__ == "__main__":
    main()
