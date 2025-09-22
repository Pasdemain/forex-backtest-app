import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import os

# Fonction pour sélectionner plusieurs fichiers Excel
def select_files():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_paths = filedialog.askopenfilenames(title="Select Excel Files", filetypes=[("Excel files", "*.xlsx")])
    root.destroy()
    return file_paths

# Fonction pour lire les stratégies disponibles dans un fichier Excel
def read_strategies_from_excel(file_path):
    xl = pd.ExcelFile(file_path)
    strategies = [sheet for sheet in xl.sheet_names if sheet not in ['Results']]
    return strategies

# Fonction pour extraire les données d'une stratégie spécifique
def extract_strategy_data(file_path, strategy):
    df = pd.read_excel(file_path, sheet_name=strategy)
    return df

def write_strategy_data_to_sheets(selected_strategies, writer):
    all_data = []
    for file_path, strategy in selected_strategies:
        data = extract_strategy_data(file_path, strategy)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        currency = file_name.split('_')[2]  # Extract currency from file name
        sheet_name = f'{file_name}_{strategy}'[:31]
        data['Currency'] = currency
        data['Strategy'] = strategy
        all_data.append(data)
        data.to_excel(writer, sheet_name=sheet_name, index=False)
    return all_data

def generate_results_tab(all_data, writer, priority):
    combined_data = pd.concat(all_data)
    filtered_data_priority = filter_positions_priority(combined_data, priority)
    filtered_data_first_open = filter_positions_first_open(combined_data)
    filtered_data_priority.to_excel(writer, sheet_name='FilteredByPriority', index=False)
    filtered_data_first_open.to_excel(writer, sheet_name='FilteredFirstOpen', index=False)



def calculate_totals_from_sheets(file_path, risk_columns):
    results_df = pd.DataFrame()
    xls = pd.ExcelFile(file_path)
    print(f"Sheets found: {xls.sheet_names}")  # Debugging print
    for sheet_name in xls.sheet_names:
        if sheet_name in ['Results']:
            continue
        print(f"Processing sheet: {sheet_name}")  # Debugging print
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        for risk_col in risk_columns:
            if risk_col in df.columns:
                if "FilteredByPriority" in sheet_name:
                    short_sheet_name = "FiltByPrio"
                elif "FilteredFirstOpen" in sheet_name:
                    short_sheet_name = "FiltFirstOpen"
                else:
                    short_sheet_name = sheet_name.split('_')[2]  # Use the currency part of the sheet name
                monthly_totals = df.groupby('YearMonth')[risk_col].sum().rename(f'{short_sheet_name} {risk_col.split("_")[1]}')
                results_df = pd.concat([results_df, monthly_totals], axis=1, sort=False)
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a') as writer:
        results_df.to_excel(writer, sheet_name='Results', index=True)
    print("Results compiled and written to 'Results' sheet.")

def consolidate_data(selected_strategies, priority):
    output_file_path = 'Global_Strategies_Comparison.xlsx'
    with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
        all_data = write_strategy_data_to_sheets(selected_strategies, writer)
        generate_results_tab(all_data, writer, priority)
    risk_columns = ['Percentage_1%', 'Percentage_2%', 'Percentage_3%', 'Percentage_4%', 'Percentage_5%']
    calculate_totals_from_sheets(output_file_path, risk_columns)
    print(f"File saved to: {os.path.abspath(output_file_path)}")
    return os.path.abspath(output_file_path)

class StrategySelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Strategy Selector")
        self.root.geometry("800x600")
        self.files = []
        self.selected_strategies = []
        self.priority = []
        self.setup_widgets()

    def setup_widgets(self):
        self.label = tk.Label(self.root, text="Selected Excel Files:")
        self.label.pack()
        self.file_listbox = tk.Listbox(self.root, height=1, width=100)
        self.file_listbox.pack()
        self.file_button = tk.Button(self.root, text="Select Files", command=self.load_files)
        self.file_button.pack()
        self.strategy_label = tk.Label(self.root, text="Select Strategies:")
        self.strategy_label.pack()
        self.strategy_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, height=10, width=100)
        self.strategy_listbox.pack()
        self.add_button = tk.Button(self.root, text="Add Strategies", command=self.add_strategies)
        self.add_button.pack()
        self.selected_label = tk.Label(self.root, text="Selected Strategies:")
        self.selected_label.pack()
        self.selected_listbox = tk.Listbox(self.root, height=5, width=100)
        self.selected_listbox.pack()
        self.priority_label = tk.Label(self.root, text="Select Priority:")
        self.priority_label.pack()
        self.priority_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE, height=5, width=100)
        self.priority_listbox.pack()
        self.priority_button_up = tk.Button(self.root, text="Move Up", command=self.move_up)
        self.priority_button_up.pack()
        self.priority_button_down = tk.Button(self.root, text="Move Down", command=self.move_down)
        self.priority_button_down.pack()
        self.calculate_button = tk.Button(self.root, text="Calculate", command=self.calculate)
        self.calculate_button.pack()

    def load_files(self):
        self.files = select_files()
        if self.files:
            self.file_listbox.delete(0, tk.END)
            self.strategy_listbox.delete(0, tk.END)
            existing_currencies = self.priority_listbox.get(0, tk.END)
            for file_path in self.files:
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
                strategies = read_strategies_from_excel(file_path)
                for strategy in strategies:
                    self.strategy_listbox.insert(tk.END, f"{strategy} ({os.path.basename(file_path)})")
                currency = os.path.basename(file_path).split('_')[2]
                if currency not in existing_currencies and currency not in self.priority:
                    self.priority.append(currency)
                    self.priority_listbox.insert(tk.END, currency)

    def add_strategies(self):
        selected_indices = self.strategy_listbox.curselection()
        for i in selected_indices:
            file_strategy = self.strategy_listbox.get(i)
            strategy, file_name = file_strategy.split(" (")
            file_name = file_name.rstrip(")")
            for file in self.files:
                if os.path.basename(file) == file_name:
                    self.selected_strategies.append((file, strategy))
                    self.selected_listbox.insert(tk.END, f"{strategy} ({file_name})")

    def move_up(self):
        selected_indices = self.priority_listbox.curselection()
        for i in selected_indices:
            if i > 0:
                self.priority[i], self.priority[i - 1] = self.priority[i - 1], self.priority[i]
                self.priority_listbox.delete(0, tk.END)
                for currency in self.priority:
                    self.priority_listbox.insert(tk.END, currency)
                self.priority_listbox.selection_set(i - 1)

    def move_down(self):
        selected_indices = self.priority_listbox.curselection()
        for i in selected_indices:
            if i < (len(self.priority) - 1):
                self.priority[i], self.priority[i + 1] = self.priority[i + 1], self.priority[i]
                self.priority_listbox.delete(0, tk.END)
                for currency in self.priority:
                    self.priority_listbox.insert(tk.END, currency)
                self.priority_listbox.selection_set(i + 1)

    def calculate(self):
        if not self.selected_strategies:
            messagebox.showerror("Error", "No strategies selected")
            return
        file_path = consolidate_data(self.selected_strategies, self.priority)
        messagebox.showinfo("Success", f"Data consolidated into {file_path}")

def find_overlaps(data):
    data['EndDatetime'] = pd.to_datetime(data['EndDatetime'])
    data['StartDatetime'] = pd.to_datetime(data['StartDatetime'])
    data.sort_values(by=['StartDatetime', 'EndDatetime'], inplace=True)
    overlaps = []
    for i in range(len(data) - 1):
        for j in range(i + 1, len(data)):
            if data.iloc[j]['StartDatetime'] < data.iloc[i]['EndDatetime']:
                overlaps.append((i, j))
            else:
                break
    return overlaps

def filter_positions_priority(data, priority):
    overlaps = find_overlaps(data)
    to_remove = set()
    for i, j in overlaps:
        if data.iloc[i]['Currency'] in priority and data.iloc[j]['Currency'] in priority:
            if priority.index(data.iloc[i]['Currency']) > priority.index(data.iloc[j]['Currency']):
                to_remove.add(i)
            else:
                to_remove.add(j)
    filtered_data = data.drop(data.index[list(to_remove)])
    return filtered_data

def filter_positions_first_open(data):
    data['EndDatetime'] = pd.to_datetime(data['EndDatetime'])
    data['StartDatetime'] = pd.to_datetime(data['StartDatetime'])
    data.sort_values(by=['StartDatetime', 'EndDatetime'], inplace=True)
    filtered_positions = []
    end_time = pd.Timestamp.min
    for i in range(len(data)):
        if data.iloc[i]['StartDatetime'] >= end_time:
            filtered_positions.append(i)
            end_time = data.iloc[i]['EndDatetime']
    filtered_data = data.iloc[filtered_positions]
    return filtered_data

root = tk.Tk()
app = StrategySelectorApp(root)
root.mainloop()
