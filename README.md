# MAD Portfolio Construction Project

This project implements and compares different portfolio optimization strategies, with a focus on Mean-Absolute Deviation (MAD) optimization versus traditional Markowitz mean-variance optimization.

## Project Overview

The project implements several portfolio optimization strategies:
- **Buy and Hold (S&P)**: A simple strategy that invests in the S&P 500 index ETF
- **Equal Weight**: Equal allocation across all sector ETFs
- **Markowitz Portfolio**: Traditional mean-variance optimization
- **MAD Portfolio**: Mean Absolute Deviation optimization

The code allows for back-testing these strategies over different time periods with various rebalancing frequencies and risk constraints.

## Prerequisites

- Python 3.8 or higher
- Required packages (see `requirements.txt`)

## Installation

1. Clone the repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following variables:

```
# Data directories
RAW_DATA_DIRECTORY=Data/Raw/
COMBINED_DATA_FILE=Data/combined.csv

# Portfolio parameters
ETF_LIST=XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY
INDEX_ETF=^GSPC
USE_CASH=True
MAX_ALLOC=0.4

# Date range
START_YEAR=2010
END_YEAR=2023
```

## Project Structure

```
├── Data/
│   ├── Raw/                 # Raw data files downloaded from Yahoo Finance
│   └── combined.csv         # Processed and combined return data
├── Output/                  # Results and visualizations
├── Paper/                   # Paper (LaTeX) and supporting assets
│   ├── LaTeX/               # Manuscript + generated tables + figures
│   │   ├── main.tex         # Main LaTeX document
│   │   ├── compile.sh       # Compile script (use --rebuild for full build)
│   │   ├── tables/          # Auto-generated LaTeX tables
│   │   └── figures/         # Auto-generated figure PDFs
│   └── scripts/             # Paper automation (table/figure generation)
│       ├── build_all.py     # Main build script
│       ├── tables/          # Table generation scripts
│       ├── figures/         # Figure generation scripts
│       └── utils/           # Shared utilities
├── scripts/
│   ├── analysis/            # Analysis and reporting utilities
│   ├── data/                # Data collection and processing scripts
│   └── finance/             # Portfolio optimization implementations
├── data.py                  # Main data collection script
├── Change in Max Risk.ipynb # Analysis of risk parameter impact
└── requirements.txt         # Required Python packages
```

## Running the Code

### Step 1: Data Collection and Processing

To download and process the data:

```bash
python data.py
```

This script will:
1. Download historical price data for the specified ETFs from Yahoo Finance
2. Process the data to calculate returns
3. Create a combined dataset for portfolio optimization

### Step 2: Running Portfolio Optimization

The main analysis can be run using the Jupyter Notebook:

```bash
jupyter notebook "Change in Max Risk.ipynb"
```

This notebook:
1. Defines the maximum risk constraint
2. Sets up the portfolio optimization parameters
3. Runs back-tests for different portfolio strategies
4. Generates performance metrics and visualizations
5. Saves results to the Output directory

### Step 3: Analyzing Results

After running the notebook, results will be available in the `Output` directory, organized by:
- Maximum risk level
- Rebalancing frequency
- Performance metrics (Returns, Volatility, Sharpe Ratio, Maximum Drawdown)
- Portfolio weights

## Custom Portfolio Optimization

To create a custom portfolio optimization:

1. Import the necessary portfolio classes:
```python
from scripts.finance.Portfolios import StdDevPortfolio, MADPortfolio
```

2. Initialize the portfolio with a rebalancing frequency:
```python
portfolio = MADPortfolio(freq='6mo')  # '1d', '1wk', '1mo', '3mo', '6mo', '1y'
```

3. Calculate performance with a risk constraint:
```python
performance = portfolio.calculate_performance(max_risk=0.15)  # 15% maximum risk
```

## Example Code

The `Paper/Dummy Example/Code.ipynb` notebook contains a simplified example of the portfolio optimization process using sample data.

## Building the Research Paper

After running the backtest and generating Output files, you can build the complete research paper:

### Quick Build (One Command)
```bash
cd Paper/LaTeX
./compile.sh --rebuild
```

This will:
1. Generate all tables from Output data
2. Generate all figures (motivation plots, PV curves, heatmaps, etc.)
3. Compile the LaTeX document to PDF

### LaTeX-Only Compilation

If tables and figures are already up to date:
```bash
cd Paper/LaTeX
./compile.sh
```

### Step-by-Step Build

If you prefer more control:

```bash
# Generate tables and figures
cd Paper/scripts
python build_all.py

# Or generate only tables or figures
python build_all.py --tables-only
python build_all.py --figures-only

# Then compile the PDF
cd ../LaTeX
./compile.sh
```

The compiled paper will be at `Paper/LaTeX/main.pdf`.

For more details on the paper build system, see `Paper/scripts/README.md`.
