#!/usr/bin/env python3
"""
Re-render the paper's figures in the siddhants.com palette, for the explainer video.

This drives the paper's own generators in Paper/scripts/figures/ so the data and
the plot construction are untouched; only presentation is overridden. Nothing in
Paper/ is modified and the published figures in Paper/LaTeX/figures/ are never
written to: output is redirected to Video/public/figures-brand/.

Three hooks do the work:
  1. rcParams            - dark ground, brand text ramp, transparent export
  2. named-colour remap  - the generators hardcode 'black', 'red', 'lightblue' etc.
  3. two call patches    - the ETF colour map and the 'RdYlGn' heatmap colormaps

Usage:  python tools/render_brand_figures.py
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgba

VIDEO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = VIDEO_ROOT.parent
# Not under public/: the video draws its own charts now, and anything in
# public/ is copied into every render bundle. These are kept as a standalone
# brand-coloured set of the paper's figures for slides and posts.
OUT_DIR = VIDEO_ROOT / "figures-brand"
sys.path.insert(0, str(PROJECT_ROOT))  # so `Paper.scripts...` imports resolve

# ---------------------------------------------------------------- palette ----
# Mirrors Video/src/brand.ts, which mirrors the website's Shell.astro.
GROUND = "#050C0F"
TEXT = "#DEEAEC"
TEXT2 = "#B4C6CA"
TEXT3 = "#8CA2A6"
PEACOCK = "#208EC5"
GLOW = "#45B5ED"
AZURE = "#2F6FE8"
IRIS = "#6A5AD8"
WARN = "#E0A88F"
RULE = "#162C34"
EDGE = "#24424C"

# Ten categorical bands for the nine sector ETFs plus cash. The site only ships
# four accents, so this extends them around the same cool arc, keeping the one
# warm accent, and holds cash at a muted slate as the original figures did.
ETF_RAMP = [
    "#45B5ED",  # glow
    "#17556F",  # deep teal
    "#E0A88F",  # warn
    "#8ED3F0",  # pale glow
    "#2E9E8F",  # teal
    "#7FCBB8",  # mint
    "#2F6FE8",  # azure
    "#C98BC0",  # mauve
    "#6A5AD8",  # iris
]
CASH = "#384D55"

STRATEGY_BRAND = {
    "S&P BnH": TEXT3,
    "Volatility": GLOW,
    "MAD": WARN,
    "IQR": IRIS,
    "95%": "#2E9E8F",
}

# Dark at the low end, bright at the high end. Two constraints shape the stops:
# the generators switch the cell label between 'white' and 'black' at the data
# midpoint, so luminance has to cross over at 0.5 or labels land dark-on-dark;
# and the floor has to stay clear of the #050C0F ground or the coldest cells
# dissolve into the background.
BRAND_SEQ = LinearSegmentedColormap.from_list(
    "brand_seq",
    [
        (0.00, "#0E3A4B"),
        (0.30, "#156A90"),
        (0.48, "#2190C6"),
        (0.52, "#4FB2E2"),
        (0.72, "#93D4F2"),
        (1.00, "#DCF1FC"),
    ],
)

# ------------------------------------------------- named-colour remapping ----
# The generators pass literal colour names. Remap them per figure family: in the
# line/box charts 'black' is a stroke and must read light, while in the heatmaps
# 'black' is a label on a pale cell and must read dark.
CHART_PROFILE = {
    "black": TEXT2,
    "white": GROUND,
    "gray": "#5A7078",
    "grey": "#5A7078",
    "red": WARN,
    "r": WARN,  # the rebalance marker is drawn with the 'r--' format shorthand
    "orange": "#E8C07A",
    "green": "#7FCBB8",
    "lightblue": "#1B4C5E",
    "darkblue": "#8ED3F0",
    # The timeline schematic hardcodes hex rather than colour names. Its two
    # window boxes were pale fills with dark labels; on a dark ground the fills
    # have to invert or the labels vanish. matplotlib checks this same registry
    # before it parses a string as hex, so these keys are honoured too.
    "#d4f1d4": "#123B38",  # estimation window fill
    "#2ca02c": "#7FCBB8",  # estimation window stroke + arrow
    "#d4e6f1": "#0F3448",  # holding window fill
    "#1f77b4": "#45B5ED",  # holding window stroke + arrow
}
HEAT_PROFILE = {
    "white": "#EAF3F5",
    "black": "#06222A",
}


@contextlib.contextmanager
def named_colours(overrides: dict[str, str]):
    """Temporarily point matplotlib's colour registry at brand equivalents."""
    reg = mcolors._colors_full_map
    saved = {k: reg[k] for k in overrides if k in reg}
    try:
        reg.update({k: to_rgba(v) for k, v in overrides.items()})
        yield
    finally:
        for k in overrides:
            reg.pop(k, None)
        reg.update(saved)


