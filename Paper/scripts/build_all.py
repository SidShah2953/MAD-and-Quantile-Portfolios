#!/usr/bin/env python3
"""
Main build script for paper artifacts.

Runs all table and figure generation scripts before PDF compilation
to ensure all paper content is up to date.

Usage:
    python build_all.py              # Build both tables and figures
    python build_all.py --tables-only # Only regenerate tables
    python build_all.py --figures-only # Only regenerate figures
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SCRIPT_DIR = Path(__file__).parent


def run_step(name: str, func, *args) -> tuple[bool, float]:
    """
    Run a build step and report timing.
    
    Returns:
        (success, elapsed_time)
    """
    print(f"\n{'='*70}")
    print(f"STEP: {name}")
    print('='*70)
    
    start = time.time()
    try:
        func(*args)
        elapsed = time.time() - start
        print(f"✓ {name} completed successfully in {elapsed:.2f}s")
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ {name} failed after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return False, elapsed


def build_tables() -> bool:
    """Generate all LaTeX tables."""
    from Paper.scripts.tables.build_paper_tables import main as build_tables_main
    success, _ = run_step("Generate LaTeX Tables", build_tables_main)
    return success


def build_figures() -> bool:
    """Generate all figures."""
    from Paper.scripts.figures.build_all_figures import main as build_figures_main
    success, _ = run_step("Generate Figures", build_figures_main)
    return success


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build all paper artifacts (tables and figures)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_all.py                  # Build everything
  python build_all.py --tables-only    # Only regenerate tables
  python build_all.py --figures-only   # Only regenerate figures
        """
    )
    parser.add_argument(
        '--tables-only',
        action='store_true',
        help='Only regenerate tables'
    )
    parser.add_argument(
        '--figures-only',
        action='store_true',
        help='Only regenerate figures'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("PAPER ARTIFACT BUILD PIPELINE")
    print("="*70)
    print(f"Working directory: {Path.cwd()}")
    print(f"Script directory: {SCRIPT_DIR}")
    
    results = {}
    overall_start = time.time()
    
    # Determine what to build
    build_all = not (args.tables_only or args.figures_only)
    
    if build_all or args.tables_only:
        results['Tables'] = build_tables()
    
    if build_all or args.figures_only:
        results['Figures'] = build_figures()
    
    overall_elapsed = time.time() - overall_start
    
    # Print summary
    print(f"\n{'='*70}")
    print("BUILD SUMMARY")
    print('='*70)
    
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{status:12} | {name}")
    
    total = len(results)
    succeeded = sum(results.values())
    
    print(f"\nTotal: {succeeded}/{total} steps completed successfully")
    print(f"Total time: {overall_elapsed:.2f}s")
    
    if succeeded < total:
        print("\n⚠ Some steps failed. Check the output above for details.")
        return 1
    else:
        print("\n✓ All artifacts generated successfully!")
        print("  Ready to compile LaTeX: cd Paper/LaTeX && ./compile.sh")
        return 0


if __name__ == '__main__':
    import sys

    sys.exit(main())
