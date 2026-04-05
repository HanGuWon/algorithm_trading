from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from longonly_research_utils import StrategyVariant, ensure_directory, make_timerange, parse_backtest_zip, run_backtest, snapshot_path, write_temp_config


@dataclass(frozen=True)
class SweepProfile:
    label: str
    changed_parameter: str
    overrides: dict[str, float]


FROZEN_DEFAULTS = {
    "vol_z_min": 1.00,
    "price_z_threshold": 1.50,
    "bb_width_min": 0.020,
    "adx_1h_max": 24,
    "slope_cap": 0.0060,
}

PARAMETER_SPECS = {
    "vol_z_min": {"type": "DecimalParameter", "low": 0.50, "high": 3.00, "decimals": 2},
    "price_z_threshold": {"type": "DecimalParameter", "low": 1.00, "high": 2.50, "decimals": 2},
    "bb_width_min": {"type": "DecimalParameter", "low": 0.005, "high": 0.100, "decimals": 3},
    "adx_1h_max": {"type": "IntParameter", "low": 16, "high": 32, "decimals": 0},
    "slope_cap": {"type": "DecimalParameter", "low": 0.0010, "high": 0.0200, "decimals": 4},
}

DEFAULT_SWEEP = [
    SweepProfile(label="baseline", changed_parameter="baseline", overrides={}),
    SweepProfile(label="vol_z_min_down", changed_parameter="vol_z_min", overrides={"vol_z_min": 0.85}),
    SweepProfile(label="vol_z_min_up", changed_parameter="vol_z_min", overrides={"vol_z_min": 1.15}),
    SweepProfile(label="price_z_threshold_down", changed_parameter="price_z_threshold", overrides={"price_z_threshold": 1.35}),
    SweepProfile(label="price_z_threshold_up", changed_parameter="price_z_threshold", overrides={"price_z_threshold": 1.65}),
    SweepProfile(label="bb_width_min_down", changed_parameter="bb_width_min", overrides={"bb_width_min": 0.015}),
    SweepProfile(label="bb_width_min_up", changed_parameter="bb_width_min", overrides={"bb_width_min": 0.025}),
    SweepProfile(label="adx_1h_max_down", changed_parameter="adx_1h_max", overrides={"adx_1h_max": 22}),
    SweepProfile(label="adx_1h_max_up", changed_parameter="adx_1h_max", overrides={"adx_1h_max": 26}),
    SweepProfile(label="slope_cap_down", changed_parameter="slope_cap", overrides={"slope_cap": 0.0050}),
    SweepProfile(label="slope_cap_up", changed_parameter="slope_cap", overrides={"slope_cap": 0.0070}),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small local parameter-stability sweep around the frozen long-only candidate.")
    parser.add_argument("--anchor", default="2024-01-01")
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--logs-dir", default="docs/validation/logs/longonly_parameter_stability")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_parameter_stability")
    parser.add_argument(
        "--db-url",
        default="sqlite:///user_data/tradesv3_volatility_rotation_mr_longonly_parameter_stability.sqlite",
    )
    return parser.parse_args()


def format_default_value(name: str, value: float) -> str:
    spec = PARAMETER_SPECS[name]
    if spec["type"] == "IntParameter":
        return str(int(value))
    return f"{value:.{int(spec['decimals'])}f}"


def build_strategy_source(base_strategy_file: Path, class_name: str, overrides: dict[str, float]) -> str:
    params = {**FROZEN_DEFAULTS, **overrides}
    lines = [
        "from __future__ import annotations",
        "",
        "import importlib.util",
        "",
        f"_STRATEGY_PATH = {json.dumps(str(base_strategy_file.resolve()))}",
        "_SPEC = importlib.util.spec_from_file_location('volatility_rotation_mr_base_module', _STRATEGY_PATH)",
        "if _SPEC is None or _SPEC.loader is None:",
        "    raise RuntimeError(f'Unable to import strategy file {_STRATEGY_PATH}')",
        "_MODULE = importlib.util.module_from_spec(_SPEC)",
        "_SPEC.loader.exec_module(_MODULE)",
        "",
        "DecimalParameter = _MODULE.DecimalParameter",
        "IntParameter = _MODULE.IntParameter",
        "",
        f"class {class_name}(_MODULE.VolatilityRotationMRDiagnosticLongOnly):",
    ]
    for parameter_name in ("vol_z_min", "price_z_threshold", "bb_width_min", "adx_1h_max", "slope_cap"):
        spec = PARAMETER_SPECS[parameter_name]
        value = format_default_value(parameter_name, params[parameter_name])
        if spec["type"] == "IntParameter":
            line = f"    {parameter_name} = IntParameter({int(spec['low'])}, {int(spec['high'])}, default={value}, space='buy', optimize=True)"
        else:
            line = (
                f"    {parameter_name} = DecimalParameter("
                f"{spec['low']:.{int(spec['decimals'])}f}, "
                f"{spec['high']:.{int(spec['decimals'])}f}, "
                f"default={value}, decimals={int(spec['decimals'])}, space='buy', optimize=True)"
            )
        lines.append(line)
    lines.extend(
        [
            "",
            "    @property",
            "    def version(self) -> str:",
            f"        return '{class_name}'",
            "",
        ]
    )
    return "\n".join(lines)


