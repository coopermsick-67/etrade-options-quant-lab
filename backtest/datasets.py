"""Validated file-backed historical option quote datasets for backtests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.engine import HistoricalBar


class HistoricalDatasetError(ValueError):
    """Raised when a historical dataset cannot be used safely."""


REQUIRED_COLUMNS = frozenset(
    {"timestamp", "close", "option_mid", "option_bid", "option_ask"}
)
SUPPORTED_SUFFIXES = frozenset({".csv", ".parquet"})


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    path: str
    format: str
    rows: int
    start: str | None
    end: str | None
    symbols: tuple[str, ...]


def _safe_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HistoricalDatasetError("dataset path must stay inside HISTORICAL_DATA_DIR") from exc
    if candidate.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise HistoricalDatasetError("dataset must be a CSV or Parquet file")
    if not candidate.is_file():
        raise HistoricalDatasetError("historical dataset was not found")
    return candidate


def _parse_timestamp_series(frame: pd.DataFrame) -> pd.Series:
    raw = pd.to_datetime(frame["timestamp"], errors="coerce")
    if raw.isna().any():
        raise HistoricalDatasetError("timestamp contains invalid values")
    if raw.dt.tz is None:
        raise HistoricalDatasetError("timestamp must include an explicit timezone offset")
    return raw.dt.tz_convert(UTC)


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path)
        else:
            frame = pd.read_parquet(path)
    except (OSError, ImportError, ValueError) as exc:
        raise HistoricalDatasetError(f"could not read dataset: {exc}") from exc
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise HistoricalDatasetError(f"dataset is missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise HistoricalDatasetError("dataset is empty")
    return frame


def _frame_with_normalized_timestamps(path: Path) -> pd.DataFrame:
    frame = _read_frame(path).copy()
    frame["timestamp"] = _parse_timestamp_series(frame)
    if frame["timestamp"].duplicated().any():
        raise HistoricalDatasetError("dataset contains duplicate timestamps")
    return frame.sort_values("timestamp", kind="stable").reset_index(drop=True)


def inspect_dataset(root: Path, relative_path: str) -> DatasetInfo:
    path = _safe_path(root, relative_path)
    frame = _frame_with_normalized_timestamps(path)
    symbols: tuple[str, ...] = ()
    if "symbol" in frame.columns:
        symbols = tuple(sorted({str(value).strip().upper() for value in frame["symbol"] if str(value).strip()}))
    timestamps = frame["timestamp"]
    return DatasetInfo(
        name=path.name,
        path=path.relative_to(root.resolve()).as_posix(),
        format=path.suffix.lower().lstrip("."),
        rows=len(frame),
        start=timestamps.iloc[0].isoformat(),
        end=timestamps.iloc[-1].isoformat(),
        symbols=symbols,
    )


def list_datasets(root: Path) -> list[DatasetInfo]:
    root.mkdir(parents=True, exist_ok=True)
    infos: list[DatasetInfo] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            infos.append(inspect_dataset(root, relative))
        except HistoricalDatasetError:
            # The catalog reports only usable files. Uploads are validated before
            # they are retained; pre-existing invalid files stay out of runs.
            continue
    return infos


def _date_bound(value: date | None, *, end: bool) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max if end else time.min, tzinfo=UTC)


def load_bars(
    root: Path,
    relative_path: str,
    *,
    symbol: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[HistoricalBar, ...]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HistoricalDatasetError("start_date cannot be after end_date")
    path = _safe_path(root, relative_path)
    frame = _frame_with_normalized_timestamps(path)
    if symbol:
        if "symbol" not in frame.columns:
            raise HistoricalDatasetError("symbol filter requires a symbol column")
        wanted = symbol.strip().upper()
        frame = frame[frame["symbol"].astype(str).str.strip().str.upper() == wanted]
    start = _date_bound(start_date, end=False)
    end = _date_bound(end_date, end=True)
    if start is not None:
        frame = frame[frame["timestamp"] >= start]
    if end is not None:
        frame = frame[frame["timestamp"] <= end]
    if len(frame) < 2:
        raise HistoricalDatasetError("selected date range must contain at least two observations")
    bars: list[HistoricalBar] = []
    for row in frame.to_dict(orient="records"):
        try:
            bars.append(
                HistoricalBar(
                    timestamp=row["timestamp"].to_pydatetime(),
                    close=float(row["close"]),
                    option_mid=float(row["option_mid"]),
                    option_bid=float(row["option_bid"]),
                    option_ask=float(row["option_ask"]),
                    multiplier=float(row.get("multiplier", 100.0)),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HistoricalDatasetError(f"invalid historical row: {exc}") from exc
    return tuple(bars)


def serialize_dataset(info: DatasetInfo) -> dict[str, Any]:
    return {
        "name": info.name,
        "path": info.path,
        "format": info.format,
        "rows": info.rows,
        "start": info.start,
        "end": info.end,
        "symbols": list(info.symbols),
    }
