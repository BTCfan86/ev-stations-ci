"""
CI entry point. Usage (from repo root):

    python ci/ci_runner.py wa_pct
    python ci/ci_runner.py wa_mkt_share
    python ci/ci_runner.py nc
    python ci/ci_runner.py ny
    python ci/ci_runner.py md
    python ci/ci_runner.py ca
    python ci/ci_runner.py combined

Your scripts call plt.show(), which is a no-op on a headless GitHub Actions
runner. This patches plt.show to save each figure to ci_output/ instead, so
you get real PNGs back as a workflow artifact. It also writes out any
DataFrame the target function returns as a CSV, so you can inspect the
actual numbers, not just the chart.
"""
import sys
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # headless backend - must happen before pyplot is imported anywhere
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "ci_output"
OUT_DIR.mkdir(exist_ok=True)

_fig_counter = {"n": 0}

def _save_instead_of_show(*args, **kwargs):
    _fig_counter["n"] += 1
    out_path = OUT_DIR / f"figure_{_fig_counter['n']:02d}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[ci_runner] saved chart -> {out_path}")

plt.show = _save_instead_of_show

# Make the Renewables.* dotted imports resolve regardless of OS or cwd
sys.path.insert(0, str(REPO_ROOT))


def _write_result(name, result):
    if isinstance(result, pd.DataFrame):
        out_path = OUT_DIR / f"{name}.csv"
        result.to_csv(out_path)
        print(f"[ci_runner] saved data -> {out_path} ({len(result)} rows)")
    elif result is not None:
        print(f"[ci_runner] {name} returned: {result!r}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    target = sys.argv[1]

    if target == "wa_pct":
        from Renewables.EV_Data.WA_EVs_v01 import WA_EV_Pct
        _write_result("wa_pct", WA_EV_Pct())

    elif target == "wa_mkt_share":
        from Renewables.EV_Data.WA_EVs_v01 import WA_EV_Mkt_Share
        _write_result("wa_mkt_share", WA_EV_Mkt_Share())

    elif target == "nc":
        from Renewables.EV_Data.NC_EVs_v01 import NC_Monthly_EVs
        _write_result("nc", NC_Monthly_EVs())

    elif target == "ny":
        from Renewables.EV_Data.NY_EVs_v01 import NY_Registrations
        result = NY_Registrations()
        for i, df in enumerate(result):
            _write_result(f"ny_{i}", df)

    elif target == "md":
        from Renewables.EV_Data.MD_EVs_v01 import MD_Monthly_EVs
        MD_Monthly_EVs()  # currently just prints - see note in project review

    elif target == "ca":
        from Renewables.EV_Data.CA_EVs_v01 import CA_Monthly_EVs
        CA_Monthly_EVs()  # currently just prints - see note in project review

    elif target == "combined":
        from Renewables.EV_Data.Combined_EV_Data_v01 import combined_EV_share
        combined_EV_share()

    elif target == "ev_stations":
        os.environ.setdefault("EV_BASE_DIR", str(REPO_ROOT / "Renewables" / "EV_Stations"))
        from Renewables.EV_Stations.EV_Stations_v08 import EV_Stations
        EV_Stations()

    else:
        print(f"Unknown target: {target}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
