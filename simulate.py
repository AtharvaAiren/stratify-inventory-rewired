import pandas as pd
from collections import deque
import os
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parent
SALES_FILE = ROOT / 'data' / 'SKU-Store Sales.xlsx'
CONSOLIDATED_FILE = ROOT / 'data' / 'Mid Term Submission.xlsx'
OUTPUT_DIR = ROOT / 'outputs'

SKU_PARAMETERS = {
    'P1001': {'unit_cost': 98.91, 'avg_lead_time': 10, 'shelf_life_days': 51},
    'P1002': {'unit_cost': 140.17, 'avg_lead_time': 8, 'shelf_life_days': 83},
    'P1003': {'unit_cost': 34.39, 'avg_lead_time': 7, 'shelf_life_days': 100},
    'P1004': {'unit_cost': 25.03, 'avg_lead_time': 5, 'shelf_life_days': 88},
    'P1005': {'unit_cost': 100.6, 'avg_lead_time': 9, 'shelf_life_days': 105},
    'P1006': {'unit_cost': 56.71, 'avg_lead_time': 7, 'shelf_life_days': 51},
    'P1007': {'unit_cost': 97.48, 'avg_lead_time': 5, 'shelf_life_days': 118},
    'P1008': {'unit_cost': 131.94, 'avg_lead_time': 5, 'shelf_life_days': 100},
    'P1009': {'unit_cost': 75.58, 'avg_lead_time': 5, 'shelf_life_days': 48},
    'P1010': {'unit_cost': 137.27, 'avg_lead_time': 4, 'shelf_life_days': 109},
}

SEASONAL_TARGETS = {
    ('P1003', 'S003'): ['Monday'],
    ('P1010', 'S003'): ['Saturday'],
    ('P1004', 'S003'): ['Saturday'],
    ('P1007', 'S001'): ['Friday'],
    ('P1010', 'S001'): ['Friday'],
    ('P1005', 'S001'): ['Monday', 'Tuesday', 'Wednesday'],
    ('P1009', 'S003'): ['Friday'],
}

seasonality_table = {
    'S003_P1003': [115/13, 56/13, 63/13, 79/13, 71/14, 79/13, 76/13],
    'S003_P1010': [92/13, 66/13, 61/13, 77/13, 85/14, 112/13, 81/13],
    'S003_P1004': [56/13, 80/13, 80/13, 81/13, 84/14, 100/13, 73/13],
    'S001_P1007': [89/13, 56/13, 62/13, 79/13, 105/14, 89/13, 88/13],
    'S001_P1010': [74/13, 93/13, 83/13, 93/13, 112/14, 68/13, 62/13],
    'S001_P1005': [97/13, 103/13, 97/13, 78/13, 65/14, 90/13, 69/13],
    'S003_P1009': [61/13, 73/13, 66/13, 79/13, 100/14, 82/13, 77/13]
}

def get_user_date():
    while True:
        try:
            date_str = input("Enter simulation start date (YYYY-MM-DD): ")
            return pd.to_datetime(date_str)
        except:
            print("Invalid date format. Please enter YYYY-MM-DD.")

def generate_forecast(store, sku, start_date, length=35):
    key = f"{store}_{sku}"
    if key not in seasonality_table:
        return pd.Series([0] * length)
    weekly = seasonality_table[key]
    dates = pd.date_range(start=start_date, periods=length)
    values = [weekly[d.weekday()] for d in dates]
    return pd.Series(values)

