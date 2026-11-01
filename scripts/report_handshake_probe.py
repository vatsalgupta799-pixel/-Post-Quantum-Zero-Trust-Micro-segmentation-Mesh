"""Validate and plot a completed handshake-only probe run."""
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_tls_results import compute_statistics, build_comparison


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path)
    a = p.parse_args()
    meta = json.loads((a.run_dir / "metadata.json").read_text(encoding="utf-8"))
    if meta.get("status") != "complete":
        raise ValueError("run is incomplete or failed")
    with (a.run_dir / "raw.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    values = {"classical": [], "hybrid": []}
    expected = {"classical": "x25519", "hybrid": "x25519mlkem768"}
    for row in rows:
        mode = row["mode"]
        if (mode not in expected or row["run_id"] != meta["run_id"] or
                row["success"] != "True" or row["tls_version"] != "TLSv1.3" or
                row["certificate_verified"] != "True" or row["session_reused"] != "False" or
                row["negotiated_group"].lower() != expected[mode]):
            raise ValueError("unverified or unexpected sample")
        duration = float(row["handshake_ms"])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("invalid timing")
        values[mode].append(duration)
    expected_count = 2 * meta["measured_per_block"]
    if any(len(v) != expected_count for v in values.values()):
        raise ValueError("sample count does not match metadata")
    summary = {mode: compute_statistics(v) for mode, v in values.items()}
    comp = build_comparison(summary["classical"], summary["hybrid"])
    out = a.run_dir / "report"
    out.mkdir(exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for mode, data in values.items():
        data = sorted(data)
        axes[0].plot(data, [(i + 1) / len(data) for i in range(len(data))], label=mode)
    axes[0].set(xlabel="TLS handshake duration (ms)", ylabel="Fraction of samples", title="Empirical distribution")
    axes[0].legend()
    axes[0].grid(alpha=.25)
    keys = ("p50_ms", "p95_ms", "p99_ms")
    axes[1].bar([-.2, .8, 1.8], [summary["classical"][k] for k in keys], width=.4, label="classical")
    axes[1].bar([.2, 1.2, 2.2], [summary["hybrid"][k] for k in keys], width=.4, label="hybrid")
    axes[1].set_xticks([0, 1, 2], ["p50", "p95", "p99"])
    axes[1].set(ylabel="TLS handshake duration (ms)", title=f"Percentiles (n={expected_count} per group)")
    axes[1].legend()
    fig.suptitle("TLS 1.3 handshake study — inspect provenance and limitations")
    fig.tight_layout()
    fig.savefig(out / "handshake_comparison.png", dpi=150)
    plt.close(fig)
    lines = ["# TLS handshake study", "", f"Run ID: {meta['run_id']}", "",
             "Timing starts after TCP connects and ends when the TLS handshake completes; certificate validation is included.",
             "The timer includes Python scheduling overhead. See metadata and accompanying study notes for server provenance.", "",
             "| Metric | Classical | Hybrid |", "| --- | ---: | ---: |"]
    for label, key in (("Count", "count"), ("p50 ms", "p50_ms"), ("p95 ms", "p95_ms"),
                       ("p99 ms", "p99_ms"), ("Mean ms", "mean_ms"), ("Sample stddev ms", "stddev_ms"),
                       ("Min ms", "min_ms"), ("Max ms", "max_ms")):
        lines.append(f"| {label} | {summary['classical'][key]:.4f} | {summary['hybrid'][key]:.4f} |")
    lines += ["", "All rows were verified as TLS 1.3, expected group, certificate valid, and not resumed.",
              "Percentiles use linear interpolation; no outliers removed.", "",
              "![Handshake distributions](handshake_comparison.png)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "recalculated.json").write_text(json.dumps({"statistics": summary, "comparison": comp}, indent=2), encoding="utf-8")
    print(f"Validated {len(rows)} observations; wrote {out}")


if __name__ == "__main__":
    main()
