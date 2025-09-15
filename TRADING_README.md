# Aura Trading Agent

This directory contains both the GitHub Pages mental health website and the Aura Trading Agent system.

## Directory Structure

- `index.html` - Mental health apps website (GitHub Pages)
- `trading_agent/` - Aura Trading Agent implementation
- `tests/` - Test suite for the trading agent
- `docs/` - Documentation for trading strategies and system

## Aura Trading Agent

The Aura Trading Agent is designed to achieve an 80% success rate in day trading stocks using advanced AI and ML models.

### Key Features

1. **AI Decision-Making**: ML models with technical indicators and ensemble methods
2. **Risk Management**: Dynamic portfolio management with trailing stop-loss
3. **Error Handling**: Comprehensive error categorization and recovery
4. **Performance**: Optimized for high-frequency trading with minimal latency
5. **Testing**: Extensive test suite with backtesting capabilities

### Quick Start

```bash
# Install dependencies
pip install -r trading_agent/requirements.txt

# Run the trading agent
python trading_agent/main.py

# Run tests
python -m pytest tests/

# Run backtesting
python trading_agent/backtesting.py
```

### Documentation

See the `docs/` directory for detailed documentation on trading strategies, risk management, and system architecture.