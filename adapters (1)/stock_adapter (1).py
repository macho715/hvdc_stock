
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from stock (1).py file
import importlib.util
spec = importlib.util.spec_from_file_location("stock", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stock (1).py"))
stock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock)

analyze_hvdc_inventory = stock.analyze_hvdc_inventory
InventoryTracker = stock.InventoryTracker

def build_stock_snapshots(stock_excel_path: str) -> dict:
    # Use the main analysis function
    print(f"📂 Loading stock data from: {stock_excel_path}")
    
    # Run the analysis
    analyze_hvdc_inventory(stock_excel_path, show_details=False)
    
    # Create an InventoryTracker instance to get processed data
    tr = InventoryTracker(stock_excel_path)
    tr.run_analysis()
    summary_df = tr.create_summary()
    
    return {
        "latest_date": None,  # Will be filled by the actual analysis
        "timeline": {},
        "current_stock_skus": set(),
        "summary_df": summary_df
    }
