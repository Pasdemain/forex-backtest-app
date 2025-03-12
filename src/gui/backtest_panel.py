"""
Backtest Panel Module

This module provides the UI for backtesting trading strategies.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.filedialog import asksaveasfilename
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
from tkcalendar import DateEntry
import threading
import os

from src.utils.config import get_config
from src.utils.time_utils import (
    format_datetime_for_db,
    combine_date_and_time,
    get_session_for_time
)
from src.data.database import (
    get_news_around_time,
    get_trading_statistics
)
from src.analysis.backtest import (
    backtest_trade,
    batch_backtest,
    summarize_backtest_results,
    calculate_drawdown,
    generate_equity_curve,
    check_news_for_entry
)

logger = logging.getLogger(__name__)

class NewsDisplayDialog(tk.Toplevel):
    """Dialog for displaying news events."""
    
    def __init__(self, parent, news_data, date_limit, db_path):
        """Initialize the news display dialog."""
        super().__init__(parent)
        self.title("News Details")
        self.geometry("600x400")
        self.transient(parent)
        self.db_path = db_path
        
        # Center on parent
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        self.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        
        # Create treeview
        self.tree = ttk.Treeview(self, columns=("Time", "Impact", "Currency", "News"), show="headings")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Impact", text="Impact")
        self.tree.heading("Currency", text="Currency")
        self.tree.heading("News", text="News")
        
        # Set column widths
        self.tree.column("Time", width=150)
        self.tree.column("Impact", width=100)
        self.tree.column("Currency", width=100)
        self.tree.column("News", width=250)
        
        # Insert data
        for news in news_data:
            self.tree.insert('', tk.END, values=(news['time'], news['impact'], news['currency'], news['news']))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind double-click event
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        # Add close button
        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(side=tk.BOTTOM, pady=10)
    
    def on_item_double_click(self, event):
        """Handle double-click on a news item."""
        # Get the selected item
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        # Extract news name and time
        news_name = values[3]
        time_str = values[0]
        
        # Convert time to datetime
        news_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        
        # Open similar news dialog
        from src.data.database import get_similar_news
        similar_news = get_similar_news(self.db_path, news_name, news_time)
        
        if similar_news:
            SimilarNewsDialog(self, similar_news, news_name)
        else:
            messagebox.showinfo("Similar News", "No similar news events found")

class SimilarNewsDialog(tk.Toplevel):
    """Dialog for displaying similar news events."""
    
    def __init__(self, parent, news_data, news_name):
        """Initialize the similar news dialog."""
        super().__init__(parent)
        self.title(f"Similar News: {news_name}")
        self.geometry("800x500")
        self.transient(parent)
        
        # Center on parent
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        self.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        
        # Create treeview
        columns = ("Time", "Impact", "Currency", "News", "Pips_Highest_Shadow", "Pips_Lowest_Shadow", "actual", "forecast", "previous")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        
        # Set headings
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        # Adjust column widths
        self.tree.column("News", width=200)
        self.tree.column("Time", width=150)
        
        # Insert data
        for news in news_data:
            values = []
            for col in columns:
                values.append(news.get(col, ""))
            self.tree.insert('', tk.END, values=values)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add close button
        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(side=tk.BOTTOM, pady=10)

class BacktestEntryDialog(tk.Toplevel):
    """Dialog for entering backtest parameters."""
    
    def __init__(self, parent, year, month, symbol, db_path):
        """Initialize the backtest entry dialog."""
        super().__init__(parent)
        self.title("Backtest Entry")
        self.geometry("500x600")
        self.transient(parent)
        
        # Store parameters
        self.parent = parent
        self.year = year
        self.month = month
        self.symbol = symbol
        self.db_path = db_path
        self.config = get_config()
        
        # Set accent color
        self.configure(bg=self.config['gui']['accent_color'])
        
        # Center on parent
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        self.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        
        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create form
        self.create_form()
        
        # Add buttons
        self.create_buttons()
        
    def create_form(self):
        """Create the form for backtest entry."""
        current_row = 0
        
        # Day selection
        ttk.Label(self.main_frame, text="Day:").grid(column=0, row=current_row, sticky='w')
        self.day_var = tk.StringVar()
        
        # Calendar button for day selection
        self.select_day_btn = ttk.Button(self.main_frame, text="Select Day", command=self._open_calendar)
        self.select_day_btn.grid(column=1, row=current_row, sticky='ew')
        
        # Label to show selected day
        self.selected_day_label = ttk.Label(self.main_frame, text="")
        self.selected_day_label.grid(column=2, row=current_row, sticky='w')
        current_row += 1
        
        # Open time
        ttk.Label(self.main_frame, text="Open Time:").grid(column=0, row=current_row, sticky='w')
        self.hour_var = tk.StringVar()
        
        # Generate hours from 00:00 to 23:45 in 15-minute intervals
        hours = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 15, 30, 45]]
        
        self.hour_entry = ttk.Combobox(self.main_frame, textvariable=self.hour_var, values=hours, width=5)
        self.hour_entry.grid(column=1, row=current_row, sticky='ew')
        
        # Check news button
        self.check_news_btn = ttk.Button(self.main_frame, text="Check News", command=self._check_news)
        self.check_news_btn.grid(column=2, row=current_row, sticky='w')
        current_row += 1
        
        # Position
        ttk.Label(self.main_frame, text="Position:").grid(column=0, row=current_row, sticky='w')
        self.position_var = tk.StringVar()
        
        # Radio buttons for position
        position_frame = ttk.Frame(self.main_frame)
        position_frame.grid(column=1, row=current_row, columnspan=2, sticky='w')
        
        ttk.Radiobutton(position_frame, text="Buy", variable=self.position_var, value="Buy").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(position_frame, text="Sell", variable=self.position_var, value="Sell").pack(side=tk.LEFT, padx=5)
        current_row += 1
        
        # H4 Category
        ttk.Label(self.main_frame, text="H4:").grid(column=0, row=current_row, sticky='w')
        self.h4_var = tk.StringVar()
        
        h4_options = [
            "Downtrend overall trend", 
            "Downtrend because of break of structure", 
            "Uptrend overall trend", 
            "Uptrend because of break of structure"
        ]
        
        self.h4_dropdown = ttk.Combobox(self.main_frame, textvariable=self.h4_var, values=h4_options, width=40)
        self.h4_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        current_row += 1
        
        # H1 Category
        ttk.Label(self.main_frame, text="H1:").grid(column=0, row=current_row, sticky='w')
        self.h1_var = tk.StringVar()
        
        h1_options = ["Downtrend", "Uptrend", "Consolidate"]
        
        self.h1_dropdown = ttk.Combobox(self.main_frame, textvariable=self.h1_var, values=h1_options, width=20)
        self.h1_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        current_row += 1
        
        # Entry Point
        ttk.Label(self.main_frame, text="Confluence:").grid(column=0, row=current_row, sticky='w')
        self.entry_point_var = tk.StringVar()
        
        entry_point_options = ["Liquidity sweep", "Equilibrum", "FVG", "Order Block", "Breaker Block"]
        
        self.entry_point_dropdown = ttk.Combobox(self.main_frame, textvariable=self.entry_point_var, values=entry_point_options, width=20)
        self.entry_point_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        current_row += 1
        
        # M15 Category
        ttk.Label(self.main_frame, text="M15:").grid(column=0, row=current_row, sticky='w')
        self.m15_var = tk.StringVar()
        
        m15_options = ["Break structure to downtrend", "Break structure to Uptrend"]
        
        self.m15_dropdown = ttk.Combobox(self.main_frame, textvariable=self.m15_var, values=m15_options, width=30)
        self.m15_dropdown.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        current_row += 1
        
        # News impact
        ttk.Label(self.main_frame, text="News Impact:").grid(column=0, row=current_row, sticky='w')
        self.news_impact_var = tk.StringVar()
        self.news_impact_entry = ttk.Entry(self.main_frame, textvariable=self.news_impact_var, width=40)
        self.news_impact_entry.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        current_row += 1
        
        # News types
        ttk.Label(self.main_frame, text="News Types:").grid(column=0, row=current_row, sticky='w')
        self.news_types_var = tk.StringVar()
        self.news_types_entry = ttk.Entry(self.main_frame, textvariable=self.news_types_var, width=40)
        self.news_types_entry.grid(column=1, row=current_row, columnspan=2, sticky='ew')
        current_row += 1
        
        # Results frame
        results_frame = ttk.LabelFrame(self.main_frame, text="Backtest Results")
        results_frame.grid(column=0, row=current_row, columnspan=3, sticky='ew', padx=5, pady=10)
        
        # Create a treeview for backtest results
        self.results_tree = ttk.Treeview(results_frame, columns=("SL", "Ratio", "Result", "Duration"), show="headings", height=5)
        self.results_tree.heading("SL", text="Stop Loss")
        self.results_tree.heading("Ratio", text="Ratio")
        self.results_tree.heading("Result", text="Result")
        self.results_tree.heading("Duration", text="Duration (h)")
        
        # Column widths
        self.results_tree.column("SL", width=70)
        self.results_tree.column("Ratio", width=70)
        self.results_tree.column("Result", width=70)
        self.results_tree.column("Duration", width=70)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        current_row += 1
    
    def create_buttons(self):
        """Create buttons for the dialog."""
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Backtest button
        backtest_button = ttk.Button(button_frame, text="Run Backtest", command=self.run_backtest)
        backtest_button.pack(side=tk.LEFT, padx=5)
        
        # Add Entry button
        add_entry_button = ttk.Button(button_frame, text="Add to Database", command=self.add_entry)
        add_entry_button.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def _open_calendar(self):
        """Open calendar for day selection."""
        cal_win = tk.Toplevel(self)
        cal_win.title("Select Day")
        cal_win.transient(self)
        cal_win.grab_set()
        
        cal_year = int(self.year)
        cal_month = int(self.month)
        
        cal = DateEntry(cal_win, selectmode='day', year=cal_year, month=cal_month, day=1)
        cal.pack(padx=10, pady=10)
        
        def _confirm_date():
            selected_date = cal.get_date()
            
            # Format as day/month/year
            formatted_date = selected_date.strftime('%d/%m/%y')
            
            # Update variables
            self.day_var.set(formatted_date)
            self.selected_day_label.config(text=formatted_date)
            
            # Close calendar window
            cal_win.destroy()
        
        ttk.Button(cal_win, text="Ok", command=_confirm_date).pack()
        
        # Center on parent
        self.update_idletasks()
        dialog_x = self.winfo_x()
        dialog_y = self.winfo_y()
        
        cal_win.update_idletasks()
        cal_win.geometry(f"+{dialog_x + 50}+{dialog_y + 50}")
        
        cal_win.wait_window()
    
    def _check_news(self):
        """Check for news events around the selected time."""
        day = self.day_var.get()
        hour = self.hour_var.get()
        
        if not day or not hour:
            messagebox.showerror("Error", "Please select day and time")
            return
        
        # Combine date and time
        start_datetime = combine_date_and_time(day, hour)
        if not start_datetime:
            messagebox.showerror("Error", "Invalid date or time format")
            return
        
        # Get news events
        hours_before = self.config['news']['hours_before']
        hours_after = self.config['news']['hours_after']
        
        news_events = check_news_for_entry(self.db_path, start_datetime, hours_before, hours_after)
        
        if news_events:
            # Open news display dialog
            NewsDisplayDialog(self, news_events, start_datetime, self.db_path)
        else:
            messagebox.showinfo("News Check", "No news found in the specified interval.")
    
    def run_backtest(self):
        """Run the backtest."""
        # Validate inputs
        if not self._validate_inputs():
            return
        
        # Prepare entry data
        entry_data = self._prepare_entry_data()
        
        # Start backtest
        self.backtest_results = []
        
        # Run backtest in a separate thread
        threading.Thread(target=self._run_backtest_thread, args=(entry_data,)).start()
    
    def _run_backtest_thread(self, entry_data):
        """Run backtest in a separate thread."""
        try:
            # Run backtest
            results = backtest_trade(self.db_path, self.symbol, entry_data)
            
            # Save results
            self.backtest_results = results
            
            # Update UI on main thread
            self.after(0, self._update_results_display)
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Backtest failed: {e}"))
    
    def _update_results_display(self):
        """Update the results display."""
        # Clear existing results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Add new results
        if self.backtest_results:
            for result in self.backtest_results:
                self.results_tree.insert('', tk.END, values=(
                    result.get('StoplossSize'),
                    result.get('TradeRatio'),
                    result.get('Result'),
                    result.get('duration_hours')
                ))
            
            # Show summary
            summary = summarize_backtest_results(self.backtest_results)
            win_rate = summary['win_rate']
            messagebox.showinfo("Backtest Complete", f"Backtest completed with {len(self.backtest_results)} scenarios.\n"
                                f"Win rate: {win_rate:.1f}%")
        else:
            messagebox.showinfo("Backtest Complete", "No results found.")
    
    def add_entry(self):
        """Add the backtest entry to the database."""
        if not self.backtest_results:
            messagebox.showerror("Error", "Please run a backtest first")
            return
        
        # Confirm with user
        if not messagebox.askyesno("Confirm", "Add these backtest results to the database?"):
            return
        
        # All backtest results are already in the database (saved during backtest)
        messagebox.showinfo("Success", "Backtest results added to database")
        
        # Close dialog
        self.destroy()
    
    def _validate_inputs(self):
        """Validate user inputs."""
        # Check required fields
        required_fields = {
            "Day": self.day_var.get(),
            "Open Time": self.hour_var.get(),
            "Position": self.position_var.get(),
            "H4": self.h4_var.get(),
            "H1": self.h1_var.get(),
            "M15": self.m15_var.get(),
            "Entry Point": self.entry_point_var.get()
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            messagebox.showerror("Error", f"Missing required fields: {', '.join(missing_fields)}")
            return False
        
        return True
    
    def _prepare_entry_data(self):
        """Prepare entry data for backtest."""
        return {
            "day": self.day_var.get(),
            "OpenTime": self.hour_var.get(),
            "position": self.position_var.get(),
            "H4": self.h4_var.get(),
            "H1": self.h1_var.get(),
            "M15": self.m15_var.get(),
            "EntryPoint": self.entry_point_var.get(),
            "ImpactPosition": self.news_impact_var.get(),
            "NewsTypes": self.news_types_var.get(),
            "save_to_db": False  # Don't save to DB during initial backtest
        }

class BacktestPanel(ttk.Frame):
    """Panel for backtesting."""
    
    def __init__(self, parent, main_app):
        """Initialize the backtest panel."""
        super().__init__(parent)
        self.parent = parent
        self.main_app = main_app
        self.config = get_config()
        
        # Initialize state variables
        self.current_db_path = None
        self.current_symbol = None
        self.backtest_results = []
        
        # Create UI
        self.create_ui()
    
    def create_ui(self):
        """Create the user interface."""
        # Create a frame with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.new_backtest_tab = ttk.Frame(self.notebook)
        self.analysis_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.new_backtest_tab, text="New Backtest")
        self.notebook.add(self.analysis_tab, text="Analysis")
        
        # Set up each tab
        self._setup_new_backtest_tab()
        self._setup_analysis_tab()
    
    def _setup_new_backtest_tab(self):
        """Set up the new backtest tab."""
        # Create main frame with padding
        main_frame = ttk.Frame(self.new_backtest_tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_label = ttk.Label(main_frame, text="Create New Backtest", font=("Helvetica", 14, "bold"))
        header_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 20))
        
        # Period selection
        ttk.Label(main_frame, text="Year:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.year_var = tk.StringVar()
        years = [str(year) for year in range(2020, 2026)]
        year_combo = ttk.Combobox(main_frame, textvariable=self.year_var, values=years, width=6)
        year_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        year_combo.set(str(datetime.now().year))
        
        ttk.Label(main_frame, text="Month:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.month_var = tk.StringVar()
        months = [str(month) for month in range(1, 13)]
        month_combo = ttk.Combobox(main_frame, textvariable=self.month_var, values=months, width=6)
        month_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        month_combo.set(str(datetime.now().month))
        
        # Symbol label
        ttk.Label(main_frame, text="Symbol:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.symbol_label = ttk.Label(main_frame, text="Not selected")
        self.symbol_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Database label
        ttk.Label(main_frame, text="Database:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.db_label = ttk.Label(main_frame, text="Not selected")
        self.db_label.grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Create buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        new_entry_button = ttk.Button(button_frame, text="New Entry", command=self.open_new_entry, width=15)
        new_entry_button.pack(side=tk.LEFT, padx=5)
        
        batch_backtest_button = ttk.Button(button_frame, text="Batch Backtest", command=self.open_batch_backtest, width=15)
        batch_backtest_button.pack(side=tk.LEFT, padx=5)
        
        # Recent entries section
        entries_frame = ttk.LabelFrame(main_frame, text="Recent Entries")
        entries_frame.grid(row=6, column=0, columnspan=3, sticky=tk.NSEW, pady=10)
        
        # Make the entries frame expandable
        main_frame.grid_rowconfigure(6, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)
        
        # Create a treeview for recent entries
        columns = ("Date", "Time", "Position", "Result", "Ratio", "SL")
        self.entries_tree = ttk.Treeview(entries_frame, columns=columns, show="headings", height=10)
        
        # Set headings
        for col in columns:
            self.entries_tree.heading(col, text=col)
            self.entries_tree.column(col, width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(entries_frame, orient=tk.VERTICAL, command=self.entries_tree.yview)
        self.entries_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.entries_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind double-click event
        self.entries_tree.bind("<Double-1>", self.on_entry_double_click)
    
    def _setup_analysis_tab(self):
        """Set up the analysis tab."""
        # Create main frame with padding
        main_frame = ttk.Frame(self.analysis_tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_label = ttk.Label(main_frame, text="Backtest Analysis", font=("Helvetica", 14, "bold"))
        header_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 20))
        
        # Filter section
        filter_frame = ttk.LabelFrame(main_frame, text="Filters")
        filter_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Create filter controls
        ttk.Label(filter_frame, text="Position:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.filter_position_var = tk.StringVar(value="All")
        position_combo = ttk.Combobox(filter_frame, textvariable=self.filter_position_var, values=["All", "Buy", "Sell"], width=10)
        position_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="H4:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.filter_h4_var = tk.StringVar(value="All")
        h4_combo = ttk.Combobox(filter_frame, textvariable=self.filter_h4_var, values=["All", "Uptrend", "Downtrend"], width=10)
        h4_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(filter_frame, text="Result:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.filter_result_var = tk.StringVar(value="All")
        result_combo = ttk.Combobox(filter_frame, textvariable=self.filter_result_var, values=["All", "Winning", "Losing"], width=10)
        result_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        apply_button = ttk.Button(filter_frame, text="Apply Filters", command=self.apply_filters)
        apply_button.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics")
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Create labels for statistics
        ttk.Label(stats_frame, text="Total Trades:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.total_trades_label = ttk.Label(stats_frame, text="0")
        self.total_trades_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Win Rate:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.win_rate_label = ttk.Label(stats_frame, text="0%")
        self.win_rate_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Avg Duration:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.avg_duration_label = ttk.Label(stats_frame, text="0 hours")
        self.avg_duration_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Graphs section
        graphs_frame = ttk.LabelFrame(main_frame, text="Performance Graphs")
        graphs_frame.grid(row=3, column=0, columnspan=3, sticky=tk.NSEW, pady=10)
        
        # Make the graphs frame expandable
        main_frame.grid_rowconfigure(3, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)
        
        # Create tabs for different graphs
        graphs_notebook = ttk.Notebook(graphs_frame)
        graphs_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tab frames
        equity_tab = ttk.Frame(graphs_notebook)
        win_rate_tab = ttk.Frame(graphs_notebook)
        drawdown_tab = ttk.Frame(graphs_notebook)
        
        graphs_notebook.add(equity_tab, text="Equity Curve")
        graphs_notebook.add(win_rate_tab, text="Win Rate Analysis")
        graphs_notebook.add(drawdown_tab, text="Drawdown Analysis")
        
        # Create figures for each tab
        self.equity_fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.equity_canvas = FigureCanvasTkAgg(self.equity_fig, equity_tab)
        self.equity_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.win_rate_fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.win_rate_canvas = FigureCanvasTkAgg(self.win_rate_fig, win_rate_tab)
        self.win_rate_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.drawdown_fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.drawdown_canvas = FigureCanvasTkAgg(self.drawdown_fig, drawdown_tab)
        self.drawdown_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Export buttons
        export_frame = ttk.Frame(main_frame)
        export_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        export_csv_button = ttk.Button(export_frame, text="Export to CSV", command=self.export_to_csv)
        export_csv_button.pack(side=tk.LEFT, padx=5)
        
        export_graph_button = ttk.Button(export_frame, text="Export Graphs", command=self.export_graphs)
        export_graph_button.pack(side=tk.LEFT, padx=5)
    
    def on_database_opened(self, db_path, symbol):
        """Handle when a database is opened."""
        self.current_db_path = db_path
        self.current_symbol = symbol
        
        # Update labels
        self.symbol_label.config(text=symbol)
        self.db_label.config(text=db_path)
        
        # Load recent entries
        self.load_recent_entries()
        
        # Update analysis
        self.update_analysis()
    
    def load_recent_entries(self):
        """Load recent entries from the database."""
        if not self.current_db_path:
            return
        
        # Clear existing entries
        for item in self.entries_tree.get_children():
            self.entries_tree.delete(item)
        
        try:
            # Connect to the database
            import sqlite3
            conn = sqlite3.connect(self.current_db_path)
            c = conn.cursor()
            
            # Get recent entries
            c.execute("""
                SELECT day, OpenTime, position, Result, TradeRatio, StoplossSize 
                FROM trading_entries 
                ORDER BY id DESC 
                LIMIT 50
            """)
            
            # Add to treeview
            for row in c.fetchall():
                self.entries_tree.insert('', tk.END, values=row)
            
            # Close connection
            conn.close()
        except Exception as e:
            logger.error(f"Error loading recent entries: {e}")
            messagebox.showerror("Error", f"Failed to load recent entries: {e}")
    
    def on_entry_double_click(self, event):
        """Handle double-click on a trading entry."""
        # Get the selected item
        selection = self.entries_tree.selection()
        if not selection:
            return
        
        item = self.entries_tree.item(selection[0])
        values = item['values']
        
        # Show entry details
        self.show_entry_details(values)
    
    def show_entry_details(self, values):
        """Show entry details in a dialog."""
        # Create a new dialog
        dialog = tk.Toplevel(self)
        dialog.title("Entry Details")
        dialog.geometry("400x300")
        dialog.transient(self)
        
        # Get full entry data
        try:
            import sqlite3
            conn = sqlite3.connect(self.current_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Get entry by matching several fields
            c.execute("""
                SELECT * FROM trading_entries 
                WHERE day = ? AND OpenTime = ? AND position = ? AND TradeRatio = ? AND StoplossSize = ?
                LIMIT 1
            """, values[0:3] + values[4:6])
            
            entry = c.fetchone()
            conn.close()
            
            if entry:
                # Create a frame
                frame = ttk.Frame(dialog, padding=10)
                frame.pack(fill=tk.BOTH, expand=True)
                
                # Add fields
                row = 0
                for key in entry.keys():
                    ttk.Label(frame, text=f"{key}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
                    ttk.Label(frame, text=str(entry[key])).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
                    row += 1
            else:
                ttk.Label(dialog, text="Entry not found").pack(pady=20)
        except Exception as e:
            logger.error(f"Error getting entry details: {e}")
            ttk.Label(dialog, text=f"Error: {e}").pack(pady=20)
        
        # Add close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def open_new_entry(self):
        """Open dialog for a new backtest entry."""
        if not self.current_db_path or not self.current_symbol:
            messagebox.showerror("Error", "Please open a database first")
            return
        
        BacktestEntryDialog(self, self.year_var.get(), self.month_var.get(), self.current_symbol, self.current_db_path)
    
    def open_batch_backtest(self):
        """Open dialog for batch backtesting."""
        messagebox.showinfo("Batch Backtest", "Batch backtest feature is not implemented yet")
    
    def apply_filters(self):
        """Apply filters to the analysis."""
        self.update_analysis()
    
    def update_analysis(self):
        """Update the analysis with current filters."""
        if not self.current_db_path:
            return
        
        # Prepare filters
        filters = {}
        if self.filter_position_var.get() != "All":
            filters['position'] = self.filter_position_var.get()
        
        if self.filter_h4_var.get() != "All":
            filters['H4'] = self.filter_h4_var.get()
        
        if self.filter_result_var.get() != "All":
            filters['Result'] = self.filter_result_var.get()
        
        # Get statistics
        try:
            stats = get_trading_statistics(self.current_db_path, filters)
            
            # Update statistics labels
            self.total_trades_label.config(text=str(stats['total_trades']))
            self.win_rate_label.config(text=f"{stats['win_rate']:.1f}%")
            self.avg_duration_label.config(text=f"{stats['average_duration']:.1f} hours")
            
            # Update graphs
            self.update_equity_graph()
            self.update_win_rate_graph(stats)
            self.update_drawdown_graph()
        except Exception as e:
            logger.error(f"Error updating analysis: {e}")
            messagebox.showerror("Error", f"Failed to update analysis: {e}")
    
    def update_equity_graph(self):
        """Update the equity curve graph."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.current_db_path)
            
            # Get trading entries
            query = """
                SELECT * FROM trading_entries 
                WHERE Result IN ('Winning', 'Losing')
                ORDER BY StartDatetime
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                # Generate equity curve
                equity_curve = generate_equity_curve(df.to_dict('records'))
                
                # Plot equity curve
                self.equity_fig.clear()
                ax = self.equity_fig.add_subplot(111)
                
                ax.plot(range(len(equity_curve)), equity_curve['balance'], marker='o', linestyle='-')
                
                # Add trade markers
                for i, row in equity_curve.iterrows():
                    color = 'green' if row['trade_result'] == 'Winning' else 'red'
                    ax.plot(i, row['balance'], marker='o', color=color)
                
                ax.set_title('Equity Curve')
                ax.set_xlabel('Trade Number')
                ax.set_ylabel('Balance')
                ax.grid(True)
                
                self.equity_fig.tight_layout()
                self.equity_canvas.draw()
        except Exception as e:
            logger.error(f"Error updating equity graph: {e}")
            self.equity_fig.clear()
            ax = self.equity_fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Error: {e}", ha='center', va='center')
            self.equity_canvas.draw()
    
    def update_win_rate_graph(self, stats):
        """Update the win rate analysis graph."""
        try:
            self.win_rate_fig.clear()
            
            # Create subplots
            fig = self.win_rate_fig
            
            # Win rate by stop loss
            ax1 = fig.add_subplot(221)
            labels = list(stats['by_stoploss'].keys())
            win_rates = [stats['by_stoploss'][k]['win_rate'] for k in labels]
            
            ax1.bar(range(len(labels)), win_rates)
            ax1.set_xticks(range(len(labels)))
            ax1.set_xticklabels(labels)
            ax1.set_ylim(0, 100)
            ax1.set_title('Win Rate by Stop Loss')
            ax1.set_ylabel('Win Rate (%)')
            
            # Win rate by ratio
            ax2 = fig.add_subplot(222)
            labels = list(stats['by_ratio'].keys())
            win_rates = [stats['by_ratio'][k]['win_rate'] for k in labels]
            
            ax2.bar(range(len(labels)), win_rates)
            ax2.set_xticks(range(len(labels)))
            ax2.set_xticklabels(labels)
            ax2.set_ylim(0, 100)
            ax2.set_title('Win Rate by Ratio')
            
            # Win rate by session
            ax3 = fig.add_subplot(223)
            labels = list(stats['by_session'].keys())
            win_rates = [stats['by_session'][k]['win_rate'] for k in labels]
            
            ax3.bar(range(len(labels)), win_rates)
            ax3.set_xticks(range(len(labels)))
            ax3.set_xticklabels(labels)
            ax3.set_ylim(0, 100)
            ax3.set_title('Win Rate by Session')
            ax3.set_ylabel('Win Rate (%)')
            
            # Win rate by position
            ax4 = fig.add_subplot(224)
            labels = list(stats['by_position'].keys())
            win_rates = [stats['by_position'][k]['win_rate'] for k in labels]
            
            ax4.bar(range(len(labels)), win_rates)
            ax4.set_xticks(range(len(labels)))
            ax4.set_xticklabels(labels)
            ax4.set_ylim(0, 100)
            ax4.set_title('Win Rate by Position')
            
            fig.tight_layout()
            self.win_rate_canvas.draw()
        except Exception as e:
            logger.error(f"Error updating win rate graph: {e}")
            self.win_rate_fig.clear()
            ax = self.win_rate_fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Error: {e}", ha='center', va='center')
            self.win_rate_canvas.draw()
    
    def update_drawdown_graph(self):
        """Update the drawdown analysis graph."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.current_db_path)
            
            # Get trading entries
            query = """
                SELECT * FROM trading_entries 
                WHERE Result IN ('Winning', 'Losing')
                ORDER BY StartDatetime
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                # Calculate drawdown
                drawdown_data = calculate_drawdown(df.to_dict('records'))
                
                # Plot drawdown
                self.drawdown_fig.clear()
                ax = self.drawdown_fig.add_subplot(111)
                
                # Generate equity curve for plotting
                equity_curve = generate_equity_curve(df.to_dict('records'))
                
                # Plot equity curve
                ax.plot(range(len(equity_curve)), equity_curve['balance'], label='Balance')
                
                # Add drawdown periods
                if drawdown_data['drawdown_periods']:
                    for period in drawdown_data['drawdown_periods']:
                        start_idx = equity_curve[equity_curve['datetime'] == period['start']].index[0] if period['start'] in equity_curve['datetime'].values else 0
                        end_idx = equity_curve[equity_curve['datetime'] == period['end']].index[0] if period['end'] in equity_curve['datetime'].values else len(equity_curve) - 1
                        
                        ax.axvspan(start_idx, end_idx, alpha=0.3, color='red')
                
                ax.set_title(f'Drawdown Analysis (Max: {drawdown_data["max_drawdown_percent"]:.1f}%)')
                ax.set_xlabel('Trade Number')
                ax.set_ylabel('Balance')
                ax.grid(True)
                
                self.drawdown_fig.tight_layout()
                self.drawdown_canvas.draw()
        except Exception as e:
            logger.error(f"Error updating drawdown graph: {e}")
            self.drawdown_fig.clear()
            ax = self.drawdown_fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Error: {e}", ha='center', va='center')
            self.drawdown_canvas.draw()
    
    def export_to_csv(self):
        """Export trading data to CSV."""
        if not self.current_db_path:
            messagebox.showerror("Error", "Please open a database first")
            return
        
        # Ask for file path
        filepath = asksaveasfilename(
            title="Export Trading Data",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        
        if not filepath:
            return
        
        try:
            # Connect to database
            import sqlite3
            conn = sqlite3.connect(self.current_db_path)
            
            # Get trading entries
            query = "SELECT * FROM trading_entries"
            
            # Apply filters
            conditions = []
            params = []
            
            if self.filter_position_var.get() != "All":
                conditions.append("position = ?")
                params.append(self.filter_position_var.get())
            
            if self.filter_h4_var.get() != "All":
                conditions.append("H4 LIKE ?")
                params.append(f"%{self.filter_h4_var.get()}%")
            
            if self.filter_result_var.get() != "All":
                conditions.append("Result = ?")
                params.append(self.filter_result_var.get())
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Execute query
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            
            messagebox.showinfo("Export", f"Data exported to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            messagebox.showerror("Error", f"Failed to export data: {e}")
    
    def export_graphs(self):
        """Export graphs to image files."""
        if not self.current_db_path:
            messagebox.showerror("Error", "Please open a database first")
            return
        
        # Ask for directory
        from tkinter import filedialog
        directory = filedialog.askdirectory(title="Select Directory for Graph Export")
        
        if not directory:
            return
        
        try:
            # Save equity curve
            equity_path = os.path.join(directory, f"{self.current_symbol}_equity_curve.png")
            self.equity_fig.savefig(equity_path, dpi=300, bbox_inches='tight')
            
            # Save win rate analysis
            win_rate_path = os.path.join(directory, f"{self.current_symbol}_win_rate_analysis.png")
            self.win_rate_fig.savefig(win_rate_path, dpi=300, bbox_inches='tight')
            
            # Save drawdown analysis
            drawdown_path = os.path.join(directory, f"{self.current_symbol}_drawdown_analysis.png")
            self.drawdown_fig.savefig(drawdown_path, dpi=300, bbox_inches='tight')
            
            messagebox.showinfo("Export", f"Graphs exported to {directory}")
        except Exception as e:
            logger.error(f"Error exporting graphs: {e}")
            messagebox.showerror("Error", f"Failed to export graphs: {e}")