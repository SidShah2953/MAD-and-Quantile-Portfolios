# Paper Build Scripts

This directory contains automated scripts for generating all tables and figures for the research paper.

## Directory Structure

```
scripts/
├── build_all.py              # Main entry point - runs all build steps
├── tables/
│   └── build_paper_tables.py # Generate all LaTeX tables from Output/
├── figures/
│   ├── build_all_figures.py          # Run all figure generators
│   ├── generate_motivation_figure.py # Quarterly outlier inflation plot
│   ├── generate_pv_figures.py        # PV curves and heatmaps
│   └── generate_cost_drag_figure.py  # Transaction cost sensitivity
└── utils/
    ├── figure_helpers.py        # Shared plotting utilities
    └── inspect_output_structure.py # Output debugging tool
```

## Quick Start

### Build Everything (Recommended)
Run before compiling the LaTeX paper to ensure all content is up to date:

```bash
cd Paper/LaTeX
./compile.sh --rebuild
```

Or build artifacts separately:

```bash
python -m Paper.scripts.build_all
```

Then compile the PDF:

```bash
cd ../LaTeX
./compile.sh
```

### Build Only Tables or Figures

```bash
# Only regenerate tables
python -m Paper.scripts.build_all --tables-only

# Only regenerate figures
python -m Paper.scripts.build_all --figures-only
```

## What Gets Generated

### Tables (`Paper/LaTeX/tables/`)
- `summary_zero_cost.tex` - Main results table (0% transaction costs)
- `tc_summary_10pct_risk.tex` - Transaction cost drag summary
- `appendix_*.tex` - Full metric grids for appendix

### Figures (`Paper/LaTeX/figures/`)
- `motivation_quarterly_outlier_inflation.pdf` - Motivation figure
- `pv_curves_zero_cost.pdf` - Portfolio value time series
- `heatmap_terminal_pv_zero_cost.pdf` - Terminal PV heatmap
- `heatmap_mdd_zero_cost.pdf` - Maximum drawdown heatmap
- `cost_drag_curves.pdf` - Transaction cost sensitivity

## Requirements

The scripts require:
- Python 3.8+
- pandas
- openpyxl
- matplotlib
- numpy

All dependencies are listed in the project's `requirements.txt`.

## Input Data

Scripts read from:
- `Data/combined.csv` - Daily returns for sector ETFs
- `Output/` - Backtest results organized by transaction cost, risk budget, and frequency

## Troubleshooting

### Import Errors
If you get import errors, prefer running via the module entrypoint from the project root:
```bash
python -m Paper.scripts.build_all
```

Legacy script-style entrypoints are still supported:
```bash
python Paper/scripts/build_all.py
```

### Missing Output Files
If scripts fail to find Output files, ensure the backtest code has been run:
```bash
cd ../..  # Back to project root
python main.py  # Or run your backtest notebook
```

### Figure Generation Issues
- Ensure matplotlib backend is properly configured
- Check that `Paper/LaTeX/figures/` directory exists (created automatically)

### Inspecting Output Structure
To debug Output file formats:
```bash
python utils/inspect_output_structure.py
```

## Development

### Adding New Figures
1. Create `figures/generate_<name>.py` with a `main()` function
2. Import and call in `figures/build_all_figures.py`
3. Add placeholder in `Paper/LaTeX/main.tex` with `\includefigure{...}`

### Adding New Tables
1. Add generation logic to `tables/build_paper_tables.py`
2. Use helper functions: `write_table()`, `grid_table()`, `grid_table_reduced()`
3. Add `\input{tables/...}` in appropriate section of `main.tex`

### Shared Utilities
Common functionality lives in `utils/figure_helpers.py`:
- Path management (PROJECT_ROOT, OUTPUT_ROOT, etc.)
- Data loading functions (load_metric, load_weights, etc.)
- Plotting configuration (LaTeX-compatible matplotlib settings)
- Color schemes and formatting helpers
