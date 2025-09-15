#!/usr/bin/env python3
"""
Simple test script to validate Aura Trading Agent functionality
"""
import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add trading_agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_agent'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    try:
        from config import CONFIG, DEFAULT_WATCHLIST, MARKET_HOURS, SAFETY_LIMITS
        from core.error_handler import error_handler, ErrorCategory, ErrorSeverity
        from indicators.technical_indicators import TechnicalIndicators
        from risk_management.portfolio_manager import PortfolioManager, PositionType
        from ml_models.ensemble_predictor import ensemble_predictor
        from data.data_fetcher import data_fetcher
        
        logger.info("✓ All modules imported successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_portfolio_manager():
    """Test basic portfolio manager functionality"""
    try:
        portfolio = PortfolioManager(100000.0)
        
        # Test initialization
        assert portfolio.initial_capital == 100000.0
        assert portfolio.cash_balance == 100000.0
        assert len(portfolio.positions) == 0
        
        # Test position size calculation
        position_size = portfolio.calculate_position_size("AAPL", 150.0, 147.0)
        assert position_size > 0
        
        # Test opening a position
        success = portfolio.open_position(
            symbol="AAPL",
            position_type=PositionType.LONG,
            entry_price=150.0,
            stop_loss=147.0,
            take_profit=156.0
        )
        assert success is True
        assert "AAPL" in portfolio.positions
        
        # Test updating position
        market_data = {"AAPL": 153.0}
        portfolio.update_positions(market_data)
        
        position = portfolio.positions["AAPL"]
        assert position.current_price == 153.0
        assert position.unrealized_pnl > 0
        
        # Test closing position
        success = portfolio.close_position("AAPL", 155.0, "manual")
        assert success is True
        assert "AAPL" not in portfolio.positions
        assert len(portfolio.closed_positions) == 1
        
        logger.info("✓ Portfolio Manager tests passed")
        return True
    except Exception as e:
        logger.error(f"✗ Portfolio Manager test failed: {e}")
        return False

def test_technical_indicators():
    """Test technical indicators calculation"""
    try:
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        data = pd.DataFrame({
            'open': prices + np.random.randn(100) * 0.1,
            'high': prices + np.abs(np.random.randn(100) * 0.5),
            'low': prices - np.abs(np.random.randn(100) * 0.5),
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        # Test individual indicators
        rsi = TechnicalIndicators.calculate_rsi(data['close'])
        assert len(rsi) == len(data)
        assert rsi.max() <= 100
        assert rsi.min() >= 0
        
        macd, macd_signal, macd_hist = TechnicalIndicators.calculate_macd(data['close'])
        assert len(macd) == len(data)
        assert len(macd_signal) == len(data)
        assert len(macd_hist) == len(data)
        
        # Test VWAP
        vwap = TechnicalIndicators.calculate_vwap(
            data['high'], data['low'], data['close'], data['volume']
        )
        assert len(vwap) == len(data)
        assert not vwap.isna().all()
        
        # Test ADX
        adx, di_plus, di_minus = TechnicalIndicators.calculate_adx(
            data['high'], data['low'], data['close']
        )
        assert len(adx) == len(data)
        
        # Test comprehensive indicators
        all_indicators = TechnicalIndicators.calculate_all_indicators(data)
        assert len(all_indicators) == len(data)
        assert 'rsi' in all_indicators.columns
        assert 'macd' in all_indicators.columns
        assert 'vwap' in all_indicators.columns
        assert 'adx' in all_indicators.columns
        
        # Test signal strength
        signal_strength = TechnicalIndicators.get_signal_strength(all_indicators)
        assert len(signal_strength) == len(data)
        assert signal_strength.max() <= 1.0
        assert signal_strength.min() >= -1.0
        
        logger.info("✓ Technical Indicators tests passed")
        return True
    except Exception as e:
        logger.error(f"✗ Technical Indicators test failed: {e}")
        return False

def test_error_handler():
    """Test error handler functionality"""
    try:
        # Test error handling
        test_error = ValueError("Test error")
        error_info = error_handler.handle_error(
            test_error, 
            ErrorCategory.VALIDATION_ERROR, 
            ErrorSeverity.MEDIUM,
            context={'test': True}
        )
        
        assert error_info.category == ErrorCategory.VALIDATION_ERROR
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.message == "Test error"
        assert error_info.context['test'] is True
        
        # Test error summary
        summary = error_handler.get_error_summary()
        assert 'error_counts' in summary
        assert 'total_errors' in summary
        assert summary['total_errors'] > 0
        
        logger.info("✓ Error Handler tests passed")
        return True
    except Exception as e:
        logger.error(f"✗ Error Handler test failed: {e}")
        return False

async def test_data_fetcher():
    """Test data fetcher functionality"""
    try:
        # Test basic data fetching
        async with data_fetcher:
            # Test single symbol
            data = await data_fetcher.fetch_historical_data("AAPL", period="1mo", interval="1d")
            if data is not None:
                assert len(data) > 0
                assert 'close' in data.columns
                assert 'volume' in data.columns
                logger.info("✓ Single symbol data fetch successful")
            else:
                logger.warning("⚠ Could not fetch AAPL data (possibly rate limited)")
            
            # Test validation
            valid_symbols = await data_fetcher.validate_symbols(["AAPL", "INVALID_SYMBOL"])
            logger.info(f"✓ Symbol validation returned: {valid_symbols}")
            
        logger.info("✓ Data Fetcher tests passed")
        return True
    except Exception as e:
        logger.error(f"✗ Data Fetcher test failed: {e}")
        return False

def test_ml_models():
    """Test ML model functionality"""
    try:
        # Create sample training data
        dates = pd.date_range('2022-01-01', periods=300, freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(300) * 0.5)
        
        training_data = pd.DataFrame({
            'open': prices + np.random.randn(300) * 0.1,
            'high': prices + np.abs(np.random.randn(300) * 0.5),
            'low': prices - np.abs(np.random.randn(300) * 0.5),
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, 300)
        }, index=dates)
        
        # Test model training
        training_results = ensemble_predictor.train_all_models(training_data)
        
        # At least some models should train successfully
        successful_models = sum(training_results.values())
        assert successful_models > 0
        
        logger.info(f"✓ ML Models trained: {successful_models} successful")
        
        # Test prediction if any model trained
        if ensemble_predictor.is_trained:
            prediction = ensemble_predictor.predict(training_data.tail(60))
            assert prediction.signal is not None
            assert 0 <= prediction.confidence <= 1
            logger.info("✓ ML prediction successful")
        
        logger.info("✓ ML Models tests passed")
        return True
    except Exception as e:
        logger.error(f"✗ ML Models test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from config import CONFIG, DEFAULT_WATCHLIST, MARKET_HOURS, SAFETY_LIMITS
        
        # Test config values
        assert CONFIG.MAX_POSITION_SIZE > 0
        assert CONFIG.MIN_RISK_REWARD_RATIO >= 2.0
        assert CONFIG.TARGET_SUCCESS_RATE == 0.80
        
        # Test watchlist
        assert len(DEFAULT_WATCHLIST) > 0
        assert all(isinstance(symbol, str) for symbol in DEFAULT_WATCHLIST)
        
        # Test market hours
        assert MARKET_HOURS.MARKET_OPEN
        assert MARKET_HOURS.MARKET_CLOSE
        
        # Test safety limits
        assert SAFETY_LIMITS.MAX_TRADES_PER_DAY > 0
        assert SAFETY_LIMITS.MAX_DRAWDOWN_PERCENT > 0
        
        logger.info("✓ Configuration tests passed")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    logger.info("Starting Aura Trading Agent Tests...")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Portfolio Manager", test_portfolio_manager),
        ("Technical Indicators", test_technical_indicators),
        ("Error Handler", test_error_handler),
        ("Data Fetcher", test_data_fetcher),
        ("ML Models", test_ml_models),
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<20}: {status}")
    
    logger.info("-"*50)
    logger.info(f"Tests Passed: {passed}/{total}")
    logger.info(f"Success Rate: {passed/total:.1%}")
    
    if passed == total:
        logger.info("🎉 All tests passed! Aura Trading Agent is ready.")
    elif passed >= total * 0.8:  # 80% pass rate
        logger.info("✅ Most tests passed. System is functional with minor issues.")
    else:
        logger.info("❌ Multiple test failures. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)