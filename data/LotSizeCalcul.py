import MetaTrader5 as mt5
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import numpy as np

# Fonction pour se connecter à MT5
def connect_mt5():
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()
    else:
        print("Connected to MetaTrader 5")

# Fonction pour obtenir les spécifications du contrat
def get_contract_specs(currency_pair):
    symbol_info = mt5.symbol_info(currency_pair)
    if symbol_info is None:
        print(f"{currency_pair} not found, cannot get contract specs.")
        return None
    if symbol_info.point == 0:
        print(f"{currency_pair} has point value of 0, cannot get contract specs.")
        return None
    
    contract_size = symbol_info.trade_contract_size
    tick_size = symbol_info.point
    tick_value = tick_size * contract_size
    tick_value_Profit = symbol_info.point
    
    # Print debug information for contract specs
    print(f"Currency pair: {currency_pair}")
    print(f"Symbol info: {symbol_info}")
    print(f"Contract size: {contract_size}")
    print(f"Tick size: {tick_size}")
    print(f"Tick value: {tick_value}")
    
    return contract_size, tick_size, tick_value

# Fonction pour obtenir le taux de change avec l'USD
def get_exchange_rate(base_currency):
    pair = f"USD{base_currency}"
    rates = mt5.symbol_info(pair)
    if rates is None:
        print(f"Could not retrieve exchange rate for {pair}")
        return None
    return (rates.bid + rates.ask) / 2  # Use the average of bid and ask

# Fonction pour se déconnecter de MT5
def disconnect_mt5():
    mt5.shutdown()
    print("Disconnected from MetaTrader 5")

# Fonction pour sélectionner un fichier Excel
def select_file():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel files", "*.xlsx")])
    root.destroy()
    return file_path

# Fonction pour lire les données de l'onglet "Results" du fichier Excel
def read_results_from_excel(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name='Results')
        return df
    except ValueError:
        messagebox.showerror("Error", "The file does not contain a 'Results' sheet")
        return None

# Fonction pour extraire les noms des devises à partir des onglets disponibles
def extract_currency_names(file_path):
    xls = pd.ExcelFile(file_path)
    currency_names = []
    for sheet_name in xls.sheet_names:
        match = re.match(r'trading_data_(\w+)_Strategies_', sheet_name)
        if match:
            currency_names.append(match.group(1))
    return currency_names

# Fonction pour lire les données des onglets de chaque devise et extraire les stop losses
def read_strategy_stop_losses(file_path, currency):
    sheet_name = f'trading_data_{currency}_Strategies_'
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        stop_losses = {}
        for strategy in df['Strategy']:
            match = re.search(r'Size_(\d+)_Ratio', strategy)
            if match:
                stop_loss = int(match.group(1))
                if stop_loss not in stop_losses:
                    stop_losses[stop_loss] = stop_loss
        return stop_losses
    except ValueError:
        messagebox.showerror("Error", f"The file does not contain a '{sheet_name}' sheet")
        return {}

# Fonction pour calculer le risque moyen nécessaire pour atteindre l'objectif
def calculate_required_risk(df, target_percentage, duration_days):
    duration_months = duration_days / 30  # Convert days to months
    whole_months = int(duration_months)   # Number of complete months
    fraction_month = duration_months - whole_months  # Remaining fraction of the month
    results = {}
    
    # Convert all columns to numeric, coercing errors to NaN
    df = df.apply(pd.to_numeric, errors='coerce')
    
    # Filter columns to include only those containing "1%" in their names
    one_percent_columns = [col for col in df.columns if '1%' in col]
    
    # Debugging print to check which columns are selected
    print("One percent columns selected:", one_percent_columns)
    
    for column in one_percent_columns:
        clean_column = df[column].dropna()  # Drop NaN values before calculating mean
        if not clean_column.empty:  # Ensure the column has data
            success_rates = []
            print(f"\nProcessing column: {column}")
            for start in range(len(clean_column) - whole_months):
                # Calculate the weighted average for the period including the fractional month
                period_values = clean_column.iloc[start:start + whole_months + 1]
                if len(period_values) < whole_months + 1:
                    continue
                
                weighted_avg = (period_values[:whole_months].sum() + period_values.iloc[whole_months] * fraction_month) / duration_months
                success_rate = (target_percentage / (weighted_avg * duration_months)) if weighted_avg > 0 else np.inf
                success_rates.append(success_rate)
                
                # Print debug information for each period
                print(f"Period {start + 1}: values = {period_values.values}")
                print(f"Period {start + 1}: whole_months_sum = {period_values[:whole_months].sum()}")
                print(f"Period {start + 1}: fraction_month_value = {period_values.iloc[whole_months]}")
                print(f"Period {start + 1}: weighted_avg = {weighted_avg:.2f}")
                print(f"Period {start + 1}: success_rate = {success_rate:.2f}")
            
            if success_rates:
                required_risk = np.percentile(success_rates, 50)  # Use median to mitigate outliers
                results[column] = required_risk
    
    return results