def summarize_stability(profile_rows: pd.DataFrame) -> str:
    baseline = profile_rows[profile_rows["label"] == "baseline"].iloc[0]
    perturbed = profile_rows[profile_rows["label"] != "baseline"].copy()
    if perturbed.empty:
        return "insufficient_data"
    if (perturbed["profit_usdt"] <= 0).any():
        return "fragile"
    if (perturbed["raw_trade_count"] < max(5, int(baseline["raw_trade_count"] * 0.6))).any():
        return "fragile"
    if (perturbed["profit_usdt"] < float(baseline["profit_usdt"]) * 0.6).any():
        return "fragile"
    return "stable"


def main() -> None:
    args = parse_args()
    snapshot = snapshot_path(Path(args.snapshot_dir), args.anchor, args.snapshot_top_n)
    snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))
    pair_count = len(snapshot_payload["exchange"]["pair_whitelist"])
    timerange, _, _ = make_timerange(pd.Timestamp(args.anchor, tz="UTC"), args.window_months)
    base_strategy_file = Path(args.strategy_path) / "VolatilityRotationMR.py"
    logs_dir = Path(args.logs_dir)
    backtest_dir = Path(args.backtest_dir)
    ensure_directory(logs_dir)
    ensure_directory(backtest_dir)

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="longonly_param_sweep_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        strategy_dir = temp_dir / "strategies"
        ensure_directory(strategy_dir)

        for profile in DEFAULT_SWEEP:
            class_name = f"VolatilityRotationMRDiagnosticLongOnly_{profile.label}"
            strategy_file = strategy_dir / f"{class_name}.py"
            strategy_file.write_text(
                build_strategy_source(base_strategy_file=base_strategy_file, class_name=class_name, overrides=profile.overrides),
                encoding="utf-8",
            )
            variant = StrategyVariant(label=profile.label, strategy=class_name, config_path="")
            config_path = write_temp_config(
                temp_dir=temp_dir,
                base_config=Path(args.base_config),
                snapshot=snapshot,
                variant=variant,
                db_url=args.db_url,
            )
            zip_path = run_backtest(
                python_executable=Path(sys.executable),
                config_path=config_path,
                strategy_path=strategy_dir,
                timerange=timerange,
                logs_dir=logs_dir,
                backtest_dir=backtest_dir,
                anchor_label=f"{args.anchor}_{profile.label}",
                variant=variant,
            )
            strategy_data, _ = parse_backtest_zip(zip_path, class_name)
            overrides = {**FROZEN_DEFAULTS, **profile.overrides}
            rows.append(
                {
                    "label": profile.label,
                    "changed_parameter": profile.changed_parameter,
                    "anchor": args.anchor,
                    "window_months": args.window_months,
                    "timerange": timerange,
                    "pair_count": pair_count,
                    "vol_z_min": overrides["vol_z_min"],
                    "price_z_threshold": overrides["price_z_threshold"],
                    "bb_width_min": overrides["bb_width_min"],
                    "adx_1h_max": int(overrides["adx_1h_max"]),
                    "slope_cap": overrides["slope_cap"],
                    "raw_trade_count": int(strategy_data.get("total_trades", 0)),
                    "profit_pct": round(float(strategy_data.get("profit_total", 0.0)) * 100.0, 2),
                    "profit_usdt": round(float(strategy_data.get("profit_total_abs", 0.0)), 3),
                    "max_drawdown_pct": round(float(strategy_data.get("max_drawdown_account", 0.0)) * 100.0, 2),
                    "results_zip": zip_path.name,
                }
            )

    frame = pd.DataFrame(rows)
    output_csv = Path(args.output_csv)
    ensure_directory(output_csv.parent)
    frame.to_csv(output_csv, index=False)

    stability = summarize_stability(frame)
    lines = [
        "# Long-Only Parameter Stability",
        "",
        "> Local neighborhood sweep only. This is not a new optimization pass and does not nominate a replacement candidate.",
        "",
        f"- Frozen evaluation window: `{args.anchor} -> {(pd.Timestamp(args.anchor) + pd.DateOffset(months=args.window_months)).strftime('%Y-%m-%d')}`",
        f"- Pair count: `{pair_count}`",
        f"- Overall classification: `{stability}`",
        "",
        "## Frozen Defaults",
        "",
        pd.DataFrame([{"parameter": key, "frozen_value": value} for key, value in FROZEN_DEFAULTS.items()]).to_markdown(index=False),
        "",
        "## Sweep Results",
        "",
        frame[
            [
                "label",
                "changed_parameter",
                "vol_z_min",
                "price_z_threshold",
                "bb_width_min",
                "adx_1h_max",
                "slope_cap",
                "raw_trade_count",
                "profit_pct",
                "profit_usdt",
                "max_drawdown_pct",
            ]
        ].to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "The frozen defaults stay in place unless the neighborhood evidence is overwhelmingly better, which this sweep is not designed to prove.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "& .\\.venv-freqtrade\\Scripts\\python.exe scripts\\run_longonly_parameter_stability.py `",
        f"  --anchor {args.anchor} `",
        f"  --window-months {args.window_months} `",
        f"  --output-md {Path(args.output_md).as_posix()} `",
        f"  --output-csv {output_csv.as_posix()} `",
        f"  --logs-dir {logs_dir.as_posix()} `",
        f"  --backtest-dir {backtest_dir.as_posix()}",
        "```",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
