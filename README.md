> **Rebuilt version:** The maintained implementation is now [stratify-inventory-optimizer](https://github.com/AtharvaAiren/stratify-inventory-optimizer). This repository retains the original proposal/submission material.

# Inventory Rewired — Stratify

A business-analytics project for **Stratify, Analytics Club, IIT Bombay (2025)**. The project analyses a simulated retail network of **three stores and ten SKUs**, then compares replenishment policies over a **21-day simulation**.

[Portfolio](https://github.com/AtharvaAiren) · [Simulation code](simulate.py) · [Power BI dashboard](dashboard/Dashboard.pbix) · [Competition brief](docs/competition-brief.pdf)

## What the project contains

- Sales and inventory analysis, safety-stock/reorder parameters, Pareto analysis and seasonality workbooks.
- A replenishment simulation with supplier lead times, outstanding orders and lost-sales accounting.
- Fixed reorder policies for stable-demand pairs and weekday demand profiles for seven seasonal pairs.
- Submitted KPI comparisons, daily simulation tables and a Power BI dashboard.

## Run the simulation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python simulate.py --start-date 2024-03-20
```

Results are written to `outputs/`. The `--sales`, `--parameters` and `--output-dir` options support alternate local paths.

The missing `Consolidated Workbook.xlsx` referenced by the original Word-document code is replaced by the supplied **Mid Term Submission.xlsx**, which contains the same required `ROP, EOQ, Safety Stock` sheet. The original replenishment logic is retained; edits recover formatting and replace machine-specific paths and interactive setup.

## Explore the analysis

| Resource | Purpose |
| --- | --- |
| [data/Given Data.xlsx](data/Given%20Data.xlsx) | Competition-supplied simulated sales, inventory, SKU, purchase-order and supplier data |
| [data/SKU-Store Sales.xlsx](data/SKU-Store%20Sales.xlsx) | Prepared daily series for all 30 store–SKU pairs |
| [data/Mid Term Submission.xlsx](data/Mid%20Term%20Submission.xlsx) | Demand analysis, safety stock, reorder points and seasonality |
| [reports/submitted/](reports/submitted/) | Existing submitted KPI and simulation workbooks |
| [dashboard/Dashboard.pbix](dashboard/Dashboard.pbix) | Power BI report; open in Power BI Desktop |
| [docs/submission-clarifications.pdf](docs/submission-clarifications.pdf) | Original assumptions and explanatory notes |

## Scope and interpretation

This is a competition project, not a winning/finalist claim. The data describes a fictional retailer. Submitted workbooks are historical outputs; newly generated outputs are separate.

The recovered Python implementation uses fixed weekday profiles rather than fitting Holt–Winters, despite that method being discussed in the original notes. Shelf life affects order sizing; the simulation does not explicitly age or expire individual inventory batches. Its original turnover comparison uses a shared simulated average-inventory denominator for both policies.