def run_replenishment_model(start_date=None):
    xl = pd.ExcelFile(SALES_FILE)
    consolidated_df = pd.read_excel(CONSOLIDATED_FILE, sheet_name='ROP, EOQ, Safety Stock')
    param_map = {(row['SKU ID'], row['Store ID']): row for _, row in consolidated_df.iterrows()}

    sim_start = pd.to_datetime(start_date) if start_date else get_user_date()
    sim_length = 21
    forecast_length = 35

    kpi_results = []
    simulation_details = []

    for sheet_name in xl.sheet_names:
        if '_' not in sheet_name:
            continue
        store, sku = sheet_name.split('_')

        df = xl.parse(sheet_name)
        df['Date'] = pd.to_datetime(df['Date'])
        sim_data = df[(df['Date'] >= sim_start) & (df['Date'] < sim_start + pd.Timedelta(days=sim_length))].copy()
        if sim_data.empty:
            print(f"No data for {store}_{sku}, skipping.")
            continue

        sku_params = SKU_PARAMETERS.get(sku, {})
        unit_cost = sku_params.get('unit_cost', 1)
        lead_time = sku_params.get('avg_lead_time', 3)
        shelf_life = sku_params.get('shelf_life_days', 30)

        consolidated = param_map.get((sku, store), None)

        if consolidated is not None and not consolidated.empty:
            base_rop = consolidated['Reorder Point']
            base_eoq = consolidated['EOQ']
            base_ss = consolidated['Safety Stock']
        else:
            base_rop = consolidated_df['Reorder Point'].mean()
            base_eoq = consolidated_df['EOQ'].mean()
            base_ss = consolidated_df['Safety Stock'].mean()

        initial_stock = df.loc[df['Date'] == sim_start, 'Opening Stock'].values[0]
        stock = initial_stock

        use_seasonal = (sku, store) in SEASONAL_TARGETS
        eoq_days = 7 if shelf_life < 60 else 14

        if use_seasonal:
            forecast = generate_forecast(store, sku, sim_start, forecast_length)
        else:
            forecast = None

        pending_orders = deque()
        order_outstanding = False
        total_lost_sales_new_units = 0
        lost_sales_old_units = 0

        daily_records = []
        total_possible_sales_units = sim_data['Demand'].sum()

        for offset in range(sim_length):
            current_day = sim_start + pd.Timedelta(days=offset)

            while pending_orders and pending_orders[0][0] <= current_day:
                arr_day, qty = pending_orders.popleft()
                stock += qty
                order_outstanding = False

            demand_row = sim_data[sim_data['Date'] == current_day]
            actual_demand = demand_row['Demand'].values[0] if not demand_row.empty else 0

            opening_stock_row = df[df['Date'] == current_day]
            opening_stock = opening_stock_row['Opening Stock'].values[0] if not opening_stock_row.empty else 0
            lost_sales_old_units += max(0, actual_demand - opening_stock)

            if use_seasonal:
                reorder_point = forecast[offset:offset+lead_time].sum() + base_ss
                order_qty = forecast[offset:offset+eoq_days].sum()
            else:
                reorder_point = base_rop
                order_qty = base_eoq

            order_qty = int(round(max(1, order_qty)))

            order_placed_today = 0
            if stock < reorder_point and not order_outstanding:
                arrival_day = current_day + pd.Timedelta(days=lead_time)
                pending_orders.append((arrival_day, order_qty))
                order_placed_today = order_qty
                order_outstanding = True

            sold_qty = min(stock, actual_demand)
            stock -= sold_qty

            lost_sales_new_units = max(0, actual_demand - sold_qty)
            total_lost_sales_new_units += lost_sales_new_units

            daily_records.append({
                'Date': current_day,
                'Demand': actual_demand,
                'Opening Stock': stock + sold_qty,
                'Closing Stock': stock,
                'Order Placed': order_placed_today,
                'Sales Lost': lost_sales_new_units,
                'Reorder Point': reorder_point,
                'Lead Time': lead_time,
                'EOQ': order_qty,
                'Policy': 'Seasonal' if use_seasonal else 'Averaged',
                'Store': store,
                'SKU': sku
            })

        avg_inventory = pd.DataFrame(daily_records)['Opening Stock'].mean()

        total_units_sold_old = total_possible_sales_units - lost_sales_old_units
        total_units_sold_new = total_possible_sales_units - total_lost_sales_new_units

        fill_rate_old = (total_units_sold_old / total_possible_sales_units) * 100 if total_possible_sales_units > 0 else 0
        fill_rate_new = (total_units_sold_new / total_possible_sales_units) * 100 if total_possible_sales_units > 0 else 0

        inventory_turnover_old = (total_units_sold_old / avg_inventory) if avg_inventory > 0 else 0
        inventory_turnover_new = (total_units_sold_new / avg_inventory) if avg_inventory > 0 else 0

        total_possible_sales_value = unit_cost * total_possible_sales_units
        lost_sales_old_value = unit_cost * lost_sales_old_units
        lost_sales_new_value = unit_cost * total_lost_sales_new_units

        percent_lost_old = (lost_sales_old_value * 100 / total_possible_sales_value) if total_possible_sales_value > 0 else 0
        percent_lost_new = (lost_sales_new_value * 100 / total_possible_sales_value) if total_possible_sales_value > 0 else 0

        kpi_record = {
            'Store': store,
            'SKU': sku,
            'Policy': 'Seasonal' if use_seasonal else 'Averaged',
            'Total Possible Sales Value': total_possible_sales_value,
            'Lost Sales Old': lost_sales_old_value,
            'Percent Sales Lost (Old)': percent_lost_old,
            'Lost Sales New': lost_sales_new_value,
            'Percent Lost New': percent_lost_new,
            'Fill Rate Old (%)': fill_rate_old,
            'Fill Rate New (%)': fill_rate_new,
            'Inventory Turnover Old': inventory_turnover_old,
            'Inventory Turnover New': inventory_turnover_new
        }
        kpi_results.append(kpi_record)

        simulation_details.extend(daily_records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    kpi_output = OUTPUT_DIR / 'Replenishment_Model_Final_KPI.xlsx'
    sim_details_output = OUTPUT_DIR / 'Replenishment_Model_Final_SimDetails.xlsx'

    pd.DataFrame(kpi_results).to_excel(kpi_output, index=False)
    print(f"KPI summary saved to: {os.path.abspath(kpi_output)}")

    sim_details_df = pd.DataFrame(simulation_details)
    with pd.ExcelWriter(sim_details_output) as writer:
        for (store, sku), group_df in sim_details_df.groupby(['Store', 'SKU']):
            group_df = group_df.drop(columns=['Store', 'SKU'])
            sheet_name = f"{store}_{sku}"[:31]
            group_df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"Detailed simulation saved to: {os.path.abspath(sim_details_output)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the original 21-day Stratify replenishment simulation.')
    parser.add_argument('--start-date', default='2024-03-20')
    parser.add_argument('--sales', type=Path, default=SALES_FILE)
    parser.add_argument('--parameters', type=Path, default=CONSOLIDATED_FILE)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    SALES_FILE = args.sales.resolve()
    CONSOLIDATED_FILE = args.parameters.resolve()
    OUTPUT_DIR = args.output_dir.resolve()
    run_replenishment_model(args.start_date)
