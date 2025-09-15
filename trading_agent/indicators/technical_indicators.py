"""
Technical Indicators for the Aura Trading Agent
Includes advanced indicators like ADX, VWAP, and traditional indicators
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional
import ta
try:
    from ..config import CONFIG
except ImportError:
    from trading_agent.config import CONFIG


class TechnicalIndicators:
    """Comprehensive technical indicators calculator"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = None) -> pd.Series:
        """Calculate Relative Strength Index"""
        if period is None:
            period = CONFIG.RSI_PERIOD
        return ta.momentum.RSIIndicator(prices, window=period).rsi()
    
    @staticmethod
    def calculate_macd(prices: pd.Series, 
                      fast: int = None, 
                      slow: int = None, 
                      signal: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, MACD Signal, and MACD Histogram"""
        if fast is None:
            fast = CONFIG.MACD_FAST
        if slow is None:
            slow = CONFIG.MACD_SLOW
        if signal is None:
            signal = CONFIG.MACD_SIGNAL
            
        macd_indicator = ta.trend.MACD(prices, window_slow=slow, window_fast=fast, window_sign=signal)
        
        return (
            macd_indicator.macd(),
            macd_indicator.macd_signal(),
            macd_indicator.macd_diff()
        )
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Average Directional Index (ADX) and Directional Indicators
        Returns: ADX, +DI, -DI
        """
        if period is None:
            period = CONFIG.ADX_PERIOD
            
        adx_indicator = ta.trend.ADXIndicator(high, low, close, window=period)
        
        return (
            adx_indicator.adx(),
            adx_indicator.adx_pos(),
            adx_indicator.adx_neg()
        )
    
    @staticmethod
    def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)
        """
        typical_price = (high + low + close) / 3
        cumulative_volume = volume.cumsum()
        cumulative_price_volume = (typical_price * volume).cumsum()
        
        # Avoid division by zero
        vwap = cumulative_price_volume / cumulative_volume
        vwap = vwap.fillna(method='ffill')
        
        return vwap
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, 
                                 period: int = None, 
                                 std_dev: float = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands (Upper, Middle, Lower)"""
        if period is None:
            period = CONFIG.BB_PERIOD
        if std_dev is None:
            std_dev = CONFIG.BB_STD
            
        bb_indicator = ta.volatility.BollingerBands(prices, window=period, window_dev=std_dev)
        
        return (
            bb_indicator.bollinger_hband(),
            bb_indicator.bollinger_mavg(),
            bb_indicator.bollinger_lband()
        )
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator (%K and %D)"""
        stoch_indicator = ta.momentum.StochasticOscillator(high, low, close, 
                                                         window=k_period, smooth_window=d_period)
        
        return (
            stoch_indicator.stoch(),
            stoch_indicator.stoch_signal()
        )
    
    @staticmethod
    def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        return ta.momentum.WilliamsRIndicator(high, low, close, lbp=period).williams_r()
    
    @staticmethod
    def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index"""
        return ta.trend.CCIIndicator(high, low, close, window=period).cci()
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        return ta.volatility.AverageTrueRange(high, low, close, window=period).average_true_range()
    
    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On-Balance Volume"""
        return ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    
    @staticmethod
    def calculate_support_resistance(prices: pd.Series, window: int = 20) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate dynamic support and resistance levels
        """
        rolling_min = prices.rolling(window=window).min()
        rolling_max = prices.rolling(window=window).max()
        
        # Smooth the levels
        support = rolling_min.rolling(window=5).mean()
        resistance = rolling_max.rolling(window=5).mean()
        
        return support, resistance
    
    @staticmethod
    def calculate_momentum_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive momentum indicators"""
        indicators = data.copy()
        
        # Basic momentum indicators
        indicators['rsi'] = TechnicalIndicators.calculate_rsi(data['close'])
        macd, macd_signal, macd_hist = TechnicalIndicators.calculate_macd(data['close'])
        indicators['macd'] = macd
        indicators['macd_signal'] = macd_signal
        indicators['macd_histogram'] = macd_hist
        
        # Stochastic indicators
        stoch_k, stoch_d = TechnicalIndicators.calculate_stochastic(
            data['high'], data['low'], data['close']
        )
        indicators['stoch_k'] = stoch_k
        indicators['stoch_d'] = stoch_d
        
        # Williams %R
        indicators['williams_r'] = TechnicalIndicators.calculate_williams_r(
            data['high'], data['low'], data['close']
        )
        
        # CCI
        indicators['cci'] = TechnicalIndicators.calculate_cci(
            data['high'], data['low'], data['close']
        )
        
        return indicators
    
    @staticmethod
    def calculate_trend_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive trend indicators"""
        indicators = data.copy()
        
        # ADX and Directional Indicators
        adx, di_plus, di_minus = TechnicalIndicators.calculate_adx(
            data['high'], data['low'], data['close']
        )
        indicators['adx'] = adx
        indicators['di_plus'] = di_plus
        indicators['di_minus'] = di_minus
        
        # VWAP
        indicators['vwap'] = TechnicalIndicators.calculate_vwap(
            data['high'], data['low'], data['close'], data['volume']
        )
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(data['close'])
        indicators['bb_upper'] = bb_upper
        indicators['bb_middle'] = bb_middle
        indicators['bb_lower'] = bb_lower
        
        # Support and Resistance
        support, resistance = TechnicalIndicators.calculate_support_resistance(data['close'])
        indicators['support'] = support
        indicators['resistance'] = resistance
        
        # Moving averages
        indicators['sma_20'] = data['close'].rolling(window=20).mean()
        indicators['sma_50'] = data['close'].rolling(window=50).mean()
        indicators['ema_12'] = data['close'].ewm(span=12).mean()
        indicators['ema_26'] = data['close'].ewm(span=26).mean()
        
        return indicators
    
    @staticmethod
    def calculate_volume_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive volume indicators"""
        indicators = data.copy()
        
        # On-Balance Volume
        indicators['obv'] = TechnicalIndicators.calculate_obv(data['close'], data['volume'])
        
        # Volume Moving Average
        indicators['volume_sma'] = data['volume'].rolling(window=20).mean()
        
        # Volume Rate of Change
        indicators['volume_roc'] = data['volume'].pct_change(periods=10)
        
        # Accumulation/Distribution Line
        indicators['ad_line'] = ta.volume.AccDistIndexIndicator(
            data['high'], data['low'], data['close'], data['volume']
        ).acc_dist_index()
        
        # Chaikin Money Flow
        indicators['cmf'] = ta.volume.ChaikinMoneyFlowIndicator(
            data['high'], data['low'], data['close'], data['volume']
        ).chaikin_money_flow()
        
        return indicators
    
    @staticmethod
    def calculate_volatility_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive volatility indicators"""
        indicators = data.copy()
        
        # Average True Range
        indicators['atr'] = TechnicalIndicators.calculate_atr(
            data['high'], data['low'], data['close']
        )
        
        # Historical Volatility
        returns = data['close'].pct_change()
        indicators['volatility'] = returns.rolling(window=20).std() * np.sqrt(252)
        
        # Donchian Channels
        indicators['donchian_high'] = data['high'].rolling(window=20).max()
        indicators['donchian_low'] = data['low'].rolling(window=20).min()
        indicators['donchian_middle'] = (indicators['donchian_high'] + indicators['donchian_low']) / 2
        
        # Keltner Channels
        ema_20 = data['close'].ewm(span=20).mean()
        atr_10 = TechnicalIndicators.calculate_atr(data['high'], data['low'], data['close'])
        indicators['keltner_upper'] = ema_20 + (2 * atr_10)
        indicators['keltner_lower'] = ema_20 - (2 * atr_10)
        indicators['keltner_middle'] = ema_20
        
        return indicators
    
    @staticmethod
    def calculate_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators for the dataset"""
        # Start with original data
        result = data.copy()
        
        # Add all indicator categories
        result = TechnicalIndicators.calculate_momentum_indicators(result)
        result = TechnicalIndicators.calculate_trend_indicators(result)
        result = TechnicalIndicators.calculate_volume_indicators(result)
        result = TechnicalIndicators.calculate_volatility_indicators(result)
        
        # Add additional derived indicators
        result['price_above_vwap'] = (result['close'] > result['vwap']).astype(int)
        result['bb_position'] = (result['close'] - result['bb_lower']) / (result['bb_upper'] - result['bb_lower'])
        result['rsi_oversold'] = (result['rsi'] < 30).astype(int)
        result['rsi_overbought'] = (result['rsi'] > 70).astype(int)
        
        # Trend strength
        result['trend_strength'] = np.where(
            result['adx'] > 25,
            np.where(result['di_plus'] > result['di_minus'], 1, -1),  # Strong trend
            0  # Weak trend
        )
        
        return result
    
    @staticmethod
    def get_signal_strength(indicators: pd.DataFrame) -> pd.Series:
        """
        Calculate overall signal strength based on multiple indicators
        Returns a score from -1 (strong sell) to 1 (strong buy)
        """
        signals = pd.DataFrame(index=indicators.index)
        
        # RSI signals
        signals['rsi_signal'] = np.where(
            indicators['rsi'] < 30, 0.3,  # Oversold - buy signal
            np.where(indicators['rsi'] > 70, -0.3, 0)  # Overbought - sell signal
        )
        
        # MACD signals
        signals['macd_signal'] = np.where(
            indicators['macd'] > indicators['macd_signal'], 0.2, -0.2
        )
        
        # ADX trend signals
        signals['adx_signal'] = np.where(
            indicators['adx'] > 25,
            np.where(indicators['di_plus'] > indicators['di_minus'], 0.25, -0.25),
            0
        )
        
        # Bollinger Bands signals
        signals['bb_signal'] = np.where(
            indicators['close'] < indicators['bb_lower'], 0.2,  # Oversold
            np.where(indicators['close'] > indicators['bb_upper'], -0.2, 0)  # Overbought
        )
        
        # Volume confirmation
        volume_above_avg = indicators['volume'] > indicators['volume_sma']
        signals['volume_confirmation'] = np.where(volume_above_avg, 0.1, -0.05)
        
        # Calculate weighted signal strength
        signal_strength = signals.sum(axis=1)
        
        # Normalize to [-1, 1] range
        signal_strength = np.clip(signal_strength, -1, 1)
        
        return signal_strength