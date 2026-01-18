"""
Master script to build all paper figures.

Runs all figure-generation scripts in sequence and reports success/failure.
"""
from __future__ import annotations

from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from Paper.scripts.figures import (
    generate_cost_drag_figure,
    generate_motivation_figure,
    generate_pv_figures,
    generate_timeline_figure,
    generate_weight_area_figures,
)


def run_generator(name: str, generator_func) -> bool:
    """Run a figure generator and report status."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print('='*60)
    try:
        generator_func()
        print(f"✓ {name} completed successfully")
        return True
    except Exception as e:
        print(f"✗ {name} failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    """Build all figures."""
    print("Starting figure generation pipeline...")
    print(f"Output directory: Paper/LaTeX/figures/")
    
    results = {}
    
    # Generate each figure set
    results['Motivation Figure'] = run_generator(
        'Motivation Figure (Six-Month Outlier Inflation)',
        generate_motivation_figure.main
    )
    
    results['Timeline Figure'] = run_generator(
        'No-Look-Ahead Timeline Schematic',
        generate_timeline_figure.main
    )
    
    results['PV Figures'] = run_generator(
        'PV Figures (Curves & Heatmaps)',
        generate_pv_figures.main
    )
    
    results['Cost Drag Figure'] = run_generator(
        'Transaction Cost Drag Figure',
        generate_cost_drag_figure.main
    )

    results['Weight Area Figures'] = run_generator(
        'Strategy Weights (Stacked Areas, 10% Risk)',
        generate_weight_area_figures.main
    )
    
    # Summary
    print(f"\n{'='*60}")
    print("FIGURE GENERATION SUMMARY")
    print('='*60)
    
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{status:12} | {name}")
    
    total = len(results)
    succeeded = sum(results.values())
    print(f"\nTotal: {succeeded}/{total} figure sets generated successfully")
    
    if succeeded < total:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
