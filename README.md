# Forex Backtest Application

A comprehensive application for backtesting forex trading strategies with integrated news event analysis.

## Features

- **Data Management**: Import historical price data from MetaTrader 5
- **News Analysis**: Track economic news events and their impact on price
- **Backtesting**: Test trading strategies with customizable parameters
- **Performance Metrics**: Analyze win rates across different stop loss and risk-reward ratios
- **User-Friendly Interface**: Intuitive GUI guides you through the entire workflow

## Requirements

- Python 3.8+
- MetaTrader 5 installed with proper login credentials
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository
```
git clone https://github.com/Pasdemain/forex-backtest-app.git
cd forex-backtest-app
```

2. Install required packages
```
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the main application:
```
python main.py
```

This will launch the unified GUI that guides you through the workflow.

### Workflow

1. **Setup Database**: Create a new database for your currency pair
2. **Import Data**: Import price history from MetaTrader 5
3. **Import News**: Add economic news events to your database
4. **Run Backtests**: Test your trading strategies with different parameters
5. **View Results**: Analyze performance metrics and refine your strategy

## Project Structure

- `main.py` - Entry point for the application
- `src/` - Source code directory
  - `data/` - Data handling modules
    - `mt5_connector.py` - MetaTrader 5 connection and data fetching
    - `database.py` - Database creation and operations
  - `analysis/` - Analysis modules
    - `news.py` - News data processing
    - `backtest.py` - Strategy backtesting logic
  - `gui/` - User interface
    - `main_window.py` - Main application window
    - `setup_panel.py` - Database and connection setup
    - `backtest_panel.py` - Backtesting interface
- `utils/` - Utility functions
  - `time_utils.py` - Time handling utilities
  - `config.py` - Configuration management

## Debugging

The application includes comprehensive logging:

- Logs are stored in the `logs/` directory
- Each module logs its actions separately
- Errors are clearly tracked with timestamps
- The GUI provides error messages for common issues

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