def apply_brand_theme() -> None:
    plt.rcParams.update({
        "figure.facecolor": GROUND,
        "axes.facecolor": "none",
        "savefig.facecolor": GROUND,
        "savefig.transparent": True,   # composites onto the video's ambient haze
        "text.color": TEXT2,
        "axes.labelcolor": TEXT2,
        "axes.titlecolor": TEXT,
        "xtick.color": TEXT3,
        "ytick.color": TEXT3,
        "axes.edgecolor": EDGE,
        "grid.color": RULE,
        "grid.linewidth": 0.6,
        "legend.facecolor": "none",
        "legend.edgecolor": EDGE,
        "legend.labelcolor": TEXT2,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
    })


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Importing figure_helpers runs the paper's own light theme; override after.
    from Paper.scripts.utils import figure_helpers as fh

    fh.FIGURES_ROOT = OUT_DIR
    fh.STRATEGY_COLORS.update(STRATEGY_BRAND)

    from Paper.scripts.figures import (
        generate_cost_drag_figure,
        generate_motivation_figure,
        generate_pv_figures,
        generate_timeline_figure,
        generate_weight_area_figures,
    )

    # save_figure captured FIGURES_ROOT at import time in each module's namespace
    # only via the function, which reads fh.FIGURES_ROOT at call time -- but the
    # modules imported `save_figure` itself, so patch the shared function's globals.
    fh.save_figure.__globals__["FIGURES_ROOT"] = OUT_DIR

    for mod in (
        generate_cost_drag_figure,
        generate_motivation_figure,
        generate_pv_figures,
        generate_timeline_figure,
        generate_weight_area_figures,
    ):
        if hasattr(mod, "STRATEGY_COLORS"):
            mod.STRATEGY_COLORS.update(STRATEGY_BRAND)

    # ETF bands for the stacked-area charts.
    def brand_color_map(columns):
        out = {}
        i = 0
        for c in columns:
            if str(c).upper() == "CSH":
                out[c] = CASH
            else:
                out[c] = ETF_RAMP[i % len(ETF_RAMP)]
                i += 1
        return out

    generate_weight_area_figures._get_color_map = brand_color_map

    # Heatmap colormaps: the generators pass the names as strings.
    # matplotlib refuses to re-register a builtin name, so write into the
    # registry's backing store, which is what a string cmap= resolves against.
    for _name, _cm in (("RdYlGn", BRAND_SEQ), ("RdYlGn_r", BRAND_SEQ.reversed())):
        matplotlib.colormaps._cmaps[_name] = _cm

    apply_brand_theme()

    steps = [
        ("motivation", generate_motivation_figure.main, CHART_PROFILE),
        ("timeline", generate_timeline_figure.main, CHART_PROFILE),
        ("cost drag", generate_cost_drag_figure.main, CHART_PROFILE),
        ("pv curves + heatmaps", generate_pv_figures.main, HEAT_PROFILE),
        ("weight areas", generate_weight_area_figures.main, CHART_PROFILE),
    ]

    # The published full-sample MDD figure has no generator in Paper/scripts/;
    # this rebuilds it from build_fullsample_mdd's own reconstruction.
    def fullsample_mdd():
        sys.path.insert(0, str(VIDEO_ROOT / "tools"))
        import build_fullsample_mdd_figure as fsm

        grids = fsm.build_grid()
        problems = fsm.check(grids)
        if problems:
            raise AssertionError(
                "full-sample MDD does not match the published figure:\n  "
                + "\n  ".join(problems)
            )
        print(f"  full-sample MDD agrees with the published figure in all "
              f"{len(fsm.PANELS) * 12} cells; max deviation "
              f"{fsm.max_deviation(grids):.3f}pp")
        fh.save_figure(fsm.plot(grids), "heatmap_mdd_fullsample_zero_cost.png")

    steps.append(("full-sample MDD heatmap", fullsample_mdd, HEAT_PROFILE))

    failed = []
    for name, fn, profile in steps:
        print(f"\n=== {name} ===")
        try:
            with named_colours(profile):
                apply_brand_theme()  # generators may re-apply the paper theme
                fn()
        except Exception as exc:  # keep going; report at the end
            import traceback

            traceback.print_exc()
            failed.append((name, exc))

    # The timeline schematic's y-limits leave a third of the canvas empty, which
    # on a transparent export is just dead space that shrinks the figure in the
    # video. Trim it. Deliberately not applied to the tenure series: those four
    # cross-dissolve on top of each other and must keep a common bounding box.
    timeline = OUT_DIR / "no_lookahead_timeline.png"
    if timeline.exists():
        try:
            from PIL import Image

            im = Image.open(timeline).convert("RGBA")
            bbox = im.getbbox()  # ignores fully transparent border
            if bbox:
                im.crop(bbox).save(timeline)
                print(f"  trimmed timeline {im.size} -> {(bbox[2]-bbox[0], bbox[3]-bbox[1])}")
        except ImportError:
            print("  (Pillow missing; timeline left untrimmed)")

    print("\n" + "=" * 60)
    produced = sorted(p.name for p in OUT_DIR.glob("*.png"))
    print(f"{len(produced)} figures -> {OUT_DIR}")
    for p in produced:
        print("  ", p)
    if failed:
        print("\nFAILED:")
        for name, exc in failed:
            print(f"  {name}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
