
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Resolve paths relative to this Python file
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "process_data.csv"
REPORT_DIR = BASE_DIR / "reports"

# Demonstration limits only, not factory-approved process limits
LIMITS = {
    "temperature_c": (20.0, 28.0),
    "pressure_kpa": (98.5, 102.0),
    "defect_count": (0, 3),
}

REQUIRED_COLUMNS = [
    "lot_id",
    "wafer_id",
    "temperature_c",
    "pressure_kpa",
    "defect_count",
]

NUMERIC_COLUMNS = [
    "temperature_c",
    "pressure_kpa",
    "defect_count",
]


def validate_process_data(df):
    """Validate required fields and process measurement values."""
    if df.empty:
        raise ValueError("The input CSV contains no readings.")

    missing_columns = [
        col for col in REQUIRED_COLUMNS if col not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    df = df.copy()

    # Validate lot and wafer identifiers
    for column in ["lot_id", "wafer_id"]:
        df[column] = df[column].astype("string").str.strip()
        invalid_ids = df[column].isna() | df[column].eq("")
        if invalid_ids.any():
            raise ValueError(
                f"Missing or blank identifiers in '{column}'."
            )

    # Convert measurements and reject missing/non-numeric values
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

        values = df[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(
                f"'{column}' contains missing or non-finite values."
            )

    # Defect counts must be non-negative whole numbers
    defects = df["defect_count"]
    if (defects < 0).any() or (defects % 1 != 0).any():
        raise ValueError(
            "'defect_count' must contain non-negative whole numbers."
        )

    return df


def analyze_readings(df, limits=None):
    """Validate readings and flag values outside configured limits."""
    if limits is None:
        limits = LIMITS

    df = validate_process_data(df)

    reasons = [[] for _ in range(len(df))]

    for column in NUMERIC_COLUMNS:
        if column not in limits:
            raise ValueError(f"No limits configured for '{column}'.")

        low, high = limits[column]
        if low > high:
            raise ValueError(f"Invalid limits for '{column}'.")

        outside = ~df[column].between(low, high)

        for position, is_outside in enumerate(outside.to_numpy()):
            if is_outside:
                reasons[position].append(column)

    df["abnormal_reasons"] = [
        "; ".join(items) for items in reasons
    ]
    df["abnormal"] = df["abnormal_reasons"].ne("")
    df["status"] = np.where(
        df["abnormal"],
        "REVIEW",
        "WITHIN_DEMO_LIMITS",
    )

    return df


def save_reports(df):
    """Save summary tables, flagged readings and trend plots."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    summary = df[NUMERIC_COLUMNS].agg(
        ["mean", "min", "max", "std"]
    ).T
    summary.index.name = "parameter"

    summary.to_csv(REPORT_DIR / "statistical_summary.csv")
    df.to_csv(
        REPORT_DIR / "analyzed_readings.csv",
        index=False,
    )
    df[df["abnormal"]].to_csv(
        REPORT_DIR / "flagged_readings.csv",
        index=False,
    )

    parameters = [
        ("temperature_c", "Temperature (°C)"),
        ("pressure_kpa", "Pressure (kPa)"),
        ("defect_count", "Defect Count"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(10, 9))

    try:
        for ax, (column, title) in zip(axes, parameters):
            ax.plot(
                np.arange(1, len(df) + 1),
                df[column],
                marker="o",
                markersize=3,
            )
            ax.set_title(title)
            ax.set_xlabel("Reading Number")
            ax.set_ylabel(title)
            ax.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig(
            REPORT_DIR / "process_trends.png",
            dpi=160,
            bbox_inches="tight",
        )
    finally:
        plt.close(fig)

    return summary


def main():
    try:
        if not DATA_FILE.is_file():
            raise FileNotFoundError(
                f"Input file not found: {DATA_FILE}"
            )

        df = pd.read_csv(DATA_FILE)
        analyzed = analyze_readings(df)
        summary = save_reports(analyzed)

        print("\nSEMICONDUCTOR PROCESS DATA ANALYZER")
        print("=" * 45)
        print("\nSTATISTICAL SUMMARY")
        print(summary.round(2))
        print("\nTotal readings:", len(analyzed))
        print(
            "Readings flagged for review:",
            int(analyzed["abnormal"].sum()),
        )
        print("Reports saved in:", REPORT_DIR)
        print("Analysis completed successfully!")

    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        ValueError,
        OSError,
    ) as exc:
        print(f"\nAnalysis failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
