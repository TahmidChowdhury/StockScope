import pandas as pd
import numpy as np
import yfinance as yf
import talib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

class InvestmentAdvisor:
    def __init__(self, symbol=None):
        self.symbol = symbol
        self.data = None
        self.technical_indicators = {}
        self.risk_metrics = {}
        self.prediction_model = None
        self.scaler = StandardScaler()
    
    def analyze_investment_opportunity(self, ticker, sentiment_df):
        """
        Comprehensive investment analysis combining sentiment and technical analysis.
        
        Args:
            ticker (str): Stock ticker symbol
            sentiment_df (pd.DataFrame): Sentiment data from social media/news
            
        Returns:
            dict: Complete investment analysis with recommendation
        """
        try:
            self.symbol = ticker
            
            # Fetch stock data
            if not self.fetch_data():
                return {"ticker": ticker, "error": "Could not fetch stock data"}
            
            # Calculate sentiment metrics
            sentiment_metrics = self._analyze_sentiment_data(sentiment_df)
            
            # Calculate technical indicators
            technical_metrics = self._calculate_technical_metrics()
            
            # Calculate risk metrics
            risk_metrics = self._calculate_investment_risk()
            
            # Generate overall recommendation
            recommendation = self._generate_investment_recommendation(
                sentiment_metrics, technical_metrics, risk_metrics
            )
            
            return {
                "ticker": ticker,
                "recommendation": recommendation,
                "confidence": recommendation.get("confidence", 0.5),
                "risk_level": self._determine_risk_level(risk_metrics),
                "metrics": {
                    **sentiment_metrics,
                    **technical_metrics,
                    **risk_metrics
                }
            }
            
        except Exception as e:
            return {"ticker": ticker, "error": f"Analysis failed: {str(e)}"}
    
    def _analyze_sentiment_data(self, df):
        """Analyze sentiment data for investment insights."""
        if df.empty:
            return {"sentiment_score": 0, "sentiment_trend": 0, "volume_trend": 0}
        
        # Overall sentiment score
        sentiment_score = df['compound'].mean()
        
        # Sentiment trend (recent vs older)
        df_sorted = df.sort_values('created_dt')
        if len(df_sorted) >= 10:
            recent_sentiment = df_sorted.tail(len(df_sorted)//3)['compound'].mean()
            older_sentiment = df_sorted.head(len(df_sorted)//3)['compound'].mean()
            sentiment_trend = recent_sentiment - older_sentiment
        else:
            sentiment_trend = 0
        
        # Volume trend (posting activity)
        df['date'] = pd.to_datetime(df['created_dt']).dt.date
        daily_counts = df.groupby('date').size()
        if len(daily_counts) >= 3:
            recent_volume = daily_counts.tail(len(daily_counts)//3).mean()
            older_volume = daily_counts.head(len(daily_counts)//3).mean()
            volume_trend = (recent_volume - older_volume) / max(older_volume, 1)
        else:
            volume_trend = 0
        
        return {
            "sentiment_score": sentiment_score,
            "sentiment_trend": sentiment_trend,
            "volume_trend": volume_trend,
            "total_posts": len(df),
            "positive_ratio": len(df[df['compound'] > 0.1]) / len(df) if len(df) > 0 else 0
        }
    
    def _calculate_technical_metrics(self):
        """Calculate key technical analysis metrics."""
        if self.data is None or len(self.data) < 50:
            return {}
        
        close = self.data['Close'].values
        high = self.data['High'].values
        low = self.data['Low'].values
        volume = self.data['Volume'].values
        
        # Calculate indicators
        sma_20 = talib.SMA(close, timeperiod=20)
        sma_50 = talib.SMA(close, timeperiod=50)
        rsi = talib.RSI(close, timeperiod=14)
        macd, macd_signal, _ = talib.MACD(close)
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20)
        
        # Current values
        current_price = close[-1]
        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50
        current_macd = macd[-1] if not np.isnan(macd[-1]) else 0
        current_macd_signal = macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0
        
        # Price momentum
        price_change_5d = (close[-1] - close[-6]) / close[-6] if len(close) >= 6 else 0
        price_change_20d = (close[-1] - close[-21]) / close[-21] if len(close) >= 21 else 0
        
        # Moving average signals
        ma_signal = 0
        if not np.isnan(sma_20[-1]) and not np.isnan(sma_50[-1]):
            if current_price > sma_20[-1] > sma_50[-1]:
                ma_signal = 1  # Bullish
            elif current_price < sma_20[-1] < sma_50[-1]:
                ma_signal = -1  # Bearish
        
        # Bollinger Band position
        bb_position = 0.5  # Default to middle
        if not np.isnan(bb_upper[-1]) and not np.isnan(bb_lower[-1]):
            bb_position = (current_price - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
        
        return {
            "price_momentum": (price_change_5d + price_change_20d) / 2,
            "rsi": current_rsi,
            "macd_signal": 1 if current_macd > current_macd_signal else -1,
            "ma_signal": ma_signal,
            "bb_position": bb_position,
            "support_resistance": {
                "support": float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else current_price * 0.95,
                "resistance": float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else current_price * 1.05
            }
        }
    
    def _calculate_investment_risk(self):
        """Calculate investment risk metrics."""
        if self.data is None or len(self.data) < 30:
            return {"volatility": 0.3, "beta": 1.0}
        
        returns = self.data['Close'].pct_change().dropna()
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)
        
        # Simple beta approximation (vs market average volatility)
        market_vol = 0.16  # Approximate S&P 500 volatility
        beta = volatility / market_vol
        
        # Sharpe ratio approximation
        avg_return = returns.mean() * 252
        risk_free_rate = 0.02  # Approximate risk-free rate
        sharpe = (avg_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        return {
            "volatility": volatility,
            "beta": beta,
            "sharpe_ratio": sharpe
        }
    
    def _generate_investment_recommendation(self, sentiment_metrics, technical_metrics, risk_metrics):
        """Generate final investment recommendation."""
        scores = []
        reasoning = []
        
        # Sentiment analysis (30% weight)
        sentiment_score = sentiment_metrics.get("sentiment_score", 0)
        if sentiment_score > 0.2:
            scores.append(0.8)
            reasoning.append("Strong positive sentiment detected")
        elif sentiment_score > 0.05:
            scores.append(0.6)
            reasoning.append("Moderately positive sentiment")
        elif sentiment_score < -0.2:
            scores.append(0.2)
            reasoning.append("Negative sentiment concerns")
        else:
            scores.append(0.5)
            reasoning.append("Neutral sentiment environment")
        
        # Technical analysis (40% weight)
        technical_score = 0.5
        
        # RSI component
        rsi = technical_metrics.get("rsi", 50)
        if 30 <= rsi <= 70:
            technical_score += 0.1
            reasoning.append("RSI in healthy range")
        elif rsi < 30:
            technical_score += 0.2
            reasoning.append("RSI shows oversold conditions (buying opportunity)")
        else:
            technical_score -= 0.1
            reasoning.append("RSI shows overbought conditions")
        
        # Moving average component
        ma_signal = technical_metrics.get("ma_signal", 0)
        if ma_signal == 1:
            technical_score += 0.2
            reasoning.append("Price above key moving averages")
        elif ma_signal == -1:
            technical_score -= 0.2
            reasoning.append("Price below key moving averages")
        
        # MACD component
        macd_signal = technical_metrics.get("macd_signal", 0)
        if macd_signal == 1:
            technical_score += 0.1
            reasoning.append("MACD shows bullish momentum")
        else:
            technical_score -= 0.1
            reasoning.append("MACD shows bearish momentum")
        
        # Price momentum
        momentum = technical_metrics.get("price_momentum", 0)
        if momentum > 0.05:
            technical_score += 0.1
            reasoning.append("Strong upward price momentum")
        elif momentum < -0.05:
            technical_score -= 0.1
            reasoning.append("Downward price momentum")
        
        scores.append(max(0, min(1, technical_score)))
        
        # Risk analysis (30% weight)
        volatility = risk_metrics.get("volatility", 0.3)
        sharpe = risk_metrics.get("sharpe_ratio", 0)
        
        risk_score = 0.5
        if volatility < 0.2:
            risk_score += 0.2
            reasoning.append("Low volatility (stable investment)")
        elif volatility > 0.4:
            risk_score -= 0.2
            reasoning.append("High volatility (risky investment)")
        
        if sharpe > 0.5:
            risk_score += 0.2
            reasoning.append("Good risk-adjusted returns")
        elif sharpe < 0:
            risk_score -= 0.2
            reasoning.append("Poor risk-adjusted returns")
        
        scores.append(max(0, min(1, risk_score)))
        
        # Calculate weighted final score
        weights = [0.3, 0.4, 0.3]  # sentiment, technical, risk
        final_score = sum(score * weight for score, weight in zip(scores, weights))
        
        # Determine action and confidence
        if final_score >= 0.7:
            action = "STRONG BUY"
            color = "🟢"
            confidence = 0.8 + (final_score - 0.7) * 0.5
        elif final_score >= 0.6:
            action = "BUY"
            color = "🟢"
            confidence = 0.6 + (final_score - 0.6) * 0.2
        elif final_score >= 0.4:
            action = "HOLD"
            color = "🟡"
            confidence = 0.5
        elif final_score >= 0.3:
            action = "WEAK SELL"
            color = "🟠"
            confidence = 0.6 + (0.4 - final_score) * 0.2
        else:
            action = "SELL"
            color = "🔴"
            confidence = 0.8 + (0.3 - final_score) * 0.5
        
        return {
            "action": action,
            "score": final_score,
            "color": color,
            "confidence": min(0.95, confidence),
            "reasoning": reasoning
        }
    
    def _determine_risk_level(self, risk_metrics):
        """Determine overall risk level."""
        volatility = risk_metrics.get("volatility", 0.3)
        beta = risk_metrics.get("beta", 1.0)
        
        if volatility > 0.4 or beta > 1.5:
            return "HIGH"
        elif volatility < 0.2 and beta < 0.8:
            return "LOW"
        else:
            return "MEDIUM"
        
    def fetch_data(self, period="2y"):
        """Fetch stock data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(period=period)
            return True
        except Exception as e:
            print(f"Error fetching data for {self.symbol}: {e}")
            return False
    
    def calculate_technical_indicators(self):
        """Calculate comprehensive technical indicators"""
        if self.data is None or len(self.data) < 50:
            return {}
        
        close = self.data['Close'].values
        high = self.data['High'].values
        low = self.data['Low'].values
        volume = self.data['Volume'].values
        
        # Trend Indicators
        self.technical_indicators['SMA_20'] = talib.SMA(close, timeperiod=20)
        self.technical_indicators['SMA_50'] = talib.SMA(close, timeperiod=50)
        self.technical_indicators['EMA_12'] = talib.EMA(close, timeperiod=12)
        self.technical_indicators['EMA_26'] = talib.EMA(close, timeperiod=26)
        
        # MACD
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        self.technical_indicators['MACD'] = macd
        self.technical_indicators['MACD_Signal'] = signal
        self.technical_indicators['MACD_Hist'] = hist
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        self.technical_indicators['BB_Upper'] = bb_upper
        self.technical_indicators['BB_Middle'] = bb_middle
        self.technical_indicators['BB_Lower'] = bb_lower
        
        # Momentum Indicators
        self.technical_indicators['RSI'] = talib.RSI(close, timeperiod=14)
        self.technical_indicators['Stoch_K'], self.technical_indicators['Stoch_D'] = talib.STOCH(high, low, close)
        self.technical_indicators['Williams_R'] = talib.WILLR(high, low, close, timeperiod=14)
        
        # Volume Indicators
        self.technical_indicators['OBV'] = talib.OBV(close, volume)
        self.technical_indicators['AD'] = talib.AD(high, low, close, volume)
        
        # Volatility Indicators
        self.technical_indicators['ATR'] = talib.ATR(high, low, close, timeperiod=14)
        
        return self.technical_indicators
    
    def calculate_risk_metrics(self):
        """Calculate comprehensive risk metrics"""
        if self.data is None:
            return {}
        
        returns = self.data['Close'].pct_change().dropna()
        
        # Basic Risk Metrics
        self.risk_metrics['volatility'] = returns.std() * np.sqrt(252)  # Annualized
        self.risk_metrics['sharpe_ratio'] = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
        
        # Drawdown Analysis
        cum_returns = (1 + returns).cumprod()
        rolling_max = cum_returns.expanding().max()
        drawdown = (cum_returns - rolling_max) / rolling_max
        self.risk_metrics['max_drawdown'] = drawdown.min()
        self.risk_metrics['current_drawdown'] = drawdown.iloc[-1]
        
        # Value at Risk (VaR)
        self.risk_metrics['var_95'] = np.percentile(returns, 5)
        self.risk_metrics['var_99'] = np.percentile(returns, 1)
        
        # Beta calculation (vs SPY)
        try:
            spy = yf.download('SPY', period='1y', progress=False)['Close']
            spy_returns = spy.pct_change().dropna()
            
            # Align dates
            common_dates = returns.index.intersection(spy_returns.index)
            if len(common_dates) > 50:
                aligned_returns = returns.loc[common_dates]
                aligned_spy = spy_returns.loc[common_dates]
                
                covariance = np.cov(aligned_returns, aligned_spy)[0][1]
                spy_variance = np.var(aligned_spy)
                self.risk_metrics['beta'] = covariance / spy_variance if spy_variance != 0 else 1.0
            else:
                self.risk_metrics['beta'] = 1.0
        except:
            self.risk_metrics['beta'] = 1.0
        
        return self.risk_metrics
    
    def prepare_ml_features(self):
        """Prepare features for machine learning model"""
        if self.data is None:
            return None, None
        
        # Calculate technical indicators first
        self.calculate_technical_indicators()
        
        # Create feature dataframe
        features_df = pd.DataFrame(index=self.data.index)
        
        # Price features
        features_df['close'] = self.data['Close']
        features_df['volume'] = self.data['Volume']
        features_df['returns'] = self.data['Close'].pct_change()
        
        # Technical indicators as features
        for name, values in self.technical_indicators.items():
            if values is not None:
                features_df[name] = values
        
        # Additional derived features
        features_df['price_sma20_ratio'] = features_df['close'] / features_df['SMA_20']
        features_df['volume_sma'] = features_df['volume'].rolling(20).mean()
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma']
        
        # Target variable (next day return)
        features_df['target'] = features_df['returns'].shift(-1)
        
        # Drop NaN values
        features_df = features_df.dropna()
        
        if len(features_df) < 50:
            return None, None
        
        # Separate features and target
        feature_cols = [col for col in features_df.columns if col != 'target']
        X = features_df[feature_cols]
        y = features_df['target']
        
        return X, y
    
    def train_prediction_model(self):
        """Train ML model for price prediction"""
        X, y = self.prepare_ml_features()
        
        if X is None or len(X) < 50:
            return False
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.prediction_model = RandomForestRegressor(
            n_estimators=100, 
            random_state=42,
            max_depth=10,
            min_samples_split=5
        )
        
        self.prediction_model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = self.prediction_model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        return {'mse': mse, 'r2': r2, 'model_trained': True}
    
    def get_investment_recommendation(self):
        """Generate comprehensive investment recommendation"""
        if self.data is None:
            return {"error": "No data available"}
        
        # Calculate all metrics
        self.calculate_technical_indicators()
        self.calculate_risk_metrics()
        
        recommendation = {
            'symbol': self.symbol,
            'current_price': float(self.data['Close'].iloc[-1]),
            'recommendation': 'HOLD',  # Default
            'confidence': 0.5,
            'signals': [],
            'risk_level': 'Medium',
            'target_price': None,
            'stop_loss': None
        }
        
        # Technical Analysis Signals
        signals = []
        signal_strength = 0
        
        # Moving Average Signals
        current_price = self.data['Close'].iloc[-1]
        sma_20 = self.technical_indicators['SMA_20'][-1] if 'SMA_20' in self.technical_indicators else current_price
        sma_50 = self.technical_indicators['SMA_50'][-1] if 'SMA_50' in self.technical_indicators else current_price
        
        if current_price > sma_20 > sma_50:
            signals.append("Bullish: Price above MA20 and MA50")
            signal_strength += 1
        elif current_price < sma_20 < sma_50:
            signals.append("Bearish: Price below MA20 and MA50")
            signal_strength -= 1
        
        # RSI Signal
        if 'RSI' in self.technical_indicators:
            rsi = self.technical_indicators['RSI'][-1]
            if rsi > 70:
                signals.append(f"Overbought: RSI = {rsi:.1f}")
                signal_strength -= 0.5
            elif rsi < 30:
                signals.append(f"Oversold: RSI = {rsi:.1f}")
                signal_strength += 0.5
        
        # MACD Signal
        if 'MACD' in self.technical_indicators and 'MACD_Signal' in self.technical_indicators:
            macd = self.technical_indicators['MACD'][-1]
            macd_signal = self.technical_indicators['MACD_Signal'][-1]
            if macd > macd_signal:
                signals.append("Bullish: MACD above signal line")
                signal_strength += 0.5
            else:
                signals.append("Bearish: MACD below signal line")
                signal_strength -= 0.5
        
        # Bollinger Bands Signal
        if all(k in self.technical_indicators for k in ['BB_Upper', 'BB_Lower']):
            bb_upper = self.technical_indicators['BB_Upper'][-1]
            bb_lower = self.technical_indicators['BB_Lower'][-1]
            
            if current_price > bb_upper:
                signals.append("Overbought: Price above upper Bollinger Band")
                signal_strength -= 0.5
            elif current_price < bb_lower:
                signals.append("Oversold: Price below lower Bollinger Band")
                signal_strength += 0.5
        
        # Determine recommendation based on signal strength
        if signal_strength >= 1.5:
            recommendation['recommendation'] = 'BUY'
            recommendation['confidence'] = min(0.9, 0.5 + signal_strength * 0.2)
        elif signal_strength <= -1.5:
            recommendation['recommendation'] = 'SELL'
            recommendation['confidence'] = min(0.9, 0.5 + abs(signal_strength) * 0.2)
        else:
            recommendation['recommendation'] = 'HOLD'
            recommendation['confidence'] = 0.5
        
        # Risk Assessment
        volatility = self.risk_metrics.get('volatility', 0.3)
        if volatility > 0.4:
            recommendation['risk_level'] = 'High'
        elif volatility < 0.2:
            recommendation['risk_level'] = 'Low'
        else:
            recommendation['risk_level'] = 'Medium'
        
        # Price targets (simple calculation)
        atr = self.technical_indicators.get('ATR', [current_price * 0.02])[-1]
        if recommendation['recommendation'] == 'BUY':
            recommendation['target_price'] = current_price + (2 * atr)
            recommendation['stop_loss'] = current_price - atr
        elif recommendation['recommendation'] == 'SELL':
            recommendation['target_price'] = current_price - (2 * atr)
            recommendation['stop_loss'] = current_price + atr
        
        recommendation['signals'] = signals
        recommendation['technical_indicators'] = {
            k: float(v[-1]) if hasattr(v, '__getitem__') and len(v) > 0 else float(v) 
            for k, v in self.technical_indicators.items() 
            if v is not None and not np.isnan(v[-1] if hasattr(v, '__getitem__') else v)
        }
        recommendation['risk_metrics'] = self.risk_metrics
        
        return recommendation
    
    def get_portfolio_suggestion(self, portfolio_value, risk_tolerance='medium'):
        """Suggest position size based on portfolio value and risk tolerance"""
        recommendation = self.get_investment_recommendation()
        
        if recommendation.get('error'):
            return recommendation
        
        # Risk-based position sizing
        risk_multipliers = {
            'low': 0.02,      # 2% of portfolio
            'medium': 0.05,   # 5% of portfolio  
            'high': 0.10      # 10% of portfolio
        }
        
        base_allocation = risk_multipliers.get(risk_tolerance, 0.05)
        
        # Adjust based on recommendation confidence
        confidence = recommendation['confidence']
        adjusted_allocation = base_allocation * confidence
        
        # Further adjust based on risk level
        if recommendation['risk_level'] == 'High':
            adjusted_allocation *= 0.7
        elif recommendation['risk_level'] == 'Low':
            adjusted_allocation *= 1.2
        
        suggested_investment = portfolio_value * adjusted_allocation
        current_price = recommendation['current_price']
        suggested_shares = int(suggested_investment / current_price)
        
        return {
            **recommendation,
            'portfolio_allocation': f"{adjusted_allocation*100:.1f}%",
            'suggested_investment': suggested_investment,
            'suggested_shares': suggested_shares,
            'risk_tolerance': risk_tolerance
        }