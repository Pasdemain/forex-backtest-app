"""
Main Application Window

This module contains the main application window and UI framework.
"""

import logging
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.filedialog import askopenfilename
import threading

from src.utils.config import get_config, save_config
from src.gui.setup_panel import SetupPanel
from src.gui.backtest_panel import BacktestPanel

logger = logging.getLogger(__name__)

class MainApplication(ttk.Frame):
    """Main application window."""
    
    def __init__(self, master=None):
        """Initialize the main application window."""
        super().__init__(master)
        self.master = master
        self.config = get_config()
        
        self.setup_ui()
        self.pack(fill=tk.BOTH, expand=True)
        
        # Initialize state variables
        self.current_db_path = None
        self.current_symbol = None
        
        # Set up GUI appearance
        self.apply_styles()
        
        # Configure window
        self.configure_window()
        
        logger.info("Main application initialized")
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create setup panel
        self.setup_panel = SetupPanel(self.notebook, self)
        self.notebook.add(self.setup_panel, text="Setup")
        
        # Create backtest panel
        self.backtest_panel = BacktestPanel(self.notebook, self)
        self.notebook.add(self.backtest_panel, text="Backtest")
        
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create menu
        self.create_menu()
    
    def create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.master)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Database", command=self.open_database)
        file_menu.add_command(label="Create New Database", command=self.create_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Import News Data", command=self.import_news)
        tools_menu.add_command(label="Analyze News Impact", command=self.analyze_news)
        tools_menu.add_separator()
        tools_menu.add_command(label="Settings", command=self.open_settings)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.open_documentation)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.master.config(menu=menubar)
    
    def apply_styles(self):
        """Apply styling to the application."""
        style = ttk.Style()
        
        # Configure colors
        accent_color = self.config['gui']['accent_color']
        
        style.configure("TFrame", background="#f5f5f5")
        style.configure("TNotebook", background="#f5f5f5")
        style.configure("TNotebook.Tab", background="#e0e0e0", padding=[10, 2], font=(self.config['gui']['font']['family'], self.config['gui']['font']['size']))
        style.map("TNotebook.Tab", background=[("selected", accent_color)], foreground=[("selected", "#ffffff")])
        
        style.configure("TButton", padding=6, relief="flat", background="#e0e0e0", font=(self.config['gui']['font']['family'], self.config['gui']['font']['size']))
        style.map("TButton", background=[("active", accent_color)], foreground=[("active", "#ffffff")])
        
        style.configure("TLabel", background="#f5f5f5", font=(self.config['gui']['font']['family'], self.config['gui']['font']['size']))
        style.configure("TEntry", padding=6, font=(self.config['gui']['font']['family'], self.config['gui']['font']['size']))
        style.configure("TCombobox", padding=4, font=(self.config['gui']['font']['family'], self.config['gui']['font']['size']))
        
        # Apply styles to the root window
        self.master.configure(background="#f5f5f5")
    
    def configure_window(self):
        """Configure the main window."""
        # Set window title
        self.master.title("Forex Backtest Application")
        
        # Set window size
        window_width = 1000
        window_height = 700
        self.master.geometry(f"{window_width}x{window_height}")
        
        # Set window position
        x_position = self.config['gui']['window_position']['x']
        y_position = self.config['gui']['window_position']['y']
        self.master.geometry(f"+{x_position}+{y_position}")
        
        # Set window icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'icon.ico')
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")
        
        # Make window resizable
        self.master.resizable(True, True)
        
        # Set minimum size
        self.master.minsize(800, 600)
        
        # Configure closing event
        self.master.protocol("WM_DELETE_WINDOW", self.quit_app)
    
    def open_database(self):
        """Open an existing database file."""
        db_path = askopenfilename(
            title="Select Database File",
            filetypes=[("SQLite Database", "*.db")],
            initialdir=self.config['database']['path']
        )
        
        if db_path:
            try:
                # Extract symbol from filename
                db_name = os.path.basename(db_path)
                symbol = db_name.replace('trading_data_', '').replace('.db', '')
                
                # Set current database and symbol
                self.current_db_path = db_path
                self.current_symbol = symbol
                
                # Update status
                self.status_var.set(f"Database opened: {db_path}")
                
                # Notify panels
                self.setup_panel.on_database_opened(db_path, symbol)
                self.backtest_panel.on_database_opened(db_path, symbol)
                
                # Switch to backtest tab
                self.notebook.select(1)  # Backtest tab index
                
                logger.info(f"Opened database: {db_path}")
                messagebox.showinfo("Database Opened", f"Successfully opened database for {symbol}")
            except Exception as e:
                logger.error(f"Error opening database: {e}")
                messagebox.showerror("Error", f"Failed to open database: {e}")
    
    def create_database(self):
        """Create a new database."""
        # Show setup panel and trigger database creation
        self.notebook.select(0)  # Setup tab index
        self.setup_panel.trigger_database_creation()
    
    def import_news(self):
        """Import news data from Excel."""
        if not self.current_db_path:
            messagebox.showwarning("Warning", "Please open a database first")
            return
        
        excel_path = askopenfilename(
            title="Select News Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls")],
            initialdir=os.path.expanduser("~")
        )
        
        if excel_path:
            # Trigger news import in setup panel
            self.notebook.select(0)  # Setup tab index
            self.setup_panel.import_news_from_excel(excel_path, self.current_db_path)
    
    def analyze_news(self):
        """Analyze news impact."""
        if not self.current_db_path:
            messagebox.showwarning("Warning", "Please open a database first")
            return
        
        # Trigger news analysis in setup panel
        self.notebook.select(0)  # Setup tab index
        self.setup_panel.analyze_news_impact(self.current_db_path, self.current_symbol)
    
    def open_settings(self):
        """Open settings dialog."""
        # Create a new dialog for settings
        settings_dialog = tk.Toplevel(self.master)
        settings_dialog.title("Settings")
        settings_dialog.geometry("600x400")
        settings_dialog.transient(self.master)
        settings_dialog.grab_set()
        
        # Create notebook for settings categories
        settings_notebook = ttk.Notebook(settings_dialog)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General settings
        general_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(general_frame, text="General")
        
        # Database settings
        database_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(database_frame, text="Database")
        
        # Trading settings
        trading_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(trading_frame, text="Trading")
        
        # Appearance settings
        appearance_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(appearance_frame, text="Appearance")
        
        # Populate settings frames
        self.populate_general_settings(general_frame)
        self.populate_database_settings(database_frame)
        self.populate_trading_settings(trading_frame)
        self.populate_appearance_settings(appearance_frame)
        
        # Add save button
        save_button = ttk.Button(settings_dialog, text="Save Settings", command=lambda: self.save_settings(settings_dialog))
        save_button.pack(side=tk.RIGHT, padx=10, pady=10)
    
    def populate_general_settings(self, parent):
        """Populate general settings frame."""
        # News settings
        ttk.Label(parent, text="News Settings", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=10)
        
        ttk.Label(parent, text="Excel Path:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        excel_path_var = tk.StringVar(value=self.config['news']['excel_path'])
        excel_path_entry = ttk.Entry(parent, textvariable=excel_path_var, width=40)
        excel_path_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        browse_button = ttk.Button(parent, text="Browse", command=lambda: self.browse_excel_path(excel_path_var))
        browse_button.grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Label(parent, text="Hours Before News:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        hours_before_var = tk.IntVar(value=self.config['news']['hours_before'])
        hours_before_spinbox = ttk.Spinbox(parent, from_=1, to=24, textvariable=hours_before_var, width=5)
        hours_before_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(parent, text="Hours After News:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        hours_after_var = tk.IntVar(value=self.config['news']['hours_after'])
        hours_after_spinbox = ttk.Spinbox(parent, from_=1, to=24, textvariable=hours_after_var, width=5)
        hours_after_spinbox.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save references to variables
        self.settings_vars = {
            'news.excel_path': excel_path_var,
            'news.hours_before': hours_before_var,
            'news.hours_after': hours_after_var
        }
    
    def populate_database_settings(self, parent):
        """Populate database settings frame."""
        ttk.Label(parent, text="Database Path:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        db_path_var = tk.StringVar(value=self.config['database']['path'])
        db_path_entry = ttk.Entry(parent, textvariable=db_path_var, width=40)
        db_path_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        browse_button = ttk.Button(parent, text="Browse", command=lambda: self.browse_db_path(db_path_var))
        browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        # MT5 settings
        ttk.Label(parent, text="MetaTrader 5 Settings", font=("Helvetica", 12, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=10)
        
        ttk.Label(parent, text="Timezone:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        timezone_var = tk.StringVar(value=self.config['mt5']['timezone'])
        timezones = ["Etc/GMT-12", "Etc/GMT-11", "Etc/GMT-10", "Etc/GMT-9", "Etc/GMT-8", "Etc/GMT-7", "Etc/GMT-6", "Etc/GMT-5", "Etc/GMT-4", "Etc/GMT-3", "Etc/GMT-2", "Etc/GMT-1", "Etc/GMT", "Etc/GMT+1", "Etc/GMT+2", "Etc/GMT+3", "Etc/GMT+4", "Etc/GMT+5", "Etc/GMT+6", "Etc/GMT+7", "Etc/GMT+8", "Etc/GMT+9", "Etc/GMT+10", "Etc/GMT+11", "Etc/GMT+12"]
        timezone_combo = ttk.Combobox(parent, textvariable=timezone_var, values=timezones)
        timezone_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(parent, text="History Days:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        history_days_var = tk.IntVar(value=self.config['mt5']['history_days'])
        history_days_spinbox = ttk.Spinbox(parent, from_=1, to=1000, textvariable=history_days_var, width=5)
        history_days_spinbox.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Add to settings vars
        self.settings_vars.update({
            'database.path': db_path_var,
            'mt5.timezone': timezone_var,
            'mt5.history_days': history_days_var
        })
    
    def populate_trading_settings(self, parent):
        """Populate trading settings frame."""
        # Stoploss sizes
        ttk.Label(parent, text="Stoploss Sizes (comma-separated):").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        sl_sizes_str = ','.join(str(x) for x in self.config['trading']['stoploss_sizes'])
        sl_sizes_var = tk.StringVar(value=sl_sizes_str)
        sl_sizes_entry = ttk.Entry(parent, textvariable=sl_sizes_var, width=20)
        sl_sizes_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Trade ratios
        ttk.Label(parent, text="Trade Ratios (comma-separated):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        ratios_str = ','.join(str(x) for x in self.config['trading']['trade_ratios'])
        ratios_var = tk.StringVar(value=ratios_str)
        ratios_entry = ttk.Entry(parent, textvariable=ratios_var, width=20)
        ratios_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Currency pairs list
        ttk.Label(parent, text="Currency Pairs:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        currency_pairs = self.config['mt5']['symbols']
        currency_vars = []
        
        # Display symbols in a 3-column grid
        for i, pair in enumerate(currency_pairs):
            var = tk.BooleanVar(value=True)
            currency_vars.append((pair, var))
            cb = ttk.Checkbutton(frame, text=pair, variable=var)
            cb.grid(row=i//3, column=i%3, sticky=tk.W, padx=10, pady=2)
        
        # Add to settings vars
        self.settings_vars.update({
            'trading.stoploss_sizes': sl_sizes_var,
            'trading.trade_ratios': ratios_var,
            'trading.currency_pairs': currency_vars
        })
    
    def populate_appearance_settings(self, parent):
        """Populate appearance settings frame."""
        # Accent color
        ttk.Label(parent, text="Accent Color:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        accent_color_var = tk.StringVar(value=self.config['gui']['accent_color'])
        accent_color_entry = ttk.Entry(parent, textvariable=accent_color_var, width=10)
        accent_color_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        color_preview = tk.Frame(parent, width=20, height=20, bg=self.config['gui']['accent_color'])
        color_preview.grid(row=0, column=2, padx=5)
        accent_color_var.trace_add("write", lambda *args: color_preview.configure(bg=accent_color_var.get()))
        
        # Font settings
        ttk.Label(parent, text="Font Family:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        font_family_var = tk.StringVar(value=self.config['gui']['font']['family'])
        font_families = ["Arial", "Helvetica", "Times", "Courier", "Verdana", "Tahoma"]
        font_family_combo = ttk.Combobox(parent, textvariable=font_family_var, values=font_families)
        font_family_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(parent, text="Font Size:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        font_size_var = tk.IntVar(value=self.config['gui']['font']['size'])
        font_size_spinbox = ttk.Spinbox(parent, from_=8, to=16, textvariable=font_size_var, width=5)
        font_size_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Window position
        ttk.Label(parent, text="Default Window Position:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        position_frame = ttk.Frame(parent)
        position_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(position_frame, text="X:").pack(side=tk.LEFT)
        x_pos_var = tk.IntVar(value=self.config['gui']['window_position']['x'])
        x_pos_spinbox = ttk.Spinbox(position_frame, from_=0, to=3000, textvariable=x_pos_var, width=5)
        x_pos_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(position_frame, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
        y_pos_var = tk.IntVar(value=self.config['gui']['window_position']['y'])
        y_pos_spinbox = ttk.Spinbox(position_frame, from_=0, to=3000, textvariable=y_pos_var, width=5)
        y_pos_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Add to settings vars
        self.settings_vars.update({
            'gui.accent_color': accent_color_var,
            'gui.font.family': font_family_var,
            'gui.font.size': font_size_var,
            'gui.window_position.x': x_pos_var,
            'gui.window_position.y': y_pos_var
        })
    
    def browse_excel_path(self, var):
        """Browse for Excel file path."""
        path = askopenfilename(
            title="Select News Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls")],
            initialdir=os.path.expanduser("~")
        )
        if path:
            var.set(path)
    
    def browse_db_path(self, var):
        """Browse for database directory."""
        path = tk.filedialog.askdirectory(
            title="Select Database Directory",
            initialdir=os.path.expanduser("~")
        )
        if path:
            var.set(path)
    
    def save_settings(self, dialog):
        """Save settings and close the dialog."""
        try:
            # Update config with new values
            # News settings
            self.config['news']['excel_path'] = self.settings_vars['news.excel_path'].get()
            self.config['news']['hours_before'] = self.settings_vars['news.hours_before'].get()
            self.config['news']['hours_after'] = self.settings_vars['news.hours_after'].get()
            
            # Database settings
            self.config['database']['path'] = self.settings_vars['database.path'].get()
            self.config['mt5']['timezone'] = self.settings_vars['mt5.timezone'].get()
            self.config['mt5']['history_days'] = self.settings_vars['mt5.history_days'].get()
            
            # Trading settings
            self.config['trading']['stoploss_sizes'] = [int(x.strip()) for x in self.settings_vars['trading.stoploss_sizes'].get().split(',')]
            self.config['trading']['trade_ratios'] = [int(x.strip()) for x in self.settings_vars['trading.trade_ratios'].get().split(',')]
            
            # Update symbols list based on checkboxes
            selected_symbols = [pair for pair, var in self.settings_vars['trading.currency_pairs'] if var.get()]
            if selected_symbols:  # Only update if at least one symbol is selected
                self.config['mt5']['symbols'] = selected_symbols
            
            # Appearance settings
            self.config['gui']['accent_color'] = self.settings_vars['gui.accent_color'].get()
            self.config['gui']['font']['family'] = self.settings_vars['gui.font.family'].get()
            self.config['gui']['font']['size'] = self.settings_vars['gui.font.size'].get()
            self.config['gui']['window_position']['x'] = self.settings_vars['gui.window_position.x'].get()
            self.config['gui']['window_position']['y'] = self.settings_vars['gui.window_position.y'].get()
            
            # Save config to file
            save_config(self.config)
            
            # Apply new styles
            self.apply_styles()
            
            # Close dialog
            dialog.destroy()
            
            messagebox.showinfo("Settings", "Settings saved successfully. Some changes may require restarting the application.")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def show_about(self):
        """Show about dialog."""
        about_dialog = tk.Toplevel(self.master)
        about_dialog.title("About Forex Backtest Application")
        about_dialog.geometry("400x300")
        about_dialog.transient(self.master)
        about_dialog.grab_set()
        
        # Add content
        ttk.Label(about_dialog, text="Forex Backtest Application", font=("Helvetica", 16, "bold")).pack(pady=(20, 10))
        ttk.Label(about_dialog, text="Version 1.0.0").pack()
        ttk.Label(about_dialog, text="A comprehensive tool for backtesting forex trading strategies").pack(pady=(10, 20))
        ttk.Label(about_dialog, text="© 2025 Your Name").pack()
        
        # Add close button
        ttk.Button(about_dialog, text="Close", command=about_dialog.destroy).pack(pady=20)
    
    def open_documentation(self):
        """Open the documentation."""
        # In a real application, this would open a browser or documentation window
        messagebox.showinfo("Documentation", "Documentation is not available in this version.")
    
    def update_status(self, message):
        """Update the status bar message."""
        self.status_var.set(message)
    
    def run_in_thread(self, func, args=(), on_complete=None):
        """Run a function in a separate thread."""
        def thread_func():
            try:
                result = func(*args)
                if on_complete:
                    self.master.after(0, lambda: on_complete(result))
            except Exception as e:
                logger.error(f"Error in thread: {e}")
                self.master.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        t = threading.Thread(target=thread_func)
        t.daemon = True
        t.start()
        return t
    
    def quit_app(self):
        """Quit the application."""
        # Save window position
        x = self.master.winfo_x()
        y = self.master.winfo_y()
        self.config['gui']['window_position']['x'] = x
        self.config['gui']['window_position']['y'] = y
        save_config(self.config)
        
        self.master.destroy()
