"""
Test suite for Portfolio Manager
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trading_agent.risk_management.portfolio_manager import (
    PortfolioManager, Position, PositionType, PortfolioMetrics
)
from trading_agent.config import CONFIG


class TestPortfolioManager:
    """Test cases for Portfolio Manager"""
    
    def setup_method(self):
        """Setup test environment"""
        self.initial_capital = 100000.0
        self.portfolio = PortfolioManager(self.initial_capital)
    
    def test_initialization(self):
        """Test portfolio manager initialization"""
        assert self.portfolio.initial_capital == self.initial_capital
        assert self.portfolio.cash_balance == self.initial_capital
        assert len(self.portfolio.positions) == 0
        assert self.portfolio.get_portfolio_value() == self.initial_capital
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        symbol = "AAPL"
        entry_price = 150.0
        stop_loss = 147.0  # 2% stop loss
        
        position_size = self.portfolio.calculate_position_size(symbol, entry_price, stop_loss)
        
        # Should be positive
        assert position_size > 0
        
        # Should not exceed available cash
        required_cash = position_size * entry_price
        assert required_cash <= self.portfolio.cash_balance
        
        # Should respect risk limits
        risk_amount = position_size * abs(entry_price - stop_loss)
        max_risk = self.portfolio.get_portfolio_value() * CONFIG.MAX_POSITION_SIZE
        assert risk_amount <= max_risk * 1.1  # Allow small tolerance
    
    def test_stop_loss_take_profit_calculation(self):
        """Test stop loss and take profit calculation"""
        entry_price = 100.0
        
        # Test long position
        stop_loss, take_profit = self.portfolio.calculate_stop_loss_take_profit(
            entry_price, PositionType.LONG
        )
        
        assert stop_loss < entry_price  # Stop loss below entry for long
        assert take_profit > entry_price  # Take profit above entry for long
        
        # Check risk-reward ratio
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        ratio = reward / risk if risk > 0 else 0
        assert ratio >= CONFIG.MIN_RISK_REWARD_RATIO * 0.95  # Allow small tolerance
        
        # Test short position
        stop_loss, take_profit = self.portfolio.calculate_stop_loss_take_profit(
            entry_price, PositionType.SHORT
        )
        
        assert stop_loss > entry_price  # Stop loss above entry for short
        assert take_profit < entry_price  # Take profit below entry for short
    
    def test_open_long_position(self):
        """Test opening a long position"""
        symbol = "AAPL"
        entry_price = 150.0
        stop_loss = 147.0
        take_profit = 156.0
        
        initial_cash = self.portfolio.cash_balance
        
        success = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        assert success is True
        assert symbol in self.portfolio.positions
        
        position = self.portfolio.positions[symbol]
        assert position.position_type == PositionType.LONG
        assert position.entry_price == entry_price
        assert position.stop_loss == stop_loss
        assert position.take_profit == take_profit
        assert position.quantity > 0
        
        # Check cash was deducted
        expected_cash = initial_cash - (position.quantity * entry_price)
        assert abs(self.portfolio.cash_balance - expected_cash) < 0.01
    
    def test_open_short_position(self):
        """Test opening a short position"""
        symbol = "TSLA"
        entry_price = 200.0
        stop_loss = 204.0
        take_profit = 192.0
        
        success = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.SHORT,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        assert success is True
        assert symbol in self.portfolio.positions
        
        position = self.portfolio.positions[symbol]
        assert position.position_type == PositionType.SHORT
        assert position.entry_price == entry_price
        assert position.stop_loss == stop_loss
        assert position.take_profit == take_profit
    
    def test_close_position(self):
        """Test closing a position"""
        symbol = "AAPL"
        entry_price = 150.0
        
        # Open position first
        self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=entry_price,
            stop_loss=147.0,
            take_profit=156.0
        )
        
        initial_positions = len(self.portfolio.positions)
        initial_closed = len(self.portfolio.closed_positions)
        
        # Close position at profit
        close_price = 155.0
        success = self.portfolio.close_position(symbol, close_price, "take_profit")
        
        assert success is True
        assert symbol not in self.portfolio.positions
        assert len(self.portfolio.positions) == initial_positions - 1
        assert len(self.portfolio.closed_positions) == initial_closed + 1
        
        # Check trade was profitable
        closed_position = self.portfolio.closed_positions[-1]
        assert closed_position.unrealized_pnl > 0
    
    def test_update_positions(self):
        """Test updating positions with market data"""
        symbol = "AAPL"
        entry_price = 150.0
        
        # Open position
        self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=entry_price,
            stop_loss=147.0,
            take_profit=156.0
        )
        
        # Update with profitable price
        market_data = {symbol: 153.0}
        self.portfolio.update_positions(market_data)
        
        position = self.portfolio.positions[symbol]
        assert position.current_price == 153.0
        assert position.unrealized_pnl > 0
        
        # Trailing stop should have moved up
        assert position.trailing_stop > 147.0
    
    def test_trailing_stop_mechanism(self):
        """Test trailing stop loss mechanism"""
        symbol = "AAPL"
        entry_price = 150.0
        
        # Open long position
        self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=entry_price,
            stop_loss=147.0,
            take_profit=160.0
        )
        
        position = self.portfolio.positions[symbol]
        initial_trailing_stop = position.trailing_stop
        
        # Price moves up significantly
        market_data = {symbol: 158.0}
        self.portfolio.update_positions(market_data)
        
        # Trailing stop should have moved up
        assert position.trailing_stop > initial_trailing_stop
        
        # Price moves down to hit trailing stop
        market_data = {symbol: position.trailing_stop - 0.01}
        initial_positions = len(self.portfolio.positions)
        
        self.portfolio.update_positions(market_data)
        
        # Position should be closed
        assert len(self.portfolio.positions) == initial_positions - 1
    
    def test_risk_limits(self):
        """Test risk limit enforcement"""
        risk_status = self.portfolio.check_risk_limits()
        
        # All limits should be ok initially
        assert all(risk_status.values())
        
        # Test daily loss limit by simulating large loss
        self.portfolio.daily_start_value = self.initial_capital
        large_loss = self.initial_capital * 0.06  # 6% loss (above 5% limit)
        
        # Simulate positions with large losses
        for i in range(5):
            symbol = f"TEST{i}"
            position = Position(
                symbol=symbol,
                position_type=PositionType.LONG,
                quantity=100,
                entry_price=100.0,
                entry_time=datetime.now(),
                stop_loss=95.0,
                take_profit=110.0,
                trailing_stop=95.0,
                current_price=94.0,  # Below stop loss
                unrealized_pnl=-600.0  # $600 loss per position
            )
            self.portfolio.positions[symbol] = position
        
        # Update cash to reflect losses
        self.portfolio.cash_balance -= large_loss
        
        risk_status = self.portfolio.check_risk_limits()
        assert not risk_status['daily_loss_limit']
    
    def test_portfolio_metrics(self):
        """Test portfolio metrics calculation"""
        # Open some positions
        symbols = ["AAPL", "GOOGL", "MSFT"]
        for i, symbol in enumerate(symbols):
            self.portfolio.open_position(
                symbol=symbol,
                position_type=PositionType.LONG,
                entry_price=100.0 + i * 10,
                stop_loss=95.0 + i * 10,
                take_profit=110.0 + i * 10
            )
        
        # Update with some profits/losses
        market_data = {
            "AAPL": 105.0,  # Profit
            "GOOGL": 108.0,  # Profit
            "MSFT": 118.0   # Profit
        }
        self.portfolio.update_positions(market_data)
        
        metrics = self.portfolio.get_portfolio_metrics()
        
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.total_value > 0
        assert metrics.cash_balance >= 0
        assert metrics.unrealized_pnl > 0  # Should have profits
        
        # Close a position for realized PnL
        self.portfolio.close_position("AAPL", 105.0, "manual")
        
        updated_metrics = self.portfolio.get_portfolio_metrics()
        assert updated_metrics.realized_pnl > 0
    
    def test_risk_reward_validation(self):
        """Test risk-reward ratio validation"""
        symbol = "AAPL"
        entry_price = 100.0
        
        # Test insufficient risk-reward ratio
        stop_loss = 99.0  # 1% risk
        take_profit = 101.0  # 1% reward (1:1 ratio, below 2:1 minimum)
        
        success = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Should fail due to poor risk-reward ratio
        assert success is False
        assert symbol not in self.portfolio.positions
        
        # Test good risk-reward ratio
        take_profit = 102.0  # 2% reward (2:1 ratio)
        
        success = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        assert success is True
        assert symbol in self.portfolio.positions
    
    def test_duplicate_position_prevention(self):
        """Test prevention of duplicate positions"""
        symbol = "AAPL"
        
        # Open first position
        success1 = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=150.0,
            stop_loss=147.0,
            take_profit=156.0
        )
        
        assert success1 is True
        
        # Try to open another position for same symbol
        success2 = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.SHORT,
            entry_price=150.0,
            stop_loss=153.0,
            take_profit=144.0
        )
        
        assert success2 is False  # Should fail
        assert len(self.portfolio.positions) == 1  # Still only one position
    
    def test_insufficient_funds(self):
        """Test handling of insufficient funds"""
        symbol = "AAPL"
        
        # Try to open a position larger than available funds
        # Set very low cash balance
        self.portfolio.cash_balance = 1000.0
        
        success = self.portfolio.open_position(
            symbol=symbol,
            position_type=PositionType.LONG,
            entry_price=150.0,
            stop_loss=147.0,
            take_profit=156.0
        )
        
        # Should either succeed with smaller position or fail
        if success:
            position = self.portfolio.positions[symbol]
            required_cash = position.quantity * position.entry_price
            assert required_cash <= 1000.0 * 0.95  # Within available funds (with buffer)
    
    def test_daily_counter_reset(self):
        """Test daily counter reset functionality"""
        # Simulate some trading activity
        self.portfolio.daily_trades = 5
        initial_value = self.portfolio.get_portfolio_value()
        
        # Reset daily counters
        self.portfolio.reset_daily_counters()
        
        assert self.portfolio.daily_trades == 0
        assert self.portfolio.daily_start_value == initial_value
        assert len(self.portfolio.equity_curve) > 1
    
    def test_position_summary(self):
        """Test position summary generation"""
        # Initially empty
        summary = self.portfolio.get_position_summary()
        assert len(summary) == 0
        
        # Open some positions
        symbols = ["AAPL", "GOOGL"]
        for symbol in symbols:
            self.portfolio.open_position(
                symbol=symbol,
                position_type=PositionType.LONG,
                entry_price=150.0,
                stop_loss=147.0,
                take_profit=156.0
            )
        
        summary = self.portfolio.get_position_summary()
        assert len(summary) == 2
        
        for symbol in symbols:
            assert symbol in summary
            position_info = summary[symbol]
            assert 'type' in position_info
            assert 'quantity' in position_info
            assert 'entry_price' in position_info
            assert 'unrealized_pnl' in position_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])