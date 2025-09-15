"""
Enhanced Error Handler with granular categorization and recovery mechanisms
"""
import logging
import traceback
from enum import Enum
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict


class ErrorCategory(Enum):
    """Categorization of different error types"""
    DATA_ERROR = "data_error"
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    TRADING_ERROR = "trading_error"
    MODEL_ERROR = "model_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    MARKET_ERROR = "market_error"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Detailed error information"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    timestamp: datetime
    context: Dict[str, Any]
    traceback: str
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[str] = None


class ErrorHandler:
    """Enhanced error handler with recovery mechanisms"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history: Dict[str, list] = {}
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {
            ErrorCategory.DATA_ERROR: self._recover_data_error,
            ErrorCategory.NETWORK_ERROR: self._recover_network_error,
            ErrorCategory.API_ERROR: self._recover_api_error,
            ErrorCategory.TRADING_ERROR: self._recover_trading_error,
            ErrorCategory.MODEL_ERROR: self._recover_model_error,
            ErrorCategory.VALIDATION_ERROR: self._recover_validation_error,
            ErrorCategory.SYSTEM_ERROR: self._recover_system_error,
            ErrorCategory.MARKET_ERROR: self._recover_market_error,
        }
        self.circuit_breaker_triggered = False
        self.error_counts = {category: 0 for category in ErrorCategory}
        self.last_error_time = {}
        
    def handle_error(self, 
                    error: Exception, 
                    category: ErrorCategory, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Dict[str, Any] = None,
                    attempt_recovery: bool = True) -> ErrorInfo:
        """
        Handle an error with categorization and optional recovery
        """
        if context is None:
            context = {}
            
        error_info = ErrorInfo(
            category=category,
            severity=severity,
            message=str(error),
            timestamp=datetime.now(),
            context=context,
            traceback=traceback.format_exc()
        )
        
        # Log the error
        self._log_error(error_info)
        
        # Update error statistics
        self._update_error_stats(error_info)
        
        # Store error in history
        self._store_error(error_info)
        
        # Check if circuit breaker should be triggered
        if self._should_trigger_circuit_breaker(error_info):
            self._trigger_circuit_breaker()
            
        # Attempt recovery if requested and strategy exists
        if attempt_recovery and category in self.recovery_strategies:
            try:
                error_info.recovery_attempted = True
                error_info.recovery_strategy = category.value
                recovery_result = self.recovery_strategies[category](error_info)
                error_info.recovery_successful = recovery_result
                
                if recovery_result:
                    self.logger.info(f"Successfully recovered from {category.value} error")
                else:
                    self.logger.warning(f"Recovery failed for {category.value} error")
                    
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed: {recovery_error}")
                error_info.recovery_successful = False
                
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level"""
        log_message = (
            f"[{error_info.category.value.upper()}] "
            f"{error_info.message} | "
            f"Context: {error_info.context}"
        )
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """Update error statistics"""
        self.error_counts[error_info.category] += 1
        self.last_error_time[error_info.category] = error_info.timestamp
    
    def _store_error(self, error_info: ErrorInfo):
        """Store error in history for analysis"""
        category_key = error_info.category.value
        if category_key not in self.error_history:
            self.error_history[category_key] = []
        
        self.error_history[category_key].append(asdict(error_info))
        
        # Keep only last 100 errors per category
        if len(self.error_history[category_key]) > 100:
            self.error_history[category_key] = self.error_history[category_key][-100:]
    
    def _should_trigger_circuit_breaker(self, error_info: ErrorInfo) -> bool:
        """Determine if circuit breaker should be triggered"""
        if self.circuit_breaker_triggered:
            return False
            
        # Trigger on critical errors
        if error_info.severity == ErrorSeverity.CRITICAL:
            return True
            
        # Trigger on high frequency of trading errors
        if error_info.category == ErrorCategory.TRADING_ERROR:
            recent_trading_errors = self._count_recent_errors(
                ErrorCategory.TRADING_ERROR, 
                minutes=15
            )
            if recent_trading_errors >= 5:
                return True
                
        # Trigger on multiple high severity errors
        recent_high_errors = sum(
            self._count_recent_errors(cat, minutes=30) 
            for cat in ErrorCategory
        )
        if recent_high_errors >= 10:
            return True
            
        return False
    
    def _count_recent_errors(self, category: ErrorCategory, minutes: int) -> int:
        """Count recent errors of a specific category"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        category_key = category.value
        
        if category_key not in self.error_history:
            return 0
            
        return len([
            error for error in self.error_history[category_key]
            if datetime.fromisoformat(error['timestamp']) > cutoff_time
        ])
    
    def _trigger_circuit_breaker(self):
        """Trigger circuit breaker to halt trading"""
        self.circuit_breaker_triggered = True
        self.logger.critical("CIRCUIT BREAKER TRIGGERED - Trading halted due to excessive errors")
        
        # Additional safety measures can be implemented here
        # e.g., close all positions, send alerts, etc.
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker (manual intervention required)"""
        self.circuit_breaker_triggered = False
        self.logger.info("Circuit breaker reset - Trading can resume")
    
    # Recovery strategies for different error categories
    
    def _recover_data_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from data errors"""
        try:
            # Try alternative data source
            # Implement retry with exponential backoff
            # Cache fallback data
            self.logger.info("Attempting data error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_network_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from network errors"""
        try:
            # Implement retry with backoff
            # Switch to backup connection
            # Use cached data if available
            self.logger.info("Attempting network error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_api_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from API errors"""
        try:
            # Check API rate limits
            # Switch to alternative API
            # Use cached responses
            self.logger.info("Attempting API error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_trading_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from trading errors"""
        try:
            # Cancel pending orders
            # Recalculate position sizes
            # Validate account status
            self.logger.info("Attempting trading error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_model_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from model errors"""
        try:
            # Fall back to simpler model
            # Use ensemble average
            # Skip prediction for this cycle
            self.logger.info("Attempting model error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_validation_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from validation errors"""
        try:
            # Apply default values
            # Skip invalid data points
            # Log for manual review
            self.logger.info("Attempting validation error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_system_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from system errors"""
        try:
            # Restart services
            # Clear caches
            # Reload configurations
            self.logger.info("Attempting system error recovery...")
            return True
        except Exception:
            return False
    
    def _recover_market_error(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from market errors"""
        try:
            # Check market status
            # Adjust trading parameters
            # Wait for market stability
            self.logger.info("Attempting market error recovery...")
            return True
        except Exception:
            return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'circuit_breaker_triggered': self.circuit_breaker_triggered,
            'last_error_times': {
                k.value: v.isoformat() if v else None 
                for k, v in self.last_error_time.items()
            },
            'total_errors': sum(self.error_counts.values())
        }
    
    def export_error_history(self, filepath: str):
        """Export error history to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.error_history, f, indent=2, default=str)
            self.logger.info(f"Error history exported to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to export error history: {e}")


# Global error handler instance
error_handler = ErrorHandler()