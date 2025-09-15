#!/usr/bin/env python3
"""
Demo Backtesting for Aura Trading Agent
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

# Simple backtesting simulation without complex imports
def create_mock_data(symbol, start_date, end_date):
    """Create mock market data for backtesting"""
    dates = pd.date_range(start_date, end_date, freq='D')
    np.random.seed(hash(symbol) % 1000)  # Consistent seed per symbol
    
    # Create realistic price movement
    n_days = len(dates)
    returns = np.random.normal(0.0005, 0.02, n_days)  # Daily returns
    prices = 100 * np.cumprod(1 + returns)
    
    # Add some volatility
    high_prices = prices * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
    low_prices = prices * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, n_days)),
        'high': high_prices,
        'low': low_prices,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days)
    }, index=dates)
    
    return data

def calculate_indicators(data):
    """Calculate basic technical indicators"""
    # RSI calculation
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # MACD calculation
    ema_12 = data['close'].ewm(span=12).mean()
    ema_26 = data['close'].ewm(span=26).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9).mean()
    
    # VWAP calculation
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    vwap = (typical_price * data['volume']).cumsum() / data['volume'].cumsum()
    
    # Simple trend indicator
    sma_20 = data['close'].rolling(window=20).mean()
    sma_50 = data['close'].rolling(window=50).mean()
    
    return {
        'rsi': rsi,
        'macd': macd,
        'macd_signal': macd_signal,
        'vwap': vwap,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'price_above_vwap': (data['close'] > vwap).astype(int)
    }

def generate_signals(data, indicators):
    """Generate trading signals based on indicators"""
    signals = pd.Series(0, index=data.index)
    
    # Buy signals
    buy_condition = (
        (indicators['rsi'] < 30) &  # Oversold
        (indicators['macd'] > indicators['macd_signal']) &  # MACD bullish
        (data['close'] > indicators['vwap']) &  # Above VWAP
        (indicators['sma_20'] > indicators['sma_50'])  # Short MA above long MA
    )
    
    # Sell signals  
    sell_condition = (
        (indicators['rsi'] > 70) &  # Overbought
        (indicators['macd'] < indicators['macd_signal']) &  # MACD bearish
        (data['close'] < indicators['vwap']) &  # Below VWAP
        (indicators['sma_20'] < indicators['sma_50'])  # Short MA below long MA
    )
    
    signals[buy_condition] = 1
    signals[sell_condition] = -1
    
    return signals

def backtest_strategy(symbols, start_date, end_date, initial_capital=100000):
    """Run backtest simulation"""
    print(f"Running backtest from {start_date} to {end_date}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print("-" * 50)
    
    # Portfolio tracking
    portfolio_value = initial_capital
    cash = initial_capital
    positions = {}
    closed_trades = []
    daily_values = []
    
    # Get all trading dates
    all_dates = pd.date_range(start_date, end_date, freq='D')
    trading_dates = [d for d in all_dates if d.weekday() < 5]  # Weekdays only
    
    # Fetch data for all symbols
    symbol_data = {}
    symbol_indicators = {}
    symbol_signals = {}
    
    for symbol in symbols:
        data = create_mock_data(symbol, start_date, end_date)
        indicators = calculate_indicators(data)
        signals = generate_signals(data, indicators)
        
        symbol_data[symbol] = data
        symbol_indicators[symbol] = indicators
        symbol_signals[symbol] = signals
    
    # Daily simulation
    for i, date in enumerate(trading_dates):
        if i < 60:  # Skip first 60 days for indicator warmup
            daily_values.append(portfolio_value)
            continue
        
        # Update portfolio value with current positions
        portfolio_value = cash
        for symbol, pos in positions.items():
            if date in symbol_data[symbol].index:
                current_price = symbol_data[symbol].loc[date, 'close']
                portfolio_value += pos['shares'] * current_price
        
        daily_values.append(portfolio_value)
        
        # Check for exit signals (close positions)
        positions_to_close = []
        for symbol, pos in positions.items():
            if date in symbol_data[symbol].index:
                current_price = symbol_data[symbol].loc[date, 'close']
                
                # Check stop loss (5% loss)
                if current_price <= pos['entry_price'] * 0.95:
                    positions_to_close.append((symbol, current_price, 'stop_loss'))
                
                # Check take profit (10% gain)
                elif current_price >= pos['entry_price'] * 1.10:
                    positions_to_close.append((symbol, current_price, 'take_profit'))
                
                # Check exit signal
                elif date in symbol_signals[symbol].index and symbol_signals[symbol].loc[date] == -1:
                    positions_to_close.append((symbol, current_price, 'signal'))
        
        # Close positions
        for symbol, exit_price, reason in positions_to_close:
            pos = positions[symbol]
            trade_pnl = (exit_price - pos['entry_price']) * pos['shares']
            cash += pos['shares'] * exit_price
            
            closed_trades.append({
                'symbol': symbol,
                'entry_date': pos['entry_date'],
                'exit_date': date,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'shares': pos['shares'],
                'pnl': trade_pnl,
                'reason': reason
            })
            
            del positions[symbol]
        
        # Check for new entry signals
        if len(positions) < 5:  # Max 5 positions
            for symbol in symbols:
                if symbol not in positions and date in symbol_signals[symbol].index:
                    if symbol_signals[symbol].loc[date] == 1:  # Buy signal
                        # Calculate position size (2% risk per trade)
                        risk_amount = portfolio_value * 0.02
                        entry_price = symbol_data[symbol].loc[date, 'close']
                        stop_price = entry_price * 0.95  # 5% stop loss
                        
                        shares = int(risk_amount / (entry_price - stop_price))
                        trade_cost = shares * entry_price
                        
                        if trade_cost <= cash * 0.8:  # Don't use all cash
                            positions[symbol] = {
                                'entry_date': date,
                                'entry_price': entry_price,
                                'shares': shares
                            }
                            cash -= trade_cost
    
    # Calculate final results
    final_portfolio_value = cash
    for symbol, pos in positions.items():
        final_price = symbol_data[symbol]['close'].iloc[-1]
        final_portfolio_value += pos['shares'] * final_price
    
    # Results analysis
    total_return = (final_portfolio_value - initial_capital) / initial_capital
    total_trades = len(closed_trades)
    
    if total_trades > 0:
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / total_trades
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(t['pnl']) for t in closed_trades if t['pnl'] <= 0])
        avg_loss = avg_loss if not np.isnan(avg_loss) else 0
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
    
    # Create equity curve
    equity_df = pd.DataFrame({
        'date': trading_dates[:len(daily_values)],
        'portfolio_value': daily_values
    })
    equity_df.set_index('date', inplace=True)
    
    return {
        'initial_capital': initial_capital,
        'final_value': final_portfolio_value,
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'closed_trades': closed_trades,
        'equity_curve': equity_df,
        'success_rate_target_met': win_rate >= 0.80
    }

def plot_results(results):
    """Plot backtest results"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Aura Trading Agent - Backtest Results', fontsize=16)
    
    # Equity curve
    results['equity_curve']['portfolio_value'].plot(ax=ax1)
    ax1.set_title('Portfolio Value Over Time')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.grid(True)
    
    # Drawdown
    peak = results['equity_curve']['portfolio_value'].expanding().max()
    drawdown = (results['equity_curve']['portfolio_value'] - peak) / peak * 100
    ax2.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
    ax2.plot(drawdown.index, drawdown.values, color='red')
    ax2.set_title('Drawdown')
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(True)
    
    # Trade PnL distribution
    if results['closed_trades']:
        pnls = [trade['pnl'] for trade in results['closed_trades']]
        ax3.hist(pnls, bins=20, alpha=0.7, edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--', alpha=0.7)
        ax3.set_title('Trade P&L Distribution')
        ax3.set_xlabel('P&L ($)')
        ax3.set_ylabel('Frequency')
        ax3.grid(True)
    
    # Performance metrics
    metrics_text = f"""
    Total Return: {results['total_return']:.2%}
    Total Trades: {results['total_trades']}
    Win Rate: {results['win_rate']:.2%}
    Avg Win: ${results['avg_win']:.2f}
    Avg Loss: ${results['avg_loss']:.2f}
    
    80% Target Met: {results['success_rate_target_met']}
    """
    
    ax4.text(0.1, 0.5, metrics_text, transform=ax4.transAxes, 
             fontsize=12, verticalalignment='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
    ax4.set_title('Performance Summary')
    ax4.axis('off')
    
    plt.tight_layout()
    plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
    print("\n📊 Backtest chart saved as 'backtest_results.png'")
    plt.show()

def main():
    """Main demo function"""
    print("="*60)
    print("AURA TRADING AGENT - BACKTEST DEMONSTRATION")
    print("="*60)
    
    # Demo parameters
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # Run backtest
    results = backtest_strategy(symbols, start_date, end_date)
    
    # Display results
    print("\n" + "="*50)
    print("BACKTEST RESULTS")
    print("="*50)
    print(f"Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2%}")
    print(f"Average Win: ${results['avg_win']:.2f}")
    print(f"Average Loss: ${results['avg_loss']:.2f}")
    print(f"80% Success Target Met: {'YES' if results['success_rate_target_met'] else 'NO'}")
    
    # Show sample trades
    if results['closed_trades']:
        print(f"\nSample Trades (last 5):")
        for trade in results['closed_trades'][-5:]:
            pnl_str = f"+${trade['pnl']:.2f}" if trade['pnl'] > 0 else f"-${abs(trade['pnl']):.2f}"
            print(f"  {trade['symbol']}: {pnl_str} ({trade['reason']})")
    
    print("="*60)
    
    # Create visualization
    try:
        plot_results(results)
    except Exception as e:
        print(f"Could not create plot: {e}")
    
    # Success message
    if results['success_rate_target_met']:
        print("🎉 SUCCESS: The Aura Trading Agent achieved the 80% success rate target!")
    elif results['win_rate'] >= 0.75:
        print("✅ GOOD: Close to the 80% target. System shows strong potential.")
    else:
        print("⚠️  ROOM FOR IMPROVEMENT: Strategy needs optimization to reach 80% target.")
    
    return results['success_rate_target_met']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)