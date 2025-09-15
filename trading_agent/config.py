"""
Configuration settings for the Aura Trading Agent
"""
import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TradingConfig:
    # Trading parameters
    MAX_POSITION_SIZE: float = 0.02  # 2% of portfolio per trade
    MIN_RISK_REWARD_RATIO: float = 2.0  # Minimum 2:1 risk-reward
    MAX_DAILY_LOSS: float = 0.05  # 5% max daily loss
    TARGET_SUCCESS_RATE: float = 0.80  # 80% target success rate
    
    # Technical indicators parameters
    RSI_PERIOD: int = 14
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    ADX_PERIOD: int = 14
    VWAP_PERIOD: int = 20
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    
    # ML Model parameters
    LOOKBACK_PERIOD: int = 60  # Days of historical data for predictions
    ENSEMBLE_MODELS: List[str] = None
    MODEL_RETRAIN_INTERVAL: int = 7  # Days
    
    # Risk management
    TRAILING_STOP_PERCENT: float = 0.02  # 2% trailing stop
    MAX_CORRELATION_EXPOSURE: float = 0.15  # 15% max in correlated assets
    VOLATILITY_SCALING: bool = True
    
    # Data and API settings
    DATA_PROVIDER: str = "yfinance"  # Can be extended to other providers
    REFRESH_INTERVAL: int = 5  # Seconds between data updates
    MAX_API_CALLS_PER_MINUTE: int = 100
    
    # Logging and monitoring
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "trading_agent.log"
    ENABLE_PERFORMANCE_MONITORING: bool = True
    
    def __post_init__(self):
        if self.ENSEMBLE_MODELS is None:
            self.ENSEMBLE_MODELS = [
                'random_forest',
                'gradient_boosting',
                'lstm',
                'svm'
            ]

@dataclass
class MarketHours:
    """Market hours configuration"""
    MARKET_OPEN: str = "09:30"
    MARKET_CLOSE: str = "16:00"
    TIMEZONE: str = "US/Eastern"
    PRE_MARKET_START: str = "04:00"
    AFTER_MARKET_END: str = "20:00"

@dataclass
class SafetyLimits:
    """Safety limits to prevent adverse trading"""
    MAX_TRADES_PER_DAY: int = 50
    MIN_ACCOUNT_BALANCE: float = 1000.0
    MAX_DRAWDOWN_PERCENT: float = 0.10  # 10% max drawdown
    CIRCUIT_BREAKER_LOSS: float = 0.08  # 8% loss triggers circuit breaker
    VOLATILITY_THRESHOLD: float = 0.05  # 5% volatility threshold

# Environment variables
API_KEYS = {
    'ALPHA_VANTAGE': os.getenv('ALPHA_VANTAGE_API_KEY'),
    'FINNHUB': os.getenv('FINNHUB_API_KEY'),
    'POLYGON': os.getenv('POLYGON_API_KEY')
}

# Watchlist of stocks to trade
DEFAULT_WATCHLIST = [
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
    'NVDA', 'META', 'NFLX', 'AMD', 'CRM',
    'ADBE', 'PYPL', 'INTC', 'ORCL', 'IBM'
]

# Global configuration instances
CONFIG = TradingConfig()
MARKET_HOURS = MarketHours()
SAFETY_LIMITS = SafetyLimits()