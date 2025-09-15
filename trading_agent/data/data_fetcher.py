"""
Optimized Data Fetcher for high-frequency trading with minimal latency
"""
import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import time
import logging
from dataclasses import dataclass, field
import json
from asyncio_throttle import Throttler
import websocket
import threading
from queue import Queue, Empty

from ..config import CONFIG, API_KEYS, DEFAULT_WATCHLIST
from ..core.error_handler import error_handler, ErrorCategory, ErrorSeverity


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: float = 0.0
    ask: float = 0.0
    last_trade_price: float = 0.0
    last_trade_size: int = 0


@dataclass
class DataCache:
    """Data caching structure"""
    data: pd.DataFrame
    last_updated: datetime
    symbol: str
    timeframe: str
    
    def is_expired(self, max_age_seconds: int = 300) -> bool:
        """Check if cached data is expired"""
        return (datetime.now() - self.last_updated).total_seconds() > max_age_seconds


class DataFetcher:
    """Optimized data fetcher with caching and async capabilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache: Dict[str, DataCache] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.throttler = Throttler(rate_limit=CONFIG.MAX_API_CALLS_PER_MINUTE, period=60)
        
        # WebSocket connections for real-time data
        self.ws_connections: Dict[str, websocket.WebSocketApp] = {}
        self.real_time_data: Dict[str, MarketData] = {}
        self.data_queue = Queue()
        
        # Performance tracking
        self.request_times: List[float] = []
        self.failed_requests = 0
        self.total_requests = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_cached_data(self, symbol: str, timeframe: str = "1d") -> Optional[pd.DataFrame]:
        """Retrieve cached data if available and not expired"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if not cached.is_expired():
                return cached.data.copy()
        
        return None
    
    def cache_data(self, symbol: str, data: pd.DataFrame, timeframe: str = "1d"):
        """Cache fetched data"""
        cache_key = f"{symbol}_{timeframe}"
        self.cache[cache_key] = DataCache(
            data=data.copy(),
            last_updated=datetime.now(),
            symbol=symbol,
            timeframe=timeframe
        )
    
    async def fetch_historical_data(self, 
                                  symbol: str, 
                                  period: str = "1y", 
                                  interval: str = "1d",
                                  force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Fetch historical data with caching and error handling
        """
        try:
            start_time = time.time()
            self.total_requests += 1
            
            # Check cache first
            if not force_refresh:
                cached_data = self.get_cached_data(symbol, interval)
                if cached_data is not None:
                    self.logger.debug(f"Using cached data for {symbol}")
                    return cached_data
            
            # Use throttler for rate limiting
            async with self.throttler:
                # Fetch data using yfinance (primary method)
                data = await self._fetch_yfinance_data(symbol, period, interval)
                
                if data is not None and not data.empty:
                    # Cache the data
                    self.cache_data(symbol, data, interval)
                    
                    # Track performance
                    request_time = time.time() - start_time
                    self.request_times.append(request_time)
                    
                    # Keep only last 100 request times
                    if len(self.request_times) > 100:
                        self.request_times = self.request_times[-100:]
                    
                    self.logger.debug(f"Fetched {len(data)} rows for {symbol} in {request_time:.3f}s")
                    return data
                else:
                    # Try alternative data source
                    return await self._fetch_alternative_data(symbol, period, interval)
                    
        except Exception as e:
            self.failed_requests += 1
            error_handler.handle_error(
                e, ErrorCategory.DATA_ERROR, ErrorSeverity.MEDIUM,
                context={'symbol': symbol, 'period': period, 'interval': interval}
            )
            
            # Try to return cached data even if expired
            cached_data = self.get_cached_data(symbol, interval)
            if cached_data is not None:
                self.logger.warning(f"Using expired cached data for {symbol}")
                return cached_data
            
            return None
    
    async def _fetch_yfinance_data(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """Fetch data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval, prepost=True, auto_adjust=True)
            
            if data.empty:
                return None
            
            # Standardize column names
            data.columns = [col.lower() for col in data.columns]
            
            # Add derived features
            data['returns'] = data['close'].pct_change()
            data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
            data['volatility'] = data['returns'].rolling(window=20).std()
            
            return data
            
        except Exception as e:
            self.logger.warning(f"YFinance fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_alternative_data(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """Fetch data from alternative sources"""
        try:
            # Try Alpha Vantage if API key is available
            if API_KEYS.get('ALPHA_VANTAGE'):
                return await self._fetch_alpha_vantage_data(symbol)
            
            # Try Polygon if API key is available
            if API_KEYS.get('POLYGON'):
                return await self._fetch_polygon_data(symbol)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Alternative data fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_alpha_vantage_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data from Alpha Vantage API"""
        if not self.session or not API_KEYS.get('ALPHA_VANTAGE'):
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY_ADJUSTED',
                'symbol': symbol,
                'apikey': API_KEYS['ALPHA_VANTAGE'],
                'outputsize': 'full'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'Time Series (Daily)' in data:
                        df = pd.DataFrame.from_dict(
                            data['Time Series (Daily)'], 
                            orient='index'
                        )
                        
                        # Convert to standard format
                        df.index = pd.to_datetime(df.index)
                        df = df.astype(float)
                        df.columns = ['open', 'high', 'low', 'close', 'adjusted_close', 'volume', 'dividend', 'split']
                        df = df[['open', 'high', 'low', 'close', 'volume']]
                        df = df.sort_index()
                        
                        return df
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Alpha Vantage fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_polygon_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data from Polygon API"""
        if not self.session or not API_KEYS.get('POLYGON'):
            return None
        
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
            params = {
                'apikey': API_KEYS['POLYGON'],
                'adjusted': 'true',
                'sort': 'asc'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and data['results']:
                        df_data = []
                        for result in data['results']:
                            df_data.append({
                                'timestamp': pd.to_datetime(result['t'], unit='ms'),
                                'open': result['o'],
                                'high': result['h'],
                                'low': result['l'],
                                'close': result['c'],
                                'volume': result['v']
                            })
                        
                        df = pd.DataFrame(df_data)
                        df.set_index('timestamp', inplace=True)
                        return df
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Polygon fetch failed for {symbol}: {e}")
            return None
    
    async def fetch_multiple_symbols(self, symbols: List[str], **kwargs) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols concurrently"""
        try:
            # Create tasks for concurrent execution
            tasks = []
            for symbol in symbols:
                task = self.fetch_historical_data(symbol, **kwargs)
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            symbol_data = {}
            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Failed to fetch data for {symbol}: {result}")
                    continue
                
                if result is not None:
                    symbol_data[symbol] = result
            
            return symbol_data
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.DATA_ERROR, ErrorSeverity.HIGH,
                context={'symbols': symbols}
            )
            return {}
    
    def start_real_time_feed(self, symbols: List[str]):
        """Start real-time data feed using WebSocket"""
        try:
            for symbol in symbols:
                self._start_websocket_connection(symbol)
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM,
                context={'symbols': symbols}
            )
    
    def _start_websocket_connection(self, symbol: str):
        """Start WebSocket connection for a symbol"""
        try:
            # This is a placeholder for WebSocket implementation
            # In practice, you would connect to your broker's WebSocket feed
            # or a financial data provider's real-time feed
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    # Process real-time data
                    if 'price' in data and 'symbol' in data:
                        market_data = MarketData(
                            symbol=data['symbol'],
                            timestamp=datetime.now(),
                            open=data.get('open', 0),
                            high=data.get('high', 0),
                            low=data.get('low', 0),
                            close=data.get('price', 0),
                            volume=data.get('volume', 0),
                            bid=data.get('bid', 0),
                            ask=data.get('ask', 0),
                            last_trade_price=data.get('price', 0),
                            last_trade_size=data.get('size', 0)
                        )
                        
                        self.real_time_data[symbol] = market_data
                        self.data_queue.put(market_data)
                        
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
            
            def on_error(ws, error):
                self.logger.error(f"WebSocket error for {symbol}: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                self.logger.info(f"WebSocket closed for {symbol}")
            
            # Placeholder WebSocket URL - replace with actual provider
            ws_url = f"wss://ws.example.com/v1/quotes?symbols={symbol}"
            
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            self.ws_connections[symbol] = ws
            
            # Start WebSocket in a separate thread
            def run_websocket():
                ws.run_forever()
            
            ws_thread = threading.Thread(target=run_websocket, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM,
                context={'symbol': symbol}
            )
    
    def get_real_time_data(self, symbol: str) -> Optional[MarketData]:
        """Get latest real-time data for a symbol"""
        return self.real_time_data.get(symbol)
    
    def get_all_real_time_data(self) -> Dict[str, MarketData]:
        """Get all real-time data"""
        return self.real_time_data.copy()
    
    def stop_real_time_feed(self):
        """Stop all real-time data feeds"""
        try:
            for symbol, ws in self.ws_connections.items():
                ws.close()
            self.ws_connections.clear()
            self.real_time_data.clear()
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.NETWORK_ERROR, ErrorSeverity.LOW
            )
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for symbols (sync method for quick access)"""
        try:
            prices = {}
            
            # First try real-time data
            for symbol in symbols:
                rt_data = self.get_real_time_data(symbol)
                if rt_data:
                    prices[symbol] = rt_data.close
                    continue
                
                # Fall back to cached data
                cached_data = self.get_cached_data(symbol, "1d")
                if cached_data is not None and not cached_data.empty:
                    prices[symbol] = float(cached_data['close'].iloc[-1])
                    continue
                
                # Last resort: fetch current price
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    current_price = info.get('regularMarketPrice') or info.get('currentPrice')
                    if current_price:
                        prices[symbol] = float(current_price)
                except:
                    pass
            
            return prices
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.DATA_ERROR, ErrorSeverity.MEDIUM,
                context={'symbols': symbols}
            )
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get data fetcher performance metrics"""
        try:
            if self.request_times:
                avg_request_time = np.mean(self.request_times)
                min_request_time = np.min(self.request_times)
                max_request_time = np.max(self.request_times)
            else:
                avg_request_time = min_request_time = max_request_time = 0.0
            
            success_rate = ((self.total_requests - self.failed_requests) / 
                          self.total_requests if self.total_requests > 0 else 0.0)
            
            return {
                'total_requests': self.total_requests,
                'failed_requests': self.failed_requests,
                'success_rate': success_rate,
                'avg_request_time': avg_request_time,
                'min_request_time': min_request_time,
                'max_request_time': max_request_time,
                'cache_entries': len(self.cache),
                'real_time_symbols': len(self.real_time_data)
            }
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
            return {}
    
    def clear_cache(self, older_than_hours: int = 24):
        """Clear old cached data"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            keys_to_remove = []
            for key, cached_data in self.cache.items():
                if cached_data.last_updated < cutoff_time:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
            
            self.logger.info(f"Cleared {len(keys_to_remove)} cached entries older than {older_than_hours} hours")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
    
    async def validate_symbols(self, symbols: List[str]) -> List[str]:
        """Validate that symbols exist and are tradeable"""
        valid_symbols = []
        
        try:
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    # Check if symbol has basic required info
                    if info and info.get('regularMarketPrice') and info.get('marketCap'):
                        valid_symbols.append(symbol)
                    else:
                        self.logger.warning(f"Symbol {symbol} appears invalid or untradeable")
                        
                except Exception as e:
                    self.logger.warning(f"Could not validate symbol {symbol}: {e}")
                    continue
            
            return valid_symbols
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.VALIDATION_ERROR, ErrorSeverity.MEDIUM,
                context={'symbols': symbols}
            )
            return symbols  # Return original list if validation fails


# Global data fetcher instance
data_fetcher = DataFetcher()