"""
Main Aura Trading Agent
Orchestrates all components for automated trading with 80% success rate target
"""
import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import colorlog
import signal
import sys
import json

from config import CONFIG, DEFAULT_WATCHLIST, MARKET_HOURS, SAFETY_LIMITS
from core.error_handler import error_handler, ErrorCategory, ErrorSeverity
from data.data_fetcher import data_fetcher
from ml_models.ensemble_predictor import ensemble_predictor, PredictionSignal
from risk_management.portfolio_manager import PortfolioManager, PositionType
from indicators.technical_indicators import TechnicalIndicators


class AuraTradingAgent:
    """Main Trading Agent orchestrating all components"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.portfolio_manager = PortfolioManager(initial_capital)
        self.watchlist = DEFAULT_WATCHLIST.copy()
        self.is_running = False
        self.is_market_hours = False
        
        # Performance tracking
        self.daily_stats = {
            'trades_executed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl': 0.0,
            'start_portfolio_value': initial_capital
        }
        
        # Strategy parameters
        self.min_signal_strength = 0.6  # Minimum confidence for trade execution
        self.max_positions = 10  # Maximum concurrent positions
        
        self.logger.info("Aura Trading Agent initialized")
        self.logger.info(f"Initial capital: ${initial_capital:,.2f}")
        self.logger.info(f"Watchlist: {', '.join(self.watchlist)}")
    
    def setup_logging(self):
        """Setup enhanced logging with colors"""
        # Create formatter
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Setup file handler
        file_handler = logging.FileHandler(CONFIG.LOG_FILE)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Configure root logger
        logging.getLogger().setLevel(getattr(logging, CONFIG.LOG_LEVEL))
        logging.getLogger().addHandler(console_handler)
        logging.getLogger().addHandler(file_handler)
    
    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("Initializing Aura Trading Agent...")
            
            # Initialize data fetcher
            await data_fetcher.__aenter__()
            
            # Validate watchlist symbols
            self.logger.info("Validating watchlist symbols...")
            valid_symbols = await data_fetcher.validate_symbols(self.watchlist)
            if len(valid_symbols) < len(self.watchlist):
                removed_symbols = set(self.watchlist) - set(valid_symbols)
                self.logger.warning(f"Removed invalid symbols: {removed_symbols}")
                self.watchlist = valid_symbols
            
            # Fetch initial data for training
            self.logger.info("Fetching initial market data...")
            market_data = await data_fetcher.fetch_multiple_symbols(
                self.watchlist,
                period="2y",  # 2 years of data for training
                interval="1d"
            )
            
            if not market_data:
                raise ValueError("Could not fetch market data for any symbols")
            
            # Train ML models
            self.logger.info("Training machine learning models...")
            await self.train_models(market_data)
            
            # Start real-time data feeds
            self.logger.info("Starting real-time data feeds...")
            data_fetcher.start_real_time_feed(self.watchlist)
            
            # Schedule tasks
            self.schedule_tasks()
            
            self.logger.info("Aura Trading Agent fully initialized and ready to trade!")
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.CRITICAL,
                context={'method': 'initialize'}
            )
            return False
    
    async def train_models(self, market_data: Dict[str, pd.DataFrame]):
        """Train ensemble models with market data"""
        try:
            # Combine data from multiple symbols for training
            combined_data = []
            
            for symbol, data in market_data.items():
                if data is not None and len(data) > 100:  # Minimum data requirement
                    # Add symbol identifier
                    data_copy = data.copy()
                    data_copy['symbol'] = symbol
                    combined_data.append(data_copy)
            
            if not combined_data:
                raise ValueError("Insufficient data for model training")
            
            # Concatenate all data
            training_data = pd.concat(combined_data, ignore_index=True)
            
            # Train ensemble models
            training_results = ensemble_predictor.train_all_models(training_data)
            
            # Log training results
            for model_name, success in training_results.items():
                status = "SUCCESS" if success else "FAILED"
                self.logger.info(f"Model training - {model_name}: {status}")
            
            # Get performance summary
            performance_summary = ensemble_predictor.get_model_performance_summary()
            for model_name, metrics in performance_summary.items():
                if metrics['trained']:
                    self.logger.info(
                        f"{model_name}: Accuracy={metrics['accuracy']:.3f}, "
                        f"Weight={metrics['weight']:.3f}"
                    )
            
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH,
                context={'method': 'train_models'}
            )
            return False
    
    def schedule_tasks(self):
        """Schedule recurring tasks"""
        # Market open tasks
        schedule.every().day.at("09:25").do(self.prepare_for_market_open)
        
        # Market close tasks
        schedule.every().day.at("16:05").do(self.market_close_tasks)
        
        # Periodic tasks during market hours
        schedule.every(5).minutes.do(self.periodic_analysis)
        
        # Daily maintenance tasks
        schedule.every().day.at("18:00").do(self.daily_maintenance)
        
        # Weekly model retraining
        schedule.every().sunday.at("20:00").do(self.weekly_model_retrain)
    
    async def run(self):
        """Main trading loop"""
        self.is_running = True
        self.logger.info("Starting main trading loop...")
        
        try:
            while self.is_running:
                try:
                    # Run scheduled tasks
                    schedule.run_pending()
                    
                    # Check if we're in market hours
                    self.is_market_hours = self.check_market_hours()
                    
                    if self.is_market_hours:
                        # Execute main trading logic
                        await self.execute_trading_cycle()
                    else:
                        # Sleep longer when market is closed
                        await asyncio.sleep(60)
                        continue
                    
                    # Short sleep between cycles
                    await asyncio.sleep(CONFIG.REFRESH_INTERVAL)
                    
                except KeyboardInterrupt:
                    self.logger.info("Received interrupt signal, shutting down...")
                    break
                    
                except Exception as e:
                    error_handler.handle_error(
                        e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH,
                        context={'method': 'run'}
                    )
                    await asyncio.sleep(30)  # Wait before retrying
                    
        finally:
            await self.shutdown()
    
    async def execute_trading_cycle(self):
        """Execute one complete trading cycle"""
        try:
            # Update portfolio with current market prices
            current_prices = data_fetcher.get_latest_prices(self.watchlist)
            if current_prices:
                self.portfolio_manager.update_positions(current_prices)
            
            # Check risk limits
            risk_status = self.portfolio_manager.check_risk_limits()
            if not all(risk_status.values()):
                self.logger.warning(f"Risk limit violations detected: {risk_status}")
                return
            
            # Analyze each symbol for trading opportunities
            for symbol in self.watchlist:
                await self.analyze_symbol(symbol)
            
            # Log portfolio status
            self.log_portfolio_status()
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.MEDIUM,
                context={'method': 'execute_trading_cycle'}
            )
    
    async def analyze_symbol(self, symbol: str):
        """Analyze a single symbol for trading opportunities"""
        try:
            # Skip if we already have a position
            if symbol in self.portfolio_manager.positions:
                return
            
            # Get recent data for analysis
            data = await data_fetcher.fetch_historical_data(symbol, period="3mo", interval="1d")
            if data is None or len(data) < 50:
                return
            
            # Get ML prediction
            prediction = ensemble_predictor.predict(data)
            
            # Get technical analysis
            indicators = TechnicalIndicators.calculate_all_indicators(data)
            signal_strength = TechnicalIndicators.get_signal_strength(indicators).iloc[-1]
            
            # Combine ML and technical signals
            combined_confidence = (prediction.confidence + abs(signal_strength)) / 2
            
            # Determine trade direction
            if prediction.signal in [PredictionSignal.BUY, PredictionSignal.STRONG_BUY] and signal_strength > 0:
                trade_direction = PositionType.LONG
            elif prediction.signal in [PredictionSignal.SELL, PredictionSignal.STRONG_SELL] and signal_strength < 0:
                trade_direction = PositionType.SHORT
            else:
                return  # No clear signal
            
            # Check if signal is strong enough
            if combined_confidence < self.min_signal_strength:
                return
            
            # Check position limits
            if len(self.portfolio_manager.positions) >= self.max_positions:
                return
            
            # Get current price and ATR for position sizing
            current_price = current_prices.get(symbol)
            if not current_price:
                real_time_data = data_fetcher.get_real_time_data(symbol)
                current_price = real_time_data.close if real_time_data else data['close'].iloc[-1]
            
            atr = indicators['atr'].iloc[-1] if 'atr' in indicators else None
            
            # Execute trade
            success = self.portfolio_manager.open_position(
                symbol=symbol,
                position_type=trade_direction,
                entry_price=current_price,
                atr=atr
            )
            
            if success:
                self.daily_stats['trades_executed'] += 1
                self.logger.info(
                    f"Opened {trade_direction.value} position for {symbol} "
                    f"@ ${current_price:.2f} (Confidence: {combined_confidence:.2f})"
                )
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.MEDIUM,
                context={'symbol': symbol}
            )
    
    def check_market_hours(self) -> bool:
        """Check if market is currently open"""
        try:
            now = datetime.now()
            
            # Simple market hours check (US Eastern Time)
            # In production, use proper timezone handling
            if now.weekday() >= 5:  # Weekend
                return False
            
            current_time = now.time()
            market_open = datetime.strptime(MARKET_HOURS.MARKET_OPEN, "%H:%M").time()
            market_close = datetime.strptime(MARKET_HOURS.MARKET_CLOSE, "%H:%M").time()
            
            return market_open <= current_time <= market_close
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
            return False
    
    def prepare_for_market_open(self):
        """Tasks to run before market opens"""
        try:
            self.logger.info("Preparing for market open...")
            
            # Reset daily counters
            self.portfolio_manager.reset_daily_counters()
            self.daily_stats = {
                'trades_executed': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'total_pnl': 0.0,
                'start_portfolio_value': self.portfolio_manager.get_portfolio_value()
            }
            
            # Clear old cache
            data_fetcher.clear_cache(older_than_hours=12)
            
            # Pre-fetch data for all watchlist symbols
            asyncio.create_task(self.prefetch_market_data())
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM
            )
    
    async def prefetch_market_data(self):
        """Pre-fetch market data for all symbols"""
        try:
            await data_fetcher.fetch_multiple_symbols(
                self.watchlist,
                period="1mo",
                interval="1d",
                force_refresh=True
            )
            self.logger.info("Market data pre-fetched successfully")
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.DATA_ERROR, ErrorSeverity.MEDIUM
            )
    
    def market_close_tasks(self):
        """Tasks to run after market closes"""
        try:
            self.logger.info("Running market close tasks...")
            
            # Calculate daily performance
            metrics = self.portfolio_manager.get_portfolio_metrics()
            
            # Update daily stats
            closed_positions_today = [
                pos for pos in self.portfolio_manager.closed_positions
                if pos.entry_time.date() == datetime.now().date()
            ]
            
            successful_trades = len([pos for pos in closed_positions_today if pos.unrealized_pnl > 0])
            failed_trades = len([pos for pos in closed_positions_today if pos.unrealized_pnl <= 0])
            
            success_rate = successful_trades / (successful_trades + failed_trades) if (successful_trades + failed_trades) > 0 else 0
            
            # Log daily summary
            self.logger.info("=== DAILY TRADING SUMMARY ===")
            self.logger.info(f"Portfolio Value: ${metrics.total_value:,.2f}")
            self.logger.info(f"Daily P&L: ${metrics.daily_pnl:,.2f}")
            self.logger.info(f"Trades Executed: {metrics.trades_today}")
            self.logger.info(f"Success Rate: {success_rate:.1%}")
            self.logger.info(f"Win Rate (Overall): {metrics.win_rate:.1%}")
            self.logger.info(f"Open Positions: {len(self.portfolio_manager.positions)}")
            
            # Save performance data
            self.save_daily_performance(metrics, success_rate)
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM
            )
    
    def periodic_analysis(self):
        """Periodic analysis tasks during market hours"""
        if not self.is_market_hours:
            return
        
        try:
            # Check system health
            performance_metrics = data_fetcher.get_performance_metrics()
            if performance_metrics.get('success_rate', 1.0) < 0.8:
                self.logger.warning("Data fetcher success rate below 80%")
            
            # Check for any critical errors
            error_summary = error_handler.get_error_summary()
            if error_summary.get('circuit_breaker_triggered', False):
                self.logger.critical("Trading circuit breaker is active!")
                
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
    
    def daily_maintenance(self):
        """Daily maintenance tasks"""
        try:
            self.logger.info("Running daily maintenance...")
            
            # Export error history
            error_handler.export_error_history("logs/error_history.json")
            
            # Clean up old log files (keep last 30 days)
            # Implementation would go here
            
            # Backup portfolio state
            portfolio_summary = self.portfolio_manager.get_position_summary()
            with open("logs/portfolio_backup.json", "w") as f:
                json.dump(portfolio_summary, f, indent=2, default=str)
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
    
    def weekly_model_retrain(self):
        """Weekly model retraining"""
        try:
            self.logger.info("Starting weekly model retraining...")
            asyncio.create_task(self.retrain_models())
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM
            )
    
    async def retrain_models(self):
        """Retrain ML models with fresh data"""
        try:
            # Fetch fresh training data
            market_data = await data_fetcher.fetch_multiple_symbols(
                self.watchlist,
                period="1y",
                interval="1d",
                force_refresh=True
            )
            
            if market_data:
                await self.train_models(market_data)
                self.logger.info("Weekly model retraining completed")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM
            )
    
    def log_portfolio_status(self):
        """Log current portfolio status"""
        try:
            metrics = self.portfolio_manager.get_portfolio_metrics()
            
            if len(self.portfolio_manager.positions) > 0:
                positions_summary = []
                for symbol, position_info in self.portfolio_manager.get_position_summary().items():
                    pnl = position_info['unrealized_pnl']
                    pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
                    positions_summary.append(f"{symbol}({pnl_str})")
                
                self.logger.info(f"Positions: {', '.join(positions_summary)} | Total: ${metrics.total_value:,.2f}")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
    
    def save_daily_performance(self, metrics, success_rate: float):
        """Save daily performance metrics"""
        try:
            performance_data = {
                'date': datetime.now().isoformat(),
                'portfolio_value': metrics.total_value,
                'daily_pnl': metrics.daily_pnl,
                'trades_executed': metrics.trades_today,
                'success_rate': success_rate,
                'win_rate': metrics.win_rate,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown
            }
            
            # Append to performance log
            with open("logs/daily_performance.jsonl", "a") as f:
                f.write(json.dumps(performance_data) + "\n")
                
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
    
    async def shutdown(self):
        """Gracefully shutdown the trading agent"""
        try:
            self.logger.info("Shutting down Aura Trading Agent...")
            self.is_running = False
            
            # Close all positions if needed (implement position closure logic)
            
            # Stop real-time data feeds
            data_fetcher.stop_real_time_feed()
            
            # Close data fetcher session
            await data_fetcher.__aexit__(None, None, None)
            
            # Save final state
            self.save_daily_performance(self.portfolio_manager.get_portfolio_metrics(), 0.0)
            
            self.logger.info("Shutdown complete")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH
            )


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nReceived shutdown signal. Gracefully shutting down...")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and initialize trading agent
    agent = AuraTradingAgent(initial_capital=100000.0)
    
    try:
        # Initialize all components
        if await agent.initialize():
            # Start trading
            await agent.run()
        else:
            print("Failed to initialize trading agent")
            return 1
            
    except Exception as e:
        error_handler.handle_error(
            e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.CRITICAL
        )
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)