# Fonction pour calculer la taille du lot en fonction du risque, du montant du portefeuille et du stop loss
def calculate_lot_size(risk_percentage, portfolio_amount, stop_loss_pips, currency):
    contract_size, tick_size, tick_value = get_contract_specs(currency)
    if tick_value is None:
        return None
    
    # Calculate the pip value per lot
    pip_value_USD = (portfolio_amount * (risk_percentage / 100)) / stop_loss_pips
    # 2000 / 40 = 50 USD
    
    Pip_value_Currency = contract_size * tick_size * 10 # 10 for 1 pips
    print(f"contract_size {contract_size} tick_size {tick_size} Pip_value_Currency {Pip_value_Currency}")
    base_currency = currency[3:]
    print(f"base_currency {base_currency}")
    if not base_currency == 'USD':
        exchange_rate = get_exchange_rate(base_currency)
        print(f"exchange_rate {exchange_rate}")
        if exchange_rate is None:
            return None
        Pip_value_Currency = Pip_value_Currency / exchange_rate


    print(f"Pip_value_Currency {Pip_value_Currency}")
        

    # Calculate the lot size
    lot_size = pip_value_USD / Pip_value_Currency
    

    
    # Print debug information for lot size calculation
    print(f"Calculating lot size for {currency}")
    print(f"Risk percentage: {risk_percentage}%")
    print(f"Portfolio amount: {portfolio_amount}")
    print(f"Stop Loss (pips): {stop_loss_pips}")
    print(f"pip_value_USD: {pip_value_USD}")
    print(f"Lot size: {lot_size}")
    
    return lot_size

# Interface utilisateur
class RiskCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Risk Calculator")
        self.root.geometry("400x600")
        
        self.file_path = ""
        
        self.setup_widgets()
        connect_mt5()  # Connect to MT5 on startup

    def setup_widgets(self):
        self.file_button = tk.Button(self.root, text="Select Excel File", command=self.load_file)
        self.file_button.pack(pady=10)
        
        self.file_label = tk.Label(self.root, text="No file selected")
        self.file_label.pack(pady=5)
        
        self.portfolio_label = tk.Label(self.root, text="Portfolio Amount:")
        self.portfolio_label.pack(pady=5)
        
        self.portfolio_entry = tk.Entry(self.root)
        self.portfolio_entry.pack(pady=5)
        
        self.duration_label = tk.Label(self.root, text="Duration to achieve target (days):")
        self.duration_label.pack(pady=5)
        
        self.duration_entry = tk.Entry(self.root)
        self.duration_entry.pack(pady=5)
        
        self.target_label = tk.Label(self.root, text="Target percentage to achieve (%):")
        self.target_label.pack(pady=5)
        
        self.target_entry = tk.Entry(self.root)
        self.target_entry.pack(pady=5)
        
        self.calculate_button = tk.Button(self.root, text="Calculate Risk", command=self.calculate_risk)
        self.calculate_button.pack(pady=10)
        
        self.result_text = tk.Text(self.root, height=15, width=80)
        self.result_text.pack(pady=10)

    def load_file(self):
        self.file_path = select_file()
        self.file_label.config(text=os.path.basename(self.file_path))

    def calculate_risk(self):
        if not self.file_path:
            messagebox.showerror("Error", "No file selected")
            return
        
        try:
            portfolio_amount = float(self.portfolio_entry.get())
            duration_days = int(self.duration_entry.get())
            target_percentage = float(self.target_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid input for portfolio amount, duration, or target percentage")
            return
        
        df = read_results_from_excel(self.file_path)
        if df is None:
            return
        
        results = calculate_required_risk(df, target_percentage, duration_days)
        
        currency_names = extract_currency_names(self.file_path)
        stop_losses = {currency: read_strategy_stop_losses(self.file_path, currency) for currency in currency_names}
        
        self.result_text.delete(1.0, tk.END)
        for section, risk in results.items():
            if 'FiltByPrio' in section or 'FiltFirstOpen' in section:
                # For FiltByPrio and FiltFirstOpen, calculate Lot Size for each currency
                for currency in stop_losses.keys():
                    for stop_loss in stop_losses[currency]:
                        lot_size = calculate_lot_size(risk, portfolio_amount, stop_loss, currency)
                        if lot_size is not None:
                            self.result_text.insert(tk.END, f"{section} ({currency}, Stop Loss = {stop_loss}): Risk = {risk:.2f}%, Lot Size = {lot_size:.2f}\n")
            else:
                # Extract the currency name from the section name
                currency = section.split(' ')[0]
                for stop_loss in stop_losses[currency]:
                    lot_size = calculate_lot_size(risk, portfolio_amount, stop_loss, currency)
                    if lot_size is not None:
                        self.result_text.insert(tk.END, f"{section} (Stop Loss = {stop_loss}): Risk = {risk:.2f}%, Lot Size = {lot_size:.2f}\n")

    def __del__(self):
        disconnect_mt5()  # Disconnect from MT5 on exit

if __name__ == "__main__":
    root = tk.Tk()
    app = RiskCalculatorApp(root)
    root.mainloop()
