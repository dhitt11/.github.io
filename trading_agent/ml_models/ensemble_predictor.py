"""
Ensemble ML Models for Enhanced AI Decision-Making
Combines multiple models for better prediction accuracy
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import pickle
import logging
from dataclasses import dataclass
from enum import Enum

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

from ..config import CONFIG
from ..core.error_handler import error_handler, ErrorCategory, ErrorSeverity
from ..indicators.technical_indicators import TechnicalIndicators


class PredictionSignal(Enum):
    STRONG_SELL = -2
    SELL = -1
    HOLD = 0
    BUY = 1
    STRONG_BUY = 2


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: np.ndarray
    feature_importance: Dict[str, float] = None


@dataclass
class EnsemblePrediction:
    """Ensemble prediction result"""
    signal: PredictionSignal
    confidence: float
    individual_predictions: Dict[str, int]
    model_weights: Dict[str, float]
    features_used: List[str]


class BasePredictor:
    """Base class for all predictors"""
    
    def __init__(self, name: str):
        self.name = name
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.performance = None
        self.feature_names = []
        
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for training/prediction"""
        # Get all technical indicators
        features_df = TechnicalIndicators.calculate_all_indicators(data)
        
        # Add price-based features
        features_df['price_change'] = features_df['close'].pct_change()
        features_df['price_change_5'] = features_df['close'].pct_change(periods=5)
        features_df['price_change_10'] = features_df['close'].pct_change(periods=10)
        
        # Add volume features
        features_df['volume_change'] = features_df['volume'].pct_change()
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume'].rolling(20).mean()
        
        # Add volatility features
        features_df['volatility_5'] = features_df['close'].rolling(5).std()
        features_df['volatility_20'] = features_df['close'].rolling(20).std()
        
        # Add time-based features
        features_df['hour'] = pd.to_datetime(features_df.index).hour if isinstance(features_df.index, pd.DatetimeIndex) else 14
        features_df['day_of_week'] = pd.to_datetime(features_df.index).dayofweek if isinstance(features_df.index, pd.DatetimeIndex) else 2
        
        return features_df
    
    def create_target(self, data: pd.DataFrame, lookforward: int = 5) -> pd.Series:
        """Create target variable for classification"""
        future_returns = data['close'].shift(-lookforward) / data['close'] - 1
        
        # Create 5-class classification
        conditions = [
            future_returns <= -0.02,  # Strong sell
            (future_returns > -0.02) & (future_returns <= -0.005),  # Sell
            (future_returns > -0.005) & (future_returns < 0.005),  # Hold
            (future_returns >= 0.005) & (future_returns < 0.02),  # Buy
            future_returns >= 0.02  # Strong buy
        ]
        
        choices = [-2, -1, 0, 1, 2]
        target = np.select(conditions, choices, default=0)
        
        return pd.Series(target, index=data.index)
    
    def train(self, data: pd.DataFrame) -> bool:
        """Train the model - to be implemented by subclasses"""
        raise NotImplementedError
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Make predictions - to be implemented by subclasses"""
        raise NotImplementedError


class RandomForestPredictor(BasePredictor):
    """Random Forest predictor"""
    
    def __init__(self):
        super().__init__("RandomForest")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
    
    def train(self, data: pd.DataFrame) -> bool:
        try:
            features_df = self.prepare_features(data)
            target = self.create_target(data)
            
            # Select features (remove non-numeric and target-related columns)
            feature_columns = [col for col in features_df.columns 
                             if col not in ['open', 'high', 'low', 'close', 'volume'] 
                             and features_df[col].dtype in ['float64', 'int64']]
            
            X = features_df[feature_columns].fillna(0)
            y = target
            
            # Remove rows where target is NaN
            valid_idx = ~y.isna()
            X = X[valid_idx]
            y = y[valid_idx]
            
            if len(X) < 100:  # Minimum data requirement
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate performance
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Store feature names and performance
            self.feature_names = feature_columns
            self.performance = ModelPerformance(
                accuracy=accuracy,
                precision=0.0,  # Simplified for now
                recall=0.0,
                f1_score=0.0,
                confusion_matrix=confusion_matrix(y_test, y_pred),
                feature_importance=dict(zip(feature_columns, self.model.feature_importances_))
            )
            
            self.is_trained = True
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM,
                context={'model': self.name}
            )
            return False
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        try:
            features_df = self.prepare_features(data)
            X = features_df[self.feature_names].fillna(0)
            X_scaled = self.scaler.transform(X)
            
            predictions = self.model.predict(X_scaled)
            return predictions
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH,
                context={'model': self.name}
            )
            return np.array([0])  # Return neutral prediction on error


class GradientBoostingPredictor(BasePredictor):
    """Gradient Boosting predictor"""
    
    def __init__(self):
        super().__init__("GradientBoosting")
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
    
    def train(self, data: pd.DataFrame) -> bool:
        try:
            features_df = self.prepare_features(data)
            target = self.create_target(data)
            
            feature_columns = [col for col in features_df.columns 
                             if col not in ['open', 'high', 'low', 'close', 'volume'] 
                             and features_df[col].dtype in ['float64', 'int64']]
            
            X = features_df[feature_columns].fillna(0)
            y = target
            
            valid_idx = ~y.isna()
            X = X[valid_idx]
            y = y[valid_idx]
            
            if len(X) < 100:
                return False
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            self.model.fit(X_train_scaled, y_train)
            
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.feature_names = feature_columns
            self.performance = ModelPerformance(
                accuracy=accuracy,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                confusion_matrix=confusion_matrix(y_test, y_pred),
                feature_importance=dict(zip(feature_columns, self.model.feature_importances_))
            )
            
            self.is_trained = True
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM,
                context={'model': self.name}
            )
            return False
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        try:
            features_df = self.prepare_features(data)
            X = features_df[self.feature_names].fillna(0)
            X_scaled = self.scaler.transform(X)
            
            predictions = self.model.predict(X_scaled)
            return predictions
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH,
                context={'model': self.name}
            )
            return np.array([0])


class LSTMPredictor(BasePredictor):
    """LSTM Neural Network predictor"""
    
    def __init__(self):
        super().__init__("LSTM")
        self.model = None
        self.lookback_window = 60
        self.label_encoder = LabelEncoder()
    
    def create_sequences(self, data: np.ndarray, target: np.ndarray, window_size: int):
        """Create sequences for LSTM training"""
        X, y = [], []
        for i in range(window_size, len(data)):
            X.append(data[i-window_size:i])
            y.append(target[i])
        return np.array(X), np.array(y)
    
    def train(self, data: pd.DataFrame) -> bool:
        try:
            features_df = self.prepare_features(data)
            target = self.create_target(data)
            
            feature_columns = [col for col in features_df.columns 
                             if col not in ['open', 'high', 'low', 'close', 'volume'] 
                             and features_df[col].dtype in ['float64', 'int64']]
            
            X = features_df[feature_columns].fillna(0).values
            y = target.fillna(0).values
            
            if len(X) < self.lookback_window + 100:
                return False
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Encode labels
            y_encoded = self.label_encoder.fit_transform(y + 2)  # Shift to make all positive
            
            # Create sequences
            X_seq, y_seq = self.create_sequences(X_scaled, y_encoded, self.lookback_window)
            
            # Split data
            split_idx = int(0.8 * len(X_seq))
            X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
            y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]
            
            # Build LSTM model
            self.model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(self.lookback_window, len(feature_columns))),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(len(np.unique(y_encoded)), activation='softmax')
            ])
            
            self.model.compile(
                optimizer=Adam(learning_rate=0.001),
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            # Train model
            early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
            reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.0001)
            
            history = self.model.fit(
                X_train, y_train,
                batch_size=32,
                epochs=50,
                validation_data=(X_test, y_test),
                callbacks=[early_stopping, reduce_lr],
                verbose=0
            )
            
            # Evaluate performance
            y_pred = self.model.predict(X_test, verbose=0)
            y_pred_classes = np.argmax(y_pred, axis=1)
            accuracy = accuracy_score(y_test, y_pred_classes)
            
            self.feature_names = feature_columns
            self.performance = ModelPerformance(
                accuracy=accuracy,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                confusion_matrix=confusion_matrix(y_test, y_pred_classes)
            )
            
            self.is_trained = True
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM,
                context={'model': self.name}
            )
            return False
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        try:
            features_df = self.prepare_features(data)
            X = features_df[self.feature_names].fillna(0).values
            
            if len(X) < self.lookback_window:
                return np.array([0])
            
            X_scaled = self.scaler.transform(X)
            
            # Get last sequence
            X_seq = X_scaled[-self.lookback_window:].reshape(1, self.lookback_window, -1)
            
            prediction = self.model.predict(X_seq, verbose=0)
            predicted_class = np.argmax(prediction, axis=1)[0]
            
            # Decode back to original labels
            original_label = self.label_encoder.inverse_transform([predicted_class])[0] - 2
            
            return np.array([original_label])
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH,
                context={'model': self.name}
            )
            return np.array([0])


class SVMPredictor(BasePredictor):
    """Support Vector Machine predictor"""
    
    def __init__(self):
        super().__init__("SVM")
        self.model = SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            random_state=42,
            probability=True  # Enable probability estimates
        )
    
    def train(self, data: pd.DataFrame) -> bool:
        try:
            features_df = self.prepare_features(data)
            target = self.create_target(data)
            
            feature_columns = [col for col in features_df.columns 
                             if col not in ['open', 'high', 'low', 'close', 'volume'] 
                             and features_df[col].dtype in ['float64', 'int64']]
            
            # Limit features for SVM (computational efficiency)
            if len(feature_columns) > 20:
                # Select top features based on correlation with target
                correlations = {}
                for col in feature_columns:
                    try:
                        corr = abs(features_df[col].corr(target))
                        if not np.isnan(corr):
                            correlations[col] = corr
                    except:
                        continue
                
                sorted_features = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
                feature_columns = [f[0] for f in sorted_features[:20]]
            
            X = features_df[feature_columns].fillna(0)
            y = target
            
            valid_idx = ~y.isna()
            X = X[valid_idx]
            y = y[valid_idx]
            
            if len(X) < 100:
                return False
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            self.model.fit(X_train_scaled, y_train)
            
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.feature_names = feature_columns
            self.performance = ModelPerformance(
                accuracy=accuracy,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                confusion_matrix=confusion_matrix(y_test, y_pred)
            )
            
            self.is_trained = True
            return True
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM,
                context={'model': self.name}
            )
            return False
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        try:
            features_df = self.prepare_features(data)
            X = features_df[self.feature_names].fillna(0)
            X_scaled = self.scaler.transform(X)
            
            predictions = self.model.predict(X_scaled)
            return predictions
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH,
                context={'model': self.name}
            )
            return np.array([0])


class EnsemblePredictor:
    """Ensemble predictor combining multiple models"""
    
    def __init__(self):
        self.models = {
            'random_forest': RandomForestPredictor(),
            'gradient_boosting': GradientBoostingPredictor(),
            'lstm': LSTMPredictor(),
            'svm': SVMPredictor()
        }
        
        self.model_weights = {name: 0.25 for name in self.models.keys()}  # Equal weights initially
        self.is_trained = False
        self.logger = logging.getLogger(__name__)
    
    def train_all_models(self, data: pd.DataFrame) -> Dict[str, bool]:
        """Train all models and return success status"""
        training_results = {}
        
        for name, model in self.models.items():
            try:
                self.logger.info(f"Training {name} model...")
                success = model.train(data)
                training_results[name] = success
                
                if success:
                    self.logger.info(f"{name} model trained successfully. Accuracy: {model.performance.accuracy:.3f}")
                else:
                    self.logger.warning(f"Failed to train {name} model")
                    
            except Exception as e:
                error_handler.handle_error(
                    e, ErrorCategory.MODEL_ERROR, ErrorSeverity.MEDIUM,
                    context={'model': name}
                )
                training_results[name] = False
        
        # Update model weights based on performance
        self._update_model_weights()
        
        # Consider ensemble trained if at least 2 models are trained
        self.is_trained = sum(training_results.values()) >= 2
        
        return training_results
    
    def _update_model_weights(self):
        """Update model weights based on performance"""
        try:
            trained_models = {name: model for name, model in self.models.items() 
                            if model.is_trained and model.performance}
            
            if not trained_models:
                return
            
            # Weight models based on accuracy
            total_accuracy = sum(model.performance.accuracy for model in trained_models.values())
            
            if total_accuracy > 0:
                for name, model in trained_models.items():
                    self.model_weights[name] = model.performance.accuracy / total_accuracy
                
                # Set weight to 0 for untrained models
                for name in self.models.keys():
                    if name not in trained_models:
                        self.model_weights[name] = 0.0
                        
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.LOW,
                context={'method': '_update_model_weights'}
            )
    
    def predict(self, data: pd.DataFrame) -> EnsemblePrediction:
        """Make ensemble prediction"""
        if not self.is_trained:
            raise ValueError("Ensemble must be trained before prediction")
        
        try:
            individual_predictions = {}
            prediction_scores = {}
            
            # Get predictions from all trained models
            for name, model in self.models.items():
                if model.is_trained:
                    try:
                        pred = model.predict(data)
                        if len(pred) > 0:
                            individual_predictions[name] = int(pred[-1])  # Get last prediction
                            prediction_scores[name] = pred[-1] * self.model_weights[name]
                    except Exception as e:
                        self.logger.warning(f"Prediction failed for {name}: {e}")
                        individual_predictions[name] = 0
                        prediction_scores[name] = 0
            
            if not prediction_scores:
                # Return neutral prediction if no models worked
                return EnsemblePrediction(
                    signal=PredictionSignal.HOLD,
                    confidence=0.0,
                    individual_predictions={},
                    model_weights=self.model_weights,
                    features_used=[]
                )
            
            # Calculate weighted ensemble prediction
            ensemble_score = sum(prediction_scores.values())
            
            # Convert to signal
            if ensemble_score >= 1.5:
                signal = PredictionSignal.STRONG_BUY
            elif ensemble_score >= 0.5:
                signal = PredictionSignal.BUY
            elif ensemble_score <= -1.5:
                signal = PredictionSignal.STRONG_SELL
            elif ensemble_score <= -0.5:
                signal = PredictionSignal.SELL
            else:
                signal = PredictionSignal.HOLD
            
            # Calculate confidence based on agreement between models
            predictions_list = list(individual_predictions.values())
            if predictions_list:
                # Higher confidence when models agree
                most_common = max(set(predictions_list), key=predictions_list.count)
                agreement_ratio = predictions_list.count(most_common) / len(predictions_list)
                confidence = agreement_ratio * min(1.0, abs(ensemble_score))
            else:
                confidence = 0.0
            
            return EnsemblePrediction(
                signal=signal,
                confidence=confidence,
                individual_predictions=individual_predictions,
                model_weights=self.model_weights,
                features_used=list(self.models.values())[0].feature_names if self.models else []
            )
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.MODEL_ERROR, ErrorSeverity.HIGH,
                context={'method': 'predict'}
            )
            
            return EnsemblePrediction(
                signal=PredictionSignal.HOLD,
                confidence=0.0,
                individual_predictions={},
                model_weights=self.model_weights,
                features_used=[]
            )
    
    def get_model_performance_summary(self) -> Dict[str, Dict]:
        """Get performance summary for all models"""
        summary = {}
        
        for name, model in self.models.items():
            if model.is_trained and model.performance:
                summary[name] = {
                    'accuracy': model.performance.accuracy,
                    'weight': self.model_weights[name],
                    'trained': True
                }
            else:
                summary[name] = {
                    'accuracy': 0.0,
                    'weight': self.model_weights[name],
                    'trained': False
                }
        
        return summary
    
    def save_models(self, filepath: str):
        """Save trained models to file"""
        try:
            save_data = {
                'model_weights': self.model_weights,
                'is_trained': self.is_trained,
                'models': {}
            }
            
            # Save individual models (excluding LSTM which needs special handling)
            for name, model in self.models.items():
                if model.is_trained and name != 'lstm':
                    save_data['models'][name] = {
                        'model': model.model,
                        'scaler': model.scaler,
                        'feature_names': model.feature_names,
                        'performance': model.performance
                    }
            
            with open(filepath, 'wb') as f:
                pickle.dump(save_data, f)
                
            # Save LSTM model separately if trained
            if self.models['lstm'].is_trained:
                lstm_path = filepath.replace('.pkl', '_lstm.h5')
                self.models['lstm'].model.save(lstm_path)
                
            self.logger.info(f"Models saved to {filepath}")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM,
                context={'filepath': filepath}
            )
    
    def load_models(self, filepath: str):
        """Load trained models from file"""
        try:
            with open(filepath, 'rb') as f:
                save_data = pickle.load(f)
            
            self.model_weights = save_data['model_weights']
            self.is_trained = save_data['is_trained']
            
            # Load individual models
            for name, model_data in save_data['models'].items():
                if name in self.models:
                    self.models[name].model = model_data['model']
                    self.models[name].scaler = model_data['scaler']
                    self.models[name].feature_names = model_data['feature_names']
                    self.models[name].performance = model_data['performance']
                    self.models[name].is_trained = True
            
            # Load LSTM model separately if exists
            lstm_path = filepath.replace('.pkl', '_lstm.h5')
            try:
                self.models['lstm'].model = tf.keras.models.load_model(lstm_path)
                self.models['lstm'].is_trained = True
            except:
                pass  # LSTM model not found or couldn't load
                
            self.logger.info(f"Models loaded from {filepath}")
            
        except Exception as e:
            error_handler.handle_error(
                e, ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM,
                context={'filepath': filepath}
            )


# Global ensemble predictor instance
ensemble_predictor = EnsemblePredictor()