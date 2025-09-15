"""
Enhanced Portfolio Manager with dynamic risk management and trailing stop-loss
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from ..config import CONFIG, SAFETY_LIMITS
from ..core.error_handler import error_handler, ErrorCategory, ErrorSeverity


class PositionType(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    position_type: PositionType
    quantity: float
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    trailing_stop: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    risk_amount: float = 0.0
    
    def update_price(self, new_price: float):
        """Update current price and recalculate PnL"""
        self.current_price = new_price
        
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - new_price) * self.quantity
    
    def should_close_position(self) -> Tuple[bool, str]:
        """Check if position should be closed based on stop loss or take profit"""
        if self.position_type == PositionType.LONG:
            if self.current_price <= self.stop_loss:
                return True, "stop_loss"
            elif self.current_price >= self.take_profit:
                return True, "take_profit"
            elif self.current_price <= self.trailing_stop:
                return True, "trailing_stop"
        else:  # SHORT position
            if self.current_price >= self.stop_loss:
                return True, "stop_loss"
            elif self.current_price <= self.take_profit:
                return True, "take_profit"
            elif self.current_price >= self.trailing_stop:
                return True, "trailing_stop"
                
        return False, ""
    
    def update_trailing_stop(self):
        """Update trailing stop based on current price"""
        if self.position_type == PositionType.LONG:
            # For long positions, trailing stop moves up
            new_trailing_stop = self.current_price * (1 - CONFIG.TRAILING_STOP_PERCENT)
            self.trailing_stop = max(self.trailing_stop, new_trailing_stop)
        else:
            # For short positions, trailing stop moves down
            new_trailing_stop = self.current_price * (1 + CONFIG.TRAILING_STOP_PERCENT)
            self.trailing_stop = min(self.trailing_stop, new_trailing_stop)


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float = 0.0
    cash_balance: float = 0.0
    invested_amount: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    trades_today: int = 0
    daily_pnl: float = 0.0


class PortfolioManager:
    """Enhanced Portfolio Manager with dynamic risk management"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.daily_returns: List[float] = []
        self.equity_curve: List[float] = [initial_capital]
        self.trade_history: List[Dict] = []
        
        self.logger = logging.getLogger(__name__)
        
        # Risk management parameters
        self.max_position_size = CONFIG.MAX_POSITION_SIZE
        self.max_daily_loss = CONFIG.MAX_DAILY_LOSS
        self.max_correlation_exposure = CONFIG.MAX_CORRELATION_EXPOSURE
        
        # Market volatility tracking
        self.market_volatility = 0.02  # Default 2% daily volatility
        self.volatility_lookback = 20  # Days
        
        # Portfolio state
        self.daily_start_value = initial_capital
        self.daily_trades = 0
        self.circuit_breaker_active = False
        
    def calculate_position_size(self, 
                              symbol: str, 
                              entry_price: float, 
                              stop_loss: float, 
                              risk_per_trade: float = None) -> float:
        """
        Calculate optimal position size based on risk management
        """
        try:
            if risk_per_trade is None:
                risk_per_trade = self.max_position_size
                
            # Adjust for market volatility if enabled
            if CONFIG.VOLATILITY_SCALING:
                volatility_adjustment = min(0.02 / self.market_volatility, 2.0)
                risk_per_trade *= volatility_adjustment
            
            # Calculate risk amount
            portfolio_value = self.get_portfolio_value()
            risk_amount = portfolio_value * risk_per_trade
            
            # Calculate position size based on stop loss distance
            price_diff = abs(entry_price - stop_loss)
            if price_diff == 0:
                raise ValueError("Stop loss cannot equal entry price")
                
            position_size = risk_amount / price_diff
            
            # Apply additional constraints
            max_position_value = portfolio_value * 0.1  # Max 10% in single position
            max_shares_by_value = max_position_value / entry_price
            
            position_size = min(position_size, max_shares_by_value)
            
            # Ensure we have enough cash
            required_cash = position_size * entry_price
            if required_cash > self.cash_balance:
                position_size = self.cash_balance / entry_price * 0.95  # Leave 5% buffer
            
            return max(0, position_size)
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.MEDIUM,
                context={'symbol': symbol, 'entry_price': entry_price, 'stop_loss': stop_loss}
            )
            return 0
    
    def calculate_stop_loss_take_profit(self, 
                                      entry_price: float, 
                                      position_type: PositionType,
                                      atr: float = None) -> Tuple[float, float]:
        """
        Calculate dynamic stop loss and take profit levels
        """
        try:
            # Use ATR for dynamic levels if available
            if atr is not None:
                stop_distance = atr * 2  # 2 ATR stop loss
                profit_distance = stop_distance * CONFIG.MIN_RISK_REWARD_RATIO
            else:
                # Fallback to percentage-based levels
                stop_distance = entry_price * 0.02  # 2% stop loss
                profit_distance = stop_distance * CONFIG.MIN_RISK_REWARD_RATIO
            
            if position_type == PositionType.LONG:
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + profit_distance
            else:
                stop_loss = entry_price + stop_distance
                take_profit = entry_price - profit_distance
            
            return stop_loss, take_profit
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.LOW,
                context={'entry_price': entry_price, 'position_type': position_type.value}
            )
            # Return conservative defaults
            if position_type == PositionType.LONG:
                return entry_price * 0.98, entry_price * 1.06
            else:
                return entry_price * 1.02, entry_price * 0.94
    
    def open_position(self, 
                     symbol: str, 
                     position_type: PositionType, 
                     entry_price: float,
                     stop_loss: float = None,
                     take_profit: float = None,
                     atr: float = None) -> bool:
        """
        Open a new trading position with comprehensive risk checks
        """
        try:
            # Pre-trade validation
            if not self._validate_trade_conditions(symbol):
                return False
            
            # Calculate stop loss and take profit if not provided
            if stop_loss is None or take_profit is None:
                calc_stop, calc_tp = self.calculate_stop_loss_take_profit(
                    entry_price, position_type, atr
                )
                stop_loss = stop_loss or calc_stop
                take_profit = take_profit or calc_tp
            
            # Validate risk-reward ratio
            if not self._validate_risk_reward_ratio(entry_price, stop_loss, take_profit, position_type):
                self.logger.warning(f"Risk-reward ratio below minimum for {symbol}")
                return False
            
            # Calculate position size
            position_size = self.calculate_position_size(symbol, entry_price, stop_loss)
            
            if position_size <= 0:
                self.logger.warning(f"Invalid position size calculated for {symbol}")
                return False
            
            # Calculate required cash
            required_cash = position_size * entry_price
            
            if required_cash > self.cash_balance:
                self.logger.warning(f"Insufficient cash for {symbol} position")
                return False
            
            # Create position
            trailing_stop = stop_loss  # Initialize trailing stop at stop loss
            
            position = Position(
                symbol=symbol,
                position_type=position_type,
                quantity=position_size,
                entry_price=entry_price,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                current_price=entry_price,
                risk_amount=abs(entry_price - stop_loss) * position_size
            )
            
            # Add position to portfolio
            self.positions[symbol] = position
            self.cash_balance -= required_cash
            self.daily_trades += 1
            
            # Log the trade
            self._log_trade("OPEN", position)
            
            self.logger.info(
                f"Opened {position_type.value} position: {symbol} "
                f"@ ${entry_price:.2f}, Size: {position_size:.2f}, "
                f"Stop: ${stop_loss:.2f}, Target: ${take_profit:.2f}"
            )
            
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.HIGH,
                context={
                    'symbol': symbol, 
                    'position_type': position_type.value,
                    'entry_price': entry_price
                }
            )
            return False
    
    def close_position(self, symbol: str, close_price: float, reason: str = "manual") -> bool:
        """Close an existing position"""
        try:
            if symbol not in self.positions:
                self.logger.warning(f"No position found for {symbol}")
                return False
            
            position = self.positions[symbol]
            position.update_price(close_price)
            
            # Calculate realized PnL
            realized_pnl = position.unrealized_pnl
            
            # Add cash back to balance
            cash_received = position.quantity * close_price
            self.cash_balance += cash_received
            
            # Move to closed positions
            self.closed_positions.append(position)
            del self.positions[symbol]
            
            # Log the trade
            self._log_trade("CLOSE", position, reason, realized_pnl)
            
            self.logger.info(
                f"Closed {position.position_type.value} position: {symbol} "
                f"@ ${close_price:.2f}, PnL: ${realized_pnl:.2f}, Reason: {reason}"
            )
            
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.HIGH,
                context={'symbol': symbol, 'close_price': close_price, 'reason': reason}
            )
            return False
    
    def update_positions(self, market_data: Dict[str, float]):
        """Update all positions with current market prices"""
        try:
            positions_to_close = []
            
            for symbol, position in self.positions.items():
                if symbol in market_data:
                    current_price = market_data[symbol]
                    position.update_price(current_price)
                    
                    # Update trailing stop
                    position.update_trailing_stop()
                    
                    # Check if position should be closed
                    should_close, reason = position.should_close_position()
                    if should_close:
                        positions_to_close.append((symbol, current_price, reason))
            
            # Close positions that hit stops
            for symbol, price, reason in positions_to_close:
                self.close_position(symbol, price, reason)
                
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.TRADING_ERROR, ErrorSeverity.MEDIUM,
                context={'market_data_symbols': list(market_data.keys())}
            )
    
    def check_risk_limits(self) -> Dict[str, bool]:
        """Check various risk limits and return status"""
        risk_status = {}
        
        try:
            current_portfolio_value = self.get_portfolio_value()
            daily_pnl = current_portfolio_value - self.daily_start_value
            
            # Check daily loss limit
            daily_loss_pct = abs(daily_pnl) / self.daily_start_value
            risk_status['daily_loss_limit'] = daily_loss_pct < self.max_daily_loss
            
            # Check maximum drawdown
            max_equity = max(self.equity_curve)
            current_drawdown = (max_equity - current_portfolio_value) / max_equity
            risk_status['max_drawdown_limit'] = current_drawdown < SAFETY_LIMITS.MAX_DRAWDOWN_PERCENT
            
            # Check daily trade limit
            risk_status['daily_trade_limit'] = self.daily_trades < SAFETY_LIMITS.MAX_TRADES_PER_DAY
            
            # Check minimum account balance
            risk_status['min_balance'] = self.cash_balance > SAFETY_LIMITS.MIN_ACCOUNT_BALANCE
            
            # Check circuit breaker
            if daily_loss_pct > SAFETY_LIMITS.CIRCUIT_BREAKER_LOSS:
                self.circuit_breaker_active = True
                self.logger.critical(f"Circuit breaker activated - Daily loss: {daily_loss_pct:.2%}")
            
            risk_status['circuit_breaker'] = not self.circuit_breaker_active
            
            return risk_status
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH,
                context={'portfolio_value': current_portfolio_value}
            )
            return {'error': True}
    
    def update_market_volatility(self, returns: List[float]):
        """Update market volatility estimate"""
        if len(returns) >= self.volatility_lookback:
            recent_returns = returns[-self.volatility_lookback:]
            self.market_volatility = np.std(recent_returns) * np.sqrt(252)  # Annualized
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        try:
            positions_value = sum(
                pos.quantity * pos.current_price 
                for pos in self.positions.values()
            )
            return self.cash_balance + positions_value
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW
            )
            return self.cash_balance
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics"""
        try:
            metrics = PortfolioMetrics()
            
            # Basic metrics
            metrics.total_value = self.get_portfolio_value()
            metrics.cash_balance = self.cash_balance
            metrics.invested_amount = sum(
                pos.quantity * pos.current_price 
                for pos in self.positions.values()
            )
            
            # PnL calculations
            metrics.unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            metrics.realized_pnl = sum(
                trade.get('pnl', 0) for trade in self.trade_history 
                if trade.get('action') == 'CLOSE'
            )
            
            # Return calculations
            metrics.total_return = (metrics.total_value - self.initial_capital) / self.initial_capital
            
            # Performance metrics from closed trades
            if self.closed_positions:
                wins = [pos for pos in self.closed_positions if pos.unrealized_pnl > 0]
                losses = [pos for pos in self.closed_positions if pos.unrealized_pnl <= 0]
                
                metrics.win_rate = len(wins) / len(self.closed_positions)
                metrics.avg_win = np.mean([pos.unrealized_pnl for pos in wins]) if wins else 0
                metrics.avg_loss = np.mean([abs(pos.unrealized_pnl) for pos in losses]) if losses else 0
                
                if metrics.avg_loss > 0:
                    metrics.profit_factor = (metrics.avg_win * len(wins)) / (metrics.avg_loss * len(losses))
            
            # Daily metrics
            metrics.trades_today = self.daily_trades
            metrics.daily_pnl = metrics.total_value - self.daily_start_value
            
            # Sharpe ratio
            if len(self.daily_returns) > 1:
                returns_mean = np.mean(self.daily_returns)
                returns_std = np.std(self.daily_returns)
                if returns_std > 0:
                    metrics.sharpe_ratio = (returns_mean / returns_std) * np.sqrt(252)
            
            # Max drawdown
            if len(self.equity_curve) > 1:
                peak = np.maximum.accumulate(self.equity_curve)
                drawdown = (peak - self.equity_curve) / peak
                metrics.max_drawdown = np.max(drawdown)
            
            return metrics
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM
            )
            return PortfolioMetrics()
    
    def _validate_trade_conditions(self, symbol: str) -> bool:
        """Validate conditions before opening a trade"""
        try:
            # Check if position already exists
            if symbol in self.positions:
                self.logger.warning(f"Position already exists for {symbol}")
                return False
            
            # Check risk limits
            risk_status = self.check_risk_limits()
            if not all(risk_status.values()):
                failed_checks = [k for k, v in risk_status.items() if not v]
                self.logger.warning(f"Risk limit violations: {failed_checks}")
                return False
            
            # Check market hours (placeholder - implement actual market hours check)
            # if not self._is_market_open():
            #     return False
            
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.VALIDATION_ERROR, ErrorSeverity.MEDIUM,
                context={'symbol': symbol}
            )
            return False
    
    def _validate_risk_reward_ratio(self, 
                                  entry_price: float, 
                                  stop_loss: float, 
                                  take_profit: float, 
                                  position_type: PositionType) -> bool:
        """Validate that risk-reward ratio meets minimum requirements"""
        try:
            if position_type == PositionType.LONG:
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk <= 0:
                return False
                
            ratio = reward / risk
            return ratio >= CONFIG.MIN_RISK_REWARD_RATIO
            
        except Exception:
            return False
    
    def _log_trade(self, action: str, position: Position, reason: str = "", pnl: float = 0.0):
        """Log trade details for analysis"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'symbol': position.symbol,
            'position_type': position.position_type.value,
            'quantity': position.quantity,
            'price': position.current_price if action == 'CLOSE' else position.entry_price,
            'pnl': pnl,
            'reason': reason,
            'portfolio_value': self.get_portfolio_value()
        }
        
        self.trade_history.append(trade_record)
    
    def reset_daily_counters(self):
        """Reset daily counters (call at start of each trading day)"""
        self.daily_start_value = self.get_portfolio_value()
        self.daily_trades = 0
        self.circuit_breaker_active = False
        
        # Add to equity curve
        self.equity_curve.append(self.daily_start_value)
        
        # Calculate daily return
        if len(self.equity_curve) > 1:
            daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
            self.daily_returns.append(daily_return)
    
    def get_position_summary(self) -> Dict[str, Dict]:
        """Get summary of all current positions"""
        summary = {}
        for symbol, position in self.positions.items():
            summary[symbol] = {
                'type': position.position_type.value,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'unrealized_pnl': position.unrealized_pnl,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'trailing_stop': position.trailing_stop
            }
        return summary