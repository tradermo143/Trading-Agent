"""
Orchestrates both scans across the full ticker universe.
"""
import logging
import pandas as pd
from screener.indicators import compute_all
from screener.scan1_setup import passes_scan1
from screener.scan2_contraction import passes_scan2

logger = logging.getLogger(__name__)


def run_scans(data: dict) -> dict:
    """
    Run Scan 1 (Setup) and Scan 2 (Contraction) across all loaded tickers.

    Returns:
        {
            'scan1': sorted list of tickers passing Setup scan,
            'scan2': sorted list of tickers passing Contraction scan,
            'both':  sorted list of tickers passing both,
        }
    """
    scan1_hits = []
    scan2_hits = []
    errors     = 0
    total      = len(data)

    for i, (ticker, df) in enumerate(data.items()):
        if i % 500 == 0 and i > 0:
            logger.info(f"  {i}/{total} scanned…")
        try:
            df_ind = compute_all(df)
            if passes_scan1(df_ind):
                scan1_hits.append(ticker)
            if passes_scan2(df_ind):
                scan2_hits.append(ticker)
        except Exception as e:
            errors += 1
            logger.debug(f"{ticker} skipped: {e}")

    both = sorted(set(scan1_hits) & set(scan2_hits))

    logger.info(
        f"Results — Setup: {len(scan1_hits)} | "
        f"Contraction: {len(scan2_hits)} | "
        f"Both: {len(both)} | Errors skipped: {errors}"
    )

    return {
        'scan1': sorted(scan1_hits),
        'scan2': sorted(scan2_hits),
        'both':  both,
    }
