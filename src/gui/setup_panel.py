"""
Setup Panel Module

This module provides the UI for database creation, symbol selection,
and data fetching functions.
"""

import logging
import os
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

from src.utils.config import get_config
from src.data.mt5_connector import (
    fetch_and_store_data_for_symbol,
    get_available_symbols, 
    initialize_mt5, 
    shutdown_mt5,
    validate_symbol
)
from src.data.database import (
    get_db_path,
    init_db
)
from src.analysis.news import (
    import_news_from_excel,
    analyze_news_impact
)

logger = logging.getLogger(__name__)

class SetupPanel(ttk.Frame):
    """Setup panel for database creation and data import."""
    
    def __init__(self, parent, main_app):
        """Initialize the setup panel."""
        super().__init__(parent)
        self.parent = parent
        self.main_app = main_app
        self.config = get_config()
        
        # Initialize state variables
        self.current_db_path = None
        self.current_symbol = None
        
        # Create UI
        self.create_ui()
    
    def create_ui(self):
        """Create the user interface."""
        # Create a frame for the setup content
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title label
        title_label = ttk.Label(content_frame, text="Database Setup", font=("Helvetica", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 20))
        
        # Symbol selection
        ttk.Label(content_frame, text="Symbol:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Symbol dropdown
        self.symbol_var = tk.StringVar()
        self.symbol_var.set(self.config['mt5']['symbols'][0])
        self.symbol_combo = ttk.Combobox(content_frame, textvariable=self.symbol_var, values=self.config['mt5']['symbols'], width=15)
        self.symbol_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Refresh symbols button
        refresh_button = ttk.Button(content_frame, text="Refresh List", command=self.refresh_symbols)
        refresh_button.grid(row=1, column=2, padx=5, pady=5)
        
        # Timeframes selection
        ttk.Label(content_frame, text="Timeframes:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Timeframes checkboxes
        timeframes_frame = ttk.Frame(content_frame)
        timeframes_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        self.timeframe_vars = {}
        for i, tf in enumerate(self.config['mt5']['timeframes']):
            var = tk.BooleanVar(value=True)
            self.timeframe_vars[tf] = var
            cb = ttk.Checkbutton(timeframes_frame, text=tf, variable=var)
            cb.grid(row=0, column=i, padx=5)
        
        # Data range
        ttk.Label(content_frame, text="History Days:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.history_days_var = tk.IntVar(value=self.config['mt5']['history_days'])
        history_days_spinbox = ttk.Spinbox(content_frame, from_=1, to=1000, textvariable=self.history_days_var, width=5)
        history_days_spinbox.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Create/Update Database button
        create_db_button = ttk.Button(content_frame, text="Create/Update Database", command=self.create_database)
        create_db_button.grid(row=4, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=20)
        
        # Progress section
        progress_frame = ttk.LabelFrame(content_frame, text="Progress")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=10)
        
        self.progress_var = tk.StringVar(value="Ready")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # News data section
        news_frame = ttk.LabelFrame(content_frame, text="News Data")
        news_frame.grid(row=6, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=10)
        
        ttk.Label(news_frame, text="News Excel File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.news_path_var = tk.StringVar(value=self.config['news']['excel_path'])
        news_path_entry = ttk.Entry(news_frame, textvariable=self.news_path_var, width=40)
        news_path_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        browse_button = ttk.Button(news_frame, text="Browse", command=self.browse_news_file)
        browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        import_button = ttk.Button(news_frame, text="Import News Data", command=self.import_news)
        import_button.grid(row=1, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=10)
        
        analyze_button = ttk.Button(news_frame, text="Analyze News Impact", command=self.analyze_news)
        analyze_button.grid(row=2, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        
        # News Analysis Results
        self.news_results_frame = ttk.LabelFrame(content_frame, text="News Analysis Results")
        self.news_results_frame.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, padx=5, pady=10)
        
        # Create an empty canvas for news analysis chart
        self.news_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.news_canvas = FigureCanvasTkAgg(self.news_fig, self.news_results_frame)
        self.news_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Make the grid expandable
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(7, weight=1)
    
    def refresh_symbols(self):
        """Refresh the symbols list from MetaTrader 5."""
        # Start the progress bar
        self.progress_bar.start()
        self.progress_var.set("Connecting to MetaTrader 5...")
        
        def _refresh():
            try:
                if initialize_mt5():
                    symbols = get_available_symbols()
                    shutdown_mt5()
                    
                    if symbols:
                        # Update GUI on main thread
                        self.after(0, lambda: self._update_symbols(symbols))
                    else:
                        self.after(0, lambda: messagebox.showerror("Error", "Failed to get symbols from MetaTrader 5"))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Failed to initialize MetaTrader 5"))
            except Exception as e:
                logger.error(f"Error refreshing symbols: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to refresh symbols: {e}"))
            finally:
                # Stop progress bar on main thread
                self.after(0, self.progress_bar.stop)
                self.after(0, lambda: self.progress_var.set("Ready"))
        
        # Run in a separate thread
        threading.Thread(target=_refresh).start()
    
    def _update_symbols(self, symbols):
        """Update the symbols dropdown."""
        # Filter for forex and common symbols
        forex_symbols = [s for s in symbols if any(pair in s for pair in ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"])]
        
        # Add commodity symbols
        commodities = ["XAUUSD", "XAGUSD", "XPDUSD", "XPTUSD"]
        for commodity in commodities:
            if commodity in symbols and commodity not in forex_symbols:
                forex_symbols.append(commodity)
        
        # Update combobox
        self.symbol_combo['values'] = forex_symbols
        
        # Log the update
        logger.info(f"Updated symbols list with {len(forex_symbols)} symbols")
        
        messagebox.showinfo("Symbols Refreshed", f"Found {len(forex_symbols)} forex and commodity symbols.")
    
    def create_database(self):
        """Create or update the database."""
        symbol = self.symbol_var.get()
        
        if not symbol:
            messagebox.showerror("Error", "Please select a symbol")
            return
        
        # Get selected timeframes
        selected_timeframes = [tf for tf, var in self.timeframe_vars.items() if var.get()]
        if not selected_timeframes:
            messagebox.showerror("Error", "Please select at least one timeframe")
            return
        
        # Get history days
        history_days = self.history_days_var.get()
        
        # Confirm with user
        if not messagebox.askyesno("Confirm", 
                                   f"This will create/update the database for {symbol} with timeframes {', '.join(selected_timeframes)}.\n"
                                   f"It will download {history_days} days of history.\n\n"
                                   "Do you want to continue?"):
            return
        
        # Get database path
        db_path = get_db_path(symbol)
        
        # Start progress
        self.progress_bar.start()
        self.progress_var.set(f"Creating database for {symbol}...")
        
        def _create_db():
            try:
                # Initialize the database
                init_db(db_path)
                
                # Update progress
                self.after(0, lambda: self.progress_var.set(f"Downloading data for {symbol}..."))
                
                # Fetch and store data
                result = fetch_and_store_data_for_symbol(symbol, db_path, selected_timeframes, history_days)
                
                if result:
                    # Update current database path and symbol
                    self.current_db_path = db_path
                    self.current_symbol = symbol
                    
                    # Update status
                    self.after(0, lambda: self.progress_var.set(f"Database for {symbol} created/updated successfully"))
                    
                    # Notify parent
                    self.after(0, lambda: self.on_database_created(db_path, symbol))
                    
                    # Show success message
                    self.after(0, lambda: messagebox.showinfo("Success", f"Database for {symbol} created/updated successfully"))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch data for {symbol}"))
            except Exception as e:
                logger.error(f"Error creating database: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to create database: {e}"))
            finally:
                # Stop progress bar
                self.after(0, self.progress_bar.stop)
        
        # Run in a separate thread
        threading.Thread(target=_create_db).start()
    
    def on_database_created(self, db_path, symbol):
        """Handle database creation completion."""
        # Update main app
        self.main_app.current_db_path = db_path
        self.main_app.current_symbol = symbol
        
        # Update status
        self.main_app.update_status(f"Database opened: {db_path}")
        
        # Notify main app's backtest panel
        self.main_app.backtest_panel.on_database_opened(db_path, symbol)
    
    def on_database_opened(self, db_path, symbol):
        """Handle when a database is opened."""
        self.current_db_path = db_path
        self.current_symbol = symbol
        
        # Update symbol dropdown
        self.symbol_var.set(symbol)
        
        # Update status
        self.progress_var.set(f"Database for {symbol} is open")
    
    def browse_news_file(self):
        """Browse for news Excel file."""
        from tkinter.filedialog import askopenfilename
        
        filepath = askopenfilename(
            title="Select News Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls")],
            initialdir=os.path.dirname(self.news_path_var.get()) if self.news_path_var.get() else os.path.expanduser("~")
        )
        
        if filepath:
            self.news_path_var.set(filepath)
            
            # Update config
            self.config['news']['excel_path'] = filepath
            from src.utils.config import save_config
            save_config(self.config)
    
    def import_news(self):
        """Import news data from Excel."""
        if not self.current_db_path:
            messagebox.showerror("Error", "Please open or create a database first")
            return
        
        excel_path = self.news_path_var.get()
        
        if not excel_path or not os.path.exists(excel_path):
            messagebox.showerror("Error", "Please select a valid Excel file")
            return
        
        # Start progress
        self.progress_bar.start()
        self.progress_var.set("Importing news data...")
        
        # Import in a separate thread
        def _import_news():
            try:
                # Import news data
                success = import_news_from_excel(excel_path, self.current_db_path)
                
                if success:
                    self.after(0, lambda: self.progress_var.set("News data imported successfully"))
                    self.after(0, lambda: messagebox.showinfo("Success", "News data imported successfully"))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Failed to import news data"))
            except Exception as e:
                logger.error(f"Error importing news data: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to import news data: {e}"))
            finally:
                # Stop progress bar
                self.after(0, self.progress_bar.stop)
        
        threading.Thread(target=_import_news).start()
    
    def analyze_news(self):
        """Analyze news impact."""
        if not self.current_db_path:
            messagebox.showerror("Error", "Please open or create a database first")
            return
        
        # Start progress
        self.progress_bar.start()
        self.progress_var.set("Analyzing news impact...")
        
        # Analyze in a separate thread
        def _analyze_news():
            try:
                # Analyze news impact
                results = analyze_news_impact(self.current_db_path, self.current_symbol)
                
                if not results.empty:
                    # Update GUI on main thread
                    self.after(0, lambda: self._show_news_analysis(results))
                    self.after(0, lambda: self.progress_var.set("News analysis completed"))
                else:
                    self.after(0, lambda: messagebox.showinfo("Analysis", "No significant news impact found"))
                    self.after(0, lambda: self.progress_var.set("No significant news impact found"))
            except Exception as e:
                logger.error(f"Error analyzing news impact: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to analyze news impact: {e}"))
            finally:
                # Stop progress bar
                self.after(0, self.progress_bar.stop)
        
        threading.Thread(target=_analyze_news).start()
    
    def _show_news_analysis(self, results):
        """Display news analysis results."""
        # Clear the previous figure
        self.news_fig.clear()
        
        # Create a new subplot
        ax = self.news_fig.add_subplot(111)
        
        # Sort by average movement
        results_sorted = results.sort_values(by='avg_movement', ascending=False).head(10)
        
        # Plot the results
        bar_width = 0.35
        index = range(len(results_sorted))
        
        # Plot upward and downward average movements
        ax.bar(index, results_sorted['upward_mean'], bar_width, label='Upward Pips', color='green', alpha=0.7)
        ax.bar([i + bar_width for i in index], results_sorted['downward_mean'], bar_width, label='Downward Pips', color='red', alpha=0.7)
        
        # Add labels and title
        ax.set_xlabel('News Event')
        ax.set_ylabel('Average Pips Movement')
        ax.set_title(f'Top 10 News Events by Price Impact ({self.current_symbol})')
        ax.set_xticks([i + bar_width/2 for i in index])
        
        # Rotate labels for readability
        news_names = results_sorted['news'].tolist()
        shortened_names = [name[:20] + '...' if len(name) > 20 else name for name in news_names]
        ax.set_xticklabels(shortened_names, rotation=45, ha='right')
        
        ax.legend()
        
        # Adjust layout
        self.news_fig.tight_layout()
        
        # Redraw the canvas
        self.news_canvas.draw()
        
        # Display results in a popup
        results_window = tk.Toplevel(self)
        results_window.title(f"News Impact Analysis - {self.current_symbol}")
        results_window.geometry("800x600")
        results_window.transient(self)
        
        # Create a frame
        frame = ttk.Frame(results_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a treeview
        ttk.Label(frame, text="News Impact Analysis Results", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        
        # Create Treeview
        columns = ("news", "impact", "upward_count", "upward_mean", "downward_count", "downward_mean", "total_count", "avg_movement")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        # Define headings
        tree.heading("news", text="News Event")
        tree.heading("impact", text="Impact")
        tree.heading("upward_count", text="Upward Count")
        tree.heading("upward_mean", text="Upward Avg")
        tree.heading("downward_count", text="Downward Count")
        tree.heading("downward_mean", text="Downward Avg")
        tree.heading("total_count", text="Total Count")
        tree.heading("avg_movement", text="Avg Movement")
        
        # Define columns width
        tree.column("news", width=200)
        tree.column("impact", width=80)
        tree.column("upward_count", width=80)
        tree.column("upward_mean", width=80)
        tree.column("downward_count", width=80)
        tree.column("downward_mean", width=80)
        tree.column("total_count", width=80)
        tree.column("avg_movement", width=80)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Insert data
        for i, row in results.iterrows():
            tree.insert("", tk.END, values=(
                row['news'],
                row['typical_impact'],
                row['upward_count'],
                f"{row['upward_mean']:.2f}",
                row['downward_count'],
                f"{row['downward_mean']:.2f}",
                row['total_count'],
                f"{row['avg_movement']:.2f}"
            ))
        
        # Add export button
        def export_to_csv():
            from tkinter.filedialog import asksaveasfilename
            
            filepath = asksaveasfilename(
                title="Save News Analysis",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")]
            )
            
            if filepath:
                results.to_csv(filepath, index=False)
                messagebox.showinfo("Export", f"News analysis exported to {filepath}")
        
        export_frame = ttk.Frame(results_window)
        export_frame.pack(fill=tk.X, padx=10, pady=10)
        
        export_button = ttk.Button(export_frame, text="Export to CSV", command=export_to_csv)
        export_button.pack(side=tk.RIGHT)
    
    def trigger_database_creation(self):
        """Trigger database creation (called from main app)."""
        self.create_database()
    
    def import_news_from_excel(self, excel_path, db_path):
        """Import news from Excel (called from main app)."""
        self.current_db_path = db_path
        self.news_path_var.set(excel_path)
        self.import_news()
    
    def analyze_news_impact(self, db_path, symbol):
        """Analyze news impact (called from main app)."""
        self.current_db_path = db_path
        self.current_symbol = symbol
        self.analyze_news()
