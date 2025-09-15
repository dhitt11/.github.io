"""
Backtesting Engine for Aura Trading Agent
Validates strategies using historical market data
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json

from config import CONFIG, DEFAULT_WATCHLIST
from data.data_fetcher import data_fetcher
from ml_models.ensemble_predictor import ensemble_predictor, PredictionSignal
from risk_management.portfolio_manager import PortfolioManager, PositionType
from indicators.technical_indicators import TechnicalIndicators
from core.error_handler import error_handler, ErrorCategory, ErrorSeverity


@dataclass
class BacktestResults:
    """Backtesting results summary"""
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    best_trade: float
    worst_trade: float
    avg_win: float
    avg_loss: float
    consecutive_wins: int
    consecutive_losses: int
    success_rate_target_met: bool


@dataclass
class TradeResult:
    """Individual trade result"""
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    position_type: str
    quantity: float
    pnl: float
    pnl_pct: float
    duration_days: int
    exit_reason: str


class BacktestEngine:
    """Backtesting engine for strategy validation"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.logger = logging.getLogger(__name__)
        
        # Results storage
        self.trade_results: List[TradeResult] = []
        self.daily_portfolio_values: List[float] = []
        self.daily_returns: List[float] = []
        self.equity_curve: pd.Series = pd.Series()
        
    async def run_backtest(self, 
                          start_date: str, 
                          end_date: str, 
                          symbols: List[str] = None,
                          initial_training_period: int = 252) -> BacktestResults:
        """
        Run comprehensive backtest
        
        Args:
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            symbols: List of symbols to trade (default: DEFAULT_WATCHLIST)
            initial_training_period: Days of data for initial model training
        """
        try:
            self.logger.info(f"Starting backtest from {start_date} to {end_date}")
            
            if symbols is None:
                symbols = DEFAULT_WATCHLIST[:10]  # Limit for faster backtesting
            
            # Initialize portfolio manager
            portfolio = PortfolioManager(self.initial_capital)
            
            # Fetch historical data
            self.logger.info("Fetching historical data...")
            all_data = await self._fetch_backtest_data(symbols, start_date, end_date, initial_training_period)
            
            if not all_data:
                raise ValueError("Could not fetch sufficient historical data")
            
            # Get date range for backtesting
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # Initial model training
            self.logger.info("Training initial models...")
            await self._train_initial_models(all_data, start_dt, initial_training_period)
            
            # Run day-by-day simulation
            self.logger.info("Running day-by-day simulation...")
            current_date = start_dt
            trading_days = 0
            
            while current_date <= end_dt:
                if current_date.weekday() < 5:  # Monday to Friday
                    await self._simulate_trading_day(current_date, all_data, portfolio, symbols)
                    trading_days += 1
                    
                    if trading_days % 50 == 0:
                        self.logger.info(f"Processed {trading_days} trading days...")
                
                current_date += timedelta(days=1)
            
            # Calculate final results
            results = self._calculate_backtest_results(portfolio, start_date, end_date)
            
            self.logger.info("Backtest completed successfully")
            self._log_backtest_summary(results)
            
            return results
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH,
                context={'start_date': start_date, 'end_date': end_date}
            )
            raise
    
    async def _fetch_backtest_data(self, 
                                  symbols: List[str], 
                                  start_date: str, 
                                  end_date: str,
                                  extra_days: int) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for backtesting"""
        try:
            # Extend start date to include training data
            extended_start = (pd.to_datetime(start_date) - timedelta(days=extra_days)).strftime('%Y-%m-%d')
            
            # Fetch data for all symbols
            async with data_fetcher:
                all_data = await data_fetcher.fetch_multiple_symbols(
                    symbols,
                    # Use custom date range instead of period
                    period="5y",  # Fallback to period-based fetching
                    interval="1d"
                )
            
            # Filter data to required date range and validate
            filtered_data = {}
            for symbol, data in all_data.items():
                if data is not None and len(data) > extra_days:
                    # Ensure we have enough data
                    filtered_data[symbol] = data
                    self.logger.debug(f"Loaded {len(data)} days of data for {symbol}")
            
            return filtered_data
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.DATA_ERROR, ErrorSeverity.HIGH,
                context={'symbols': symbols}
            )
            return {}
    
    async def _train_initial_models(self, 
                                   all_data: Dict[str, pd.DataFrame], 
                                   start_date: pd.Timestamp,
                                   training_days: int):
        """Train initial models with historical data"""
        try:
            # Combine training data from all symbols
            training_data = []
            
            for symbol, data in all_data.items():
                # Get training period data (before backtest start)
                training_end = start_date - timedelta(days=1)
                training_start = training_end - timedelta(days=training_days)
                
                symbol_training_data = data[
                    (data.index >= training_start) & (data.index <= training_end)
                ].copy()
                
                if len(symbol_training_data) > 50:  # Minimum data requirement
                    symbol_training_data['symbol'] = symbol
                    training_data.append(symbol_training_data)
            
            if training_data:
                combined_training = pd.concat(training_data, ignore_index=True)
                training_results = ensemble_predictor.train_all_models(combined_training)
                
                trained_models = sum(training_results.values())
                self.logger.info(f"Successfully trained {trained_models} models")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH
            )
    
    async def _simulate_trading_day(self, 
                                   current_date: pd.Timestamp,
                                   all_data: Dict[str, pd.DataFrame],
                                   portfolio: PortfolioManager,
                                   symbols: List[str]):
        """Simulate one trading day"""
        try:
            # Get current prices for all symbols
            current_prices = {}
            for symbol in symbols:
                if symbol in all_data:
                    data = all_data[symbol]
                    
                    # Find closest date
                    available_dates = data.index[data.index <= current_date]
                    if len(available_dates) > 0:
                        closest_date = available_dates[-1]
                        current_prices[symbol] = float(data.loc[closest_date, 'close'])
            
            # Update existing positions
            portfolio.update_positions(current_prices)
            
            # Check for new trading opportunities
            for symbol in symbols:
                await self._evaluate_symbol_for_trading(
                    symbol, current_date, all_data, portfolio, current_prices
                )
            
            # Record daily portfolio value
            portfolio_value = portfolio.get_portfolio_value()
            self.daily_portfolio_values.append(portfolio_value)
            
            # Calculate daily return
            if len(self.daily_portfolio_values) > 1:
                daily_return = (portfolio_value - self.daily_portfolio_values[-2]) / self.daily_portfolio_values[-2]
                self.daily_returns.append(daily_return)
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.MEDIUM,
                context={'date': current_date.strftime('%Y-%m-%d')}
            )
    
    async def _evaluate_symbol_for_trading(self,
                                          symbol: str,
                                          current_date: pd.Timestamp,
                                          all_data: Dict[str, pd.DataFrame],
                                          portfolio: PortfolioManager,
                                          current_prices: Dict[str, float]):
        """Evaluate a symbol for trading opportunities"""
        try:
            # Skip if we already have a position
            if symbol in portfolio.positions:
                return
            
            # Skip if no price data available
            if symbol not in current_prices or symbol not in all_data:
                return
            
            # Get historical data up to current date
            data = all_data[symbol]
            historical_data = data[data.index <= current_date].copy()
            
            if len(historical_data) < 60:  # Need minimum data for analysis
                return
            
            # Get recent data for prediction (last 60 days)
            recent_data = historical_data.tail(60)
            
            # Get ML prediction
            if ensemble_predictor.is_trained:
                try:
                    prediction = ensemble_predictor.predict(recent_data)
                except:
                    return  # Skip if prediction fails
            else:
                return
            
            # Get technical analysis
            indicators = TechnicalIndicators.calculate_all_indicators(recent_data)
            if len(indicators) == 0:
                return
                
            signal_strength = TechnicalIndicators.get_signal_strength(indicators).iloc[-1]
            
            # Combine signals
            combined_confidence = (prediction.confidence + abs(signal_strength)) / 2
            
            # Determine trade direction
            if (prediction.signal in [PredictionSignal.BUY, PredictionSignal.STRONG_BUY] 
                and signal_strength > 0.3):
                trade_direction = PositionType.LONG
            elif (prediction.signal in [PredictionSignal.SELL, PredictionSignal.STRONG_SELL] 
                  and signal_strength < -0.3):
                trade_direction = PositionType.SHORT
            else:
                return  # No clear signal
            
            # Check signal strength threshold
            if combined_confidence < 0.6:  # Minimum confidence threshold
                return
            
            # Check position limits
            if len(portfolio.positions) >= 8:  # Maximum positions for backtest
                return
            
            # Calculate ATR for position sizing
            atr = indicators['atr'].iloc[-1] if 'atr' in indicators else None
            current_price = current_prices[symbol]
            
            # Attempt to open position
            success = portfolio.open_position(
                symbol=symbol,
                position_type=trade_direction,
                entry_price=current_price,
                atr=atr
            )
            
            if success:
                self.logger.debug(
                    f"Opened {trade_direction.value} position: {symbol} "
                    f"@ ${current_price:.2f} on {current_date.strftime('%Y-%m-%d')}"
                )
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.LOW,
                context={'symbol': symbol, 'date': current_date.strftime('%Y-%m-%d')}
            )
    
    def _calculate_backtest_results(self, 
                                   portfolio: PortfolioManager, 
                                   start_date: str, 
                                   end_date: str) -> BacktestResults:
        """Calculate comprehensive backtest results"""
        try:
            final_capital = portfolio.get_portfolio_value()
            total_return = (final_capital - self.initial_capital) / self.initial_capital
            
            # Calculate date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            trading_days = len(self.daily_portfolio_values)
            years = (end_dt - start_dt).days / 365.25
            
            # Annualized return
            annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
            
            # Create equity curve
            dates = pd.date_range(start=start_date, periods=trading_days, freq='D')
            self.equity_curve = pd.Series(self.daily_portfolio_values, index=dates[:len(self.daily_portfolio_values)])
            
            # Calculate drawdown
            peak = self.equity_curve.expanding().max()
            drawdown = (self.equity_curve - peak) / peak
            max_drawdown = drawdown.min()
            
            # Calculate Sharpe ratio
            if len(self.daily_returns) > 1:
                excess_returns = np.array(self.daily_returns)
                sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0
                
                # Sortino ratio (using downside deviation)
                downside_returns = excess_returns[excess_returns < 0]
                downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.std(excess_returns)
                sortino_ratio = np.mean(excess_returns) / downside_std * np.sqrt(252) if downside_std > 0 else 0
            else:
                sharpe_ratio = sortino_ratio = 0
            
            # Analyze closed trades
            closed_trades = portfolio.closed_positions
            total_trades = len(closed_trades)
            
            if total_trades > 0:
                winning_trades = [t for t in closed_trades if t.unrealized_pnl > 0]
                losing_trades = [t for t in closed_trades if t.unrealized_pnl <= 0]
                
                win_rate = len(winning_trades) / total_trades
                avg_win = np.mean([t.unrealized_pnl for t in winning_trades]) if winning_trades else 0
                avg_loss = np.mean([abs(t.unrealized_pnl) for t in losing_trades]) if losing_trades else 0
                
                profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) if avg_loss > 0 and losing_trades else 0
                
                best_trade = max([t.unrealized_pnl for t in closed_trades]) if closed_trades else 0
                worst_trade = min([t.unrealized_pnl for t in closed_trades]) if closed_trades else 0
                
                # Calculate consecutive wins/losses
                consecutive_wins = consecutive_losses = 0
                max_consecutive_wins = max_consecutive_losses = 0
                current_streak = 0
                last_was_win = None
                
                for trade in closed_trades:
                    is_win = trade.unrealized_pnl > 0
                    if last_was_win is None or last_was_win == is_win:
                        current_streak += 1
                    else:
                        if last_was_win:
                            max_consecutive_wins = max(max_consecutive_wins, current_streak)
                        else:
                            max_consecutive_losses = max(max_consecutive_losses, current_streak)
                        current_streak = 1
                    last_was_win = is_win
                
                # Handle final streak
                if last_was_win:
                    max_consecutive_wins = max(max_consecutive_wins, current_streak)
                else:
                    max_consecutive_losses = max(max_consecutive_losses, current_streak)
                
                consecutive_wins = max_consecutive_wins
                consecutive_losses = max_consecutive_losses
                
                # Calculate average trade duration
                durations = []
                for trade in closed_trades:
                    if hasattr(trade, 'entry_time'):
                        # This would need to be calculated during simulation
                        durations.append(1)  # Placeholder
                avg_trade_duration = np.mean(durations) if durations else 0
                
            else:
                win_rate = avg_win = avg_loss = profit_factor = 0
                best_trade = worst_trade = 0
                consecutive_wins = consecutive_losses = 0
                avg_trade_duration = 0
            
            # Check if success rate target is met
            success_rate_target_met = win_rate >= CONFIG.TARGET_SUCCESS_RATE
            
            return BacktestResults(
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=final_capital,
                total_return=total_return,
                annualized_return=annualized_return,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=total_trades,
                avg_trade_duration=avg_trade_duration,
                best_trade=best_trade,
                worst_trade=worst_trade,
                avg_win=avg_win,
                avg_loss=avg_loss,
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses,
                success_rate_target_met=success_rate_target_met
            )
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH
            )
            # Return minimal results on error
            return BacktestResults(
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_return=0.0,
                annualized_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                avg_trade_duration=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                consecutive_wins=0,
                consecutive_losses=0,
                success_rate_target_met=False
            )
    
    def _log_backtest_summary(self, results: BacktestResults):
        """Log backtest summary"""
        self.logger.info("=== BACKTEST RESULTS ===")
        self.logger.info(f"Period: {results.start_date} to {results.end_date}")
        self.logger.info(f"Initial Capital: ${results.initial_capital:,.2f}")
        self.logger.info(f"Final Capital: ${results.final_capital:,.2f}")
        self.logger.info(f"Total Return: {results.total_return:.2%}")
        self.logger.info(f"Annualized Return: {results.annualized_return:.2%}")
        self.logger.info(f"Max Drawdown: {results.max_drawdown:.2%}")
        self.logger.info(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
        self.logger.info(f"Win Rate: {results.win_rate:.2%}")
        self.logger.info(f"Total Trades: {results.total_trades}")
        self.logger.info(f"Profit Factor: {results.profit_factor:.2f}")
        self.logger.info(f"80% Success Target Met: {results.success_rate_target_met}")
    
    def plot_results(self, results: BacktestResults, save_path: str = None):
        """Plot backtest results"""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Backtest Results', fontsize=16)
            
            # Equity curve
            axes[0, 0].plot(self.equity_curve.index, self.equity_curve.values)
            axes[0, 0].set_title('Equity Curve')
            axes[0, 0].set_ylabel('Portfolio Value ($)')
            axes[0, 0].grid(True)
            
            # Drawdown
            if len(self.equity_curve) > 0:
                peak = self.equity_curve.expanding().max()
                drawdown = (self.equity_curve - peak) / peak * 100
                axes[0, 1].fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
                axes[0, 1].plot(drawdown.index, drawdown.values, color='red')
                axes[0, 1].set_title('Drawdown')
                axes[0, 1].set_ylabel('Drawdown (%)')
                axes[0, 1].grid(True)
            
            # Daily returns histogram
            if len(self.daily_returns) > 0:
                axes[1, 0].hist(self.daily_returns, bins=50, alpha=0.7)
                axes[1, 0].set_title('Daily Returns Distribution')
                axes[1, 0].set_xlabel('Daily Return')
                axes[1, 0].set_ylabel('Frequency')
                axes[1, 0].grid(True)
            
            # Performance metrics
            metrics_text = f"""
            Total Return: {results.total_return:.2%}
            Annualized Return: {results.annualized_return:.2%}
            Max Drawdown: {results.max_drawdown:.2%}
            Sharpe Ratio: {results.sharpe_ratio:.2f}
            Win Rate: {results.win_rate:.2%}
            Total Trades: {results.total_trades}
            Profit Factor: {results.profit_factor:.2f}
            Target Met: {results.success_rate_target_met}
            """
            
            axes[1, 1].text(0.1, 0.5, metrics_text, transform=axes[1, 1].transAxes, 
                           fontsize=10, verticalalignment='center')
            axes[1, 1].set_title('Performance Metrics')
            axes[1, 1].axis('off')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"Backtest plots saved to {save_path}")
            
            plt.show()
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
    
    def export_results(self, results: BacktestResults, filepath: str):
        """Export backtest results to JSON"""
        try:
            results_dict = asdict(results)
            
            # Add additional data
            results_dict['daily_returns'] = self.daily_returns
            results_dict['equity_curve'] = self.equity_curve.to_dict() if len(self.equity_curve) > 0 else {}
            
            with open(filepath, 'w') as f:
                json.dump(results_dict, f, indent=2, default=str)
            
            self.logger.info(f"Backtest results exported to {filepath}")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM,
                context={'filepath': filepath}
            )


async def main():
    """Main function for running backtest"""
    logging.basicConfig(level=logging.INFO)
    
    # Create backtest engine
    engine = BacktestEngine(initial_capital=100000.0)
    
    # Run backtest for last 2 years
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    try:
        results = await engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            symbols=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META']
        )
        
        # Plot and export results
        engine.plot_results(results, 'backtest_results.png')
        engine.export_results(results, 'backtest_results.json')
        
        print(f"\nBacktest completed!")
        print(f"Success rate target (80%) met: {results.success_rate_target_met}")
        print(f"Actual win rate: {results.win_rate:.2%}")
        
    except Exception as e:
        print(f"Backtest failed: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())