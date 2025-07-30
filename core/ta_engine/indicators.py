import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators"""
    # RSI settings
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    
    # MACD settings
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands settings
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Moving averages
    sma_periods: List[int] = None
    ema_periods: List[int] = None
    
    # Volume indicators
    volume_ma_period: int = 20
    
    # Divergence settings
    divergence_lookback: int = 20
    divergence_threshold: float = 0.02
    
    def __post_init__(self):
        if self.sma_periods is None:
            self.sma_periods = [20, 50, 200]
        if self.ema_periods is None:
            self.ema_periods = [12, 26]

class TechnicalIndicatorEngine:
    """Comprehensive technical indicator engine with divergence detection"""
    
    def __init__(self, config: IndicatorConfig = None):
        self.config = config or IndicatorConfig()
        self.logger = logger
        
    def calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate all technical indicators"""
        # Validate required columns (case-insensitive)
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        data_cols_lower = [col.lower() for col in data.columns]
        
        missing_cols = [col for col in required_cols if col not in data_cols_lower]
        if missing_cols:
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Normalize column names to lowercase for consistency
        data_normalized = data.copy()
        data_normalized.columns = data_normalized.columns.str.lower()
        
        self.logger.info(f"Calculating indicators for {len(data)} data points")
        
        # Calculate all indicator categories
        momentum_indicators = self._calculate_momentum_indicators(data_normalized)
        trend_indicators = self._calculate_trend_indicators(data_normalized)
        volume_indicators = self._calculate_volume_indicators(data_normalized)
        volatility_indicators = self._calculate_volatility_indicators(data_normalized)
        divergence_indicators = self._calculate_divergence_indicators(data_normalized)
        
        # Combine all indicators
        all_indicators = {}
        all_indicators.update(momentum_indicators)
        all_indicators.update(trend_indicators)
        all_indicators.update(volume_indicators)
        all_indicators.update(volatility_indicators)
        all_indicators.update(divergence_indicators)
        
        # Add original data columns
        all_indicators.update({
            'Open': data_normalized['open'],
            'High': data_normalized['high'],
            'Low': data_normalized['low'],
            'Close': data_normalized['close'],
            'Volume': data_normalized['volume']
        })
        
        self.logger.info(f"Calculated {len(all_indicators)} indicators")
        return all_indicators
    
    def _calculate_momentum_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate momentum-based indicators"""
        results = {}
        
        # RSI
        try:
            rsi = vbt.RSI.run(data['close'], window=self.config.rsi_period).rsi
            results['RSI'] = rsi
            self.logger.debug(f"RSI calculated: range {rsi.min():.2f} to {rsi.max():.2f}")
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            results['RSI'] = pd.Series(dtype=float)
        
        # MACD
        try:
            macd = vbt.MACD.run(
                data['close'], 
                fast_window=self.config.macd_fast,
                slow_window=self.config.macd_slow,
                signal_window=self.config.macd_signal
            )
            results['MACD'] = macd.macd
            results['MACD_Signal'] = macd.signal
            # Calculate histogram manually since vectorbt doesn't provide it
            results['MACD_Histogram'] = macd.macd - macd.signal
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            results['MACD'] = pd.Series(dtype=float)
            results['MACD_Signal'] = pd.Series(dtype=float)
            results['MACD_Histogram'] = pd.Series(dtype=float)
        
        # Stochastic (manual calculation since vectorbt doesn't have STOCH)
        try:
            stoch_k, stoch_d = self._calculate_stochastic(data['high'], data['low'], data['close'])
            results['Stoch_K'] = stoch_k
            results['Stoch_D'] = stoch_d
        except Exception as e:
            self.logger.error(f"Error calculating Stochastic: {e}")
            results['Stoch_K'] = pd.Series(dtype=float)
            results['Stoch_D'] = pd.Series(dtype=float)
        
        # Williams %R (manual calculation)
        try:
            williams_r = self._calculate_williams_r(data['high'], data['low'], data['close'])
            results['Williams_R'] = williams_r
        except Exception as e:
            self.logger.error(f"Error calculating Williams %R: {e}")
            results['Williams_R'] = pd.Series(dtype=float)
        
        return results
    
    def _calculate_trend_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate trend-based indicators"""
        results = {}
        
        # Simple Moving Averages
        for period in self.config.sma_periods:
            try:
                sma = data['close'].rolling(window=period).mean()
                results[f'SMA_{period}'] = sma
            except Exception as e:
                self.logger.error(f"Error calculating SMA {period}: {e}")
                results[f'SMA_{period}'] = pd.Series(dtype=float)
        
        # Exponential Moving Averages
        for period in self.config.ema_periods:
            try:
                ema = data['close'].ewm(span=period).mean()
                results[f'EMA_{period}'] = ema
            except Exception as e:
                self.logger.error(f"Error calculating EMA {period}: {e}")
                results[f'EMA_{period}'] = pd.Series(dtype=float)
        
        # ADX (Average Directional Index) - manual calculation
        try:
            adx, plus_di, minus_di = self._calculate_adx(data['high'], data['low'], data['close'])
            results['ADX'] = adx
            results['ADX_Plus'] = plus_di
            results['ADX_Minus'] = minus_di
        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            results['ADX'] = pd.Series(dtype=float)
            results['ADX_Plus'] = pd.Series(dtype=float)
            results['ADX_Minus'] = pd.Series(dtype=float)
        
        # Parabolic SAR - manual calculation
        try:
            sar = self._calculate_psar(data['high'], data['low'], data['close'])
            results['PSAR'] = sar
        except Exception as e:
            self.logger.error(f"Error calculating Parabolic SAR: {e}")
            results['PSAR'] = pd.Series(dtype=float)
        
        return results
    
    def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate volume-based indicators"""
        results = {}
        
        # Volume Moving Average
        try:
            volume_ma = data['volume'].rolling(window=self.config.volume_ma_period).mean()
            results['Volume_MA'] = volume_ma
            results['Volume_Ratio'] = data['volume'] / volume_ma
        except Exception as e:
            self.logger.error(f"Error calculating volume indicators: {e}")
            results['Volume_MA'] = pd.Series(dtype=float)
            results['Volume_Ratio'] = pd.Series(dtype=float)
        
        # On Balance Volume (OBV) - manual calculation
        try:
            obv = self._calculate_obv(data['close'], data['volume'])
            results['OBV'] = obv
        except Exception as e:
            self.logger.error(f"Error calculating OBV: {e}")
            results['OBV'] = pd.Series(dtype=float)
        
        # Volume Price Trend (VPT) - manual calculation
        try:
            vpt = self._calculate_vpt(data['close'], data['volume'])
            results['VPT'] = vpt
        except Exception as e:
            self.logger.error(f"Error calculating VPT: {e}")
            results['VPT'] = pd.Series(dtype=float)
        
        return results
    
    def _calculate_volatility_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate volatility-based indicators"""
        results = {}
        
        # Bollinger Bands
        try:
            bb = vbt.BBANDS.run(
                data['close'], 
                window=self.config.bb_period, 
                alpha=self.config.bb_std
            )
            results['BB_Upper'] = bb.upper
            results['BB_Middle'] = bb.middle
            results['BB_Lower'] = bb.lower
            results['BB_Width'] = (bb.upper - bb.lower) / bb.middle
            results['BB_Position'] = (data['close'] - bb.lower) / (bb.upper - bb.lower)
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            results['BB_Upper'] = pd.Series(dtype=float)
            results['BB_Middle'] = pd.Series(dtype=float)
            results['BB_Lower'] = pd.Series(dtype=float)
            results['BB_Width'] = pd.Series(dtype=float)
            results['BB_Position'] = pd.Series(dtype=float)
        
        # Average True Range (ATR) - manual calculation
        try:
            atr = self._calculate_atr(data['high'], data['low'], data['close'])
            results['ATR'] = atr
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            results['ATR'] = pd.Series(dtype=float)
        
        # Keltner Channels - manual calculation
        try:
            kc_upper, kc_middle, kc_lower = self._calculate_keltner_channels(data['high'], data['low'], data['close'])
            results['KC_Upper'] = kc_upper
            results['KC_Middle'] = kc_middle
            results['KC_Lower'] = kc_lower
        except Exception as e:
            self.logger.error(f"Error calculating Keltner Channels: {e}")
            results['KC_Upper'] = pd.Series(dtype=float)
            results['KC_Middle'] = pd.Series(dtype=float)
            results['KC_Lower'] = pd.Series(dtype=float)
        
        return results
    
    def _calculate_divergence_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate divergence indicators"""
        results = {}
        
        # RSI Divergence
        if 'RSI' in data.columns or 'RSI' in self._calculate_momentum_indicators(data):
            rsi = data.get('RSI', self._calculate_momentum_indicators(data)['RSI'])
            results.update(self._detect_rsi_divergence(data, rsi))
        
        # MACD Divergence
        if 'MACD' in data.columns or 'MACD' in self._calculate_momentum_indicators(data):
            macd = data.get('MACD', self._calculate_momentum_indicators(data)['MACD'])
            results.update(self._detect_macd_divergence(data, macd))
        
        return results
    
    def _detect_rsi_divergence(self, data: pd.DataFrame, rsi: pd.Series) -> Dict[str, pd.Series]:
        """Detect RSI divergence patterns"""
        results = {}
        
        # Initialize divergence signals
        bullish_divergence = pd.Series(0, index=data.index)
        bearish_divergence = pd.Series(0, index=data.index)
        hidden_bullish_divergence = pd.Series(0, index=data.index)
        hidden_bearish_divergence = pd.Series(0, index=data.index)
        
        lookback = self.config.divergence_lookback
        threshold = self.config.divergence_threshold
        
        for i in range(lookback, len(data)):
            # Find pivot points
            price_pivot_low = self._find_pivot_low(data['low'], i, lookback//2)
            price_pivot_high = self._find_pivot_high(data['high'], i, lookback//2)
            rsi_pivot_low = self._find_pivot_low(rsi, i, lookback//2)
            rsi_pivot_high = self._find_pivot_high(rsi, i, lookback//2)
            
            if price_pivot_low and rsi_pivot_low:
                # Regular bullish divergence: price makes lower low, RSI makes higher low
                if (data['low'].iloc[i] < data['low'].iloc[price_pivot_low] and 
                    rsi.iloc[i] > rsi.iloc[rsi_pivot_low] + threshold):
                    bullish_divergence.iloc[i] = 1
                
                # Hidden bullish divergence: price makes higher low, RSI makes lower low
                elif (data['low'].iloc[i] > data['low'].iloc[price_pivot_low] and 
                      rsi.iloc[i] < rsi.iloc[rsi_pivot_low] - threshold):
                    hidden_bullish_divergence.iloc[i] = 1
            
            if price_pivot_high and rsi_pivot_high:
                # Regular bearish divergence: price makes higher high, RSI makes lower high
                if (data['high'].iloc[i] > data['high'].iloc[price_pivot_high] and 
                    rsi.iloc[i] < rsi.iloc[rsi_pivot_high] - threshold):
                    bearish_divergence.iloc[i] = 1
                
                # Hidden bearish divergence: price makes lower high, RSI makes higher high
                elif (data['high'].iloc[i] < data['high'].iloc[price_pivot_high] and 
                      rsi.iloc[i] > rsi.iloc[rsi_pivot_high] + threshold):
                    hidden_bearish_divergence.iloc[i] = 1
        
        results['RSI_Bullish_Divergence'] = bullish_divergence
        results['RSI_Bearish_Divergence'] = bearish_divergence
        results['RSI_Hidden_Bullish_Divergence'] = hidden_bullish_divergence
        results['RSI_Hidden_Bearish_Divergence'] = hidden_bearish_divergence
        
        return results
    
    def _detect_macd_divergence(self, data: pd.DataFrame, macd: pd.Series) -> Dict[str, pd.Series]:
        """Detect MACD divergence patterns"""
        results = {}
        
        # Initialize divergence signals
        bullish_divergence = pd.Series(0, index=data.index)
        bearish_divergence = pd.Series(0, index=data.index)
        
        lookback = self.config.divergence_lookback
        threshold = self.config.divergence_threshold
        
        for i in range(lookback, len(data)):
            # Find pivot points
            price_pivot_low = self._find_pivot_low(data['low'], i, lookback//2)
            price_pivot_high = self._find_pivot_high(data['high'], i, lookback//2)
            macd_pivot_low = self._find_pivot_low(macd, i, lookback//2)
            macd_pivot_high = self._find_pivot_high(macd, i, lookback//2)
            
            if price_pivot_low and macd_pivot_low:
                # Bullish divergence: price makes lower low, MACD makes higher low
                if (data['low'].iloc[i] < data['low'].iloc[price_pivot_low] and 
                    macd.iloc[i] > macd.iloc[macd_pivot_low] + threshold):
                    bullish_divergence.iloc[i] = 1
            
            if price_pivot_high and macd_pivot_high:
                # Bearish divergence: price makes higher high, MACD makes lower high
                if (data['high'].iloc[i] > data['high'].iloc[price_pivot_high] and 
                    macd.iloc[i] < macd.iloc[macd_pivot_high] - threshold):
                    bearish_divergence.iloc[i] = 1
        
        results['MACD_Bullish_Divergence'] = bullish_divergence
        results['MACD_Bearish_Divergence'] = bearish_divergence
        
        return results
    
    def get_signal_strength(self, indicators: Dict[str, pd.Series], signal_type: str) -> float:
        """Calculate signal strength based on multiple indicators"""
        strength = 0.0
        count = 0
        
        if signal_type == 'bullish':
            # RSI oversold
            if 'RSI' in indicators and indicators['RSI'].iloc[-1] < self.config.rsi_oversold:
                strength += 0.2
                count += 1
            
            # MACD bullish crossover
            if 'MACD' in indicators and 'MACD_Signal' in indicators:
                if (indicators['MACD'].iloc[-1] > indicators['MACD_Signal'].iloc[-1] and
                    indicators['MACD'].iloc[-2] <= indicators['MACD_Signal'].iloc[-2]):
                    strength += 0.3
                    count += 1
            
            # Price above moving averages
            for period in self.config.sma_periods:
                sma_key = f'SMA_{period}'
                if sma_key in indicators and indicators['close'].iloc[-1] > indicators[sma_key].iloc[-1]:
                    strength += 0.1
                    count += 1
            
            # Bullish divergence
            if 'RSI_Bullish_Divergence' in indicators and indicators['RSI_Bullish_Divergence'].iloc[-1] == 1:
                strength += 0.4
                count += 1
        
        elif signal_type == 'bearish':
            # RSI overbought
            if 'RSI' in indicators and indicators['RSI'].iloc[-1] > self.config.rsi_overbought:
                strength += 0.2
                count += 1
            
            # MACD bearish crossover
            if 'MACD' in indicators and 'MACD_Signal' in indicators:
                if (indicators['MACD'].iloc[-1] < indicators['MACD_Signal'].iloc[-1] and
                    indicators['MACD'].iloc[-2] >= indicators['MACD_Signal'].iloc[-2]):
                    strength += 0.3
                    count += 1
            
            # Price below moving averages
            for period in self.config.sma_periods:
                sma_key = f'SMA_{period}'
                if sma_key in indicators and indicators['close'].iloc[-1] < indicators[sma_key].iloc[-1]:
                    strength += 0.1
                    count += 1
            
            # Bearish divergence
            if 'RSI_Bearish_Divergence' in indicators and indicators['RSI_Bearish_Divergence'].iloc[-1] == 1:
                strength += 0.4
                count += 1
        
        return strength / max(count, 1) if count > 0 else 0.0 
    
    def _calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent, d_percent
    
    def _calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return williams_r
    
    def _calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Average Directional Index (ADX)"""
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        dm_plus = high - high.shift(1)
        dm_minus = low.shift(1) - low
        
        dm_plus = dm_plus.where(dm_plus > dm_minus, 0)
        dm_plus = dm_plus.where(dm_plus > 0, 0)
        
        dm_minus = dm_minus.where(dm_minus > dm_plus, 0)
        dm_minus = dm_minus.where(dm_minus > 0, 0)
        
        # Smoothed values
        tr_smooth = tr.rolling(window=period).mean()
        dm_plus_smooth = dm_plus.rolling(window=period).mean()
        dm_minus_smooth = dm_minus.rolling(window=period).mean()
        
        # Directional Indicators
        di_plus = 100 * (dm_plus_smooth / tr_smooth)
        di_minus = 100 * (dm_minus_smooth / tr_smooth)
        
        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()
        
        return adx, di_plus, di_minus
    
    def _calculate_psar(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                       acceleration: float = 0.02, maximum: float = 0.2) -> pd.Series:
        """Calculate Parabolic SAR"""
        psar = pd.Series(index=close.index, dtype=float)
        af = pd.Series(index=close.index, dtype=float)  # Acceleration Factor
        ep = pd.Series(index=close.index, dtype=float)  # Extreme Point
        
        # Initialize
        psar.iloc[0] = low.iloc[0]
        af.iloc[0] = acceleration
        ep.iloc[0] = high.iloc[0]
        
        long_position = True
        
        for i in range(1, len(close)):
            if long_position:
                psar.iloc[i] = psar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - psar.iloc[i-1])
                
                if psar.iloc[i] > low.iloc[i]:
                    psar.iloc[i] = low.iloc[i]
                
                if close.iloc[i] > ep.iloc[i-1]:
                    ep.iloc[i] = close.iloc[i]
                    af.iloc[i] = min(af.iloc[i-1] + acceleration, maximum)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    af.iloc[i] = af.iloc[i-1]
                
                if close.iloc[i] < psar.iloc[i]:
                    long_position = False
                    psar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = close.iloc[i]
                    af.iloc[i] = acceleration
            else:
                psar.iloc[i] = psar.iloc[i-1] - af.iloc[i-1] * (psar.iloc[i-1] - ep.iloc[i-1])
                
                if psar.iloc[i] < high.iloc[i]:
                    psar.iloc[i] = high.iloc[i]
                
                if close.iloc[i] < ep.iloc[i-1]:
                    ep.iloc[i] = close.iloc[i]
                    af.iloc[i] = min(af.iloc[i-1] + acceleration, maximum)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    af.iloc[i] = af.iloc[i-1]
                
                if close.iloc[i] > psar.iloc[i]:
                    long_position = True
                    psar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = close.iloc[i]
                    af.iloc[i] = acceleration
        
        return psar
    
    def _calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On Balance Volume (OBV)"""
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def _calculate_vpt(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate Volume Price Trend (VPT)"""
        vpt = pd.Series(index=close.index, dtype=float)
        vpt.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            vpt.iloc[i] = vpt.iloc[i-1] + (close.iloc[i] - close.iloc[i-1]) / close.iloc[i-1] * volume.iloc[i]
        
        return vpt
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR)"""
        tr = pd.Series(index=close.index, dtype=float)
        tr.iloc[0] = 0 # No previous close on first day
        
        for i in range(1, len(close)):
            tr.iloc[i] = max(high.iloc[i] - low.iloc[i],
                             abs(high.iloc[i] - close.iloc[i-1]),
                             abs(low.iloc[i] - close.iloc[i-1]))
        
        return tr.rolling(window=period).mean()
    
    def _calculate_keltner_channels(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                                   kc_period: int = 20, kc_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Keltner Channels"""
        # Typical Price
        tp = (high + low + close) / 3
        
        # Middle Line (EMA of TP)
        kc_middle = tp.ewm(span=kc_period).mean()
        
        # True Range
        tr = pd.Series(index=close.index, dtype=float)
        tr.iloc[0] = 0 # No previous close on first day
        
        for i in range(1, len(close)):
            tr.iloc[i] = max(high.iloc[i] - low.iloc[i],
                             abs(high.iloc[i] - close.iloc[i-1]),
                             abs(low.iloc[i] - close.iloc[i-1]))
        
        # ATR (EMA of TR)
        atr = tr.ewm(span=kc_period).mean()
        
        # Upper and Lower Channels
        kc_upper = kc_middle + kc_std * atr
        kc_lower = kc_middle - kc_std * atr
        
        return kc_upper, kc_middle, kc_lower
    
    def _find_pivot_low(self, series: pd.Series, current_idx: int, window: int) -> Optional[int]:
        """Find the most recent pivot low within the window"""
        start_idx = max(0, current_idx - window)
        end_idx = current_idx
        
        if end_idx - start_idx < 3:
            return None
        
        # Get the window slice
        window_slice = series.iloc[start_idx:end_idx]
        
        # Check if the slice is empty or has NaN values
        if window_slice.empty or window_slice.isna().all():
            return None
        
        # Find the minimum in the window
        try:
            min_idx = window_slice.idxmin()
            min_idx_pos = series.index.get_loc(min_idx)
            
            # Check if it's a pivot (lower than neighbors)
            if (min_idx_pos > start_idx and min_idx_pos < end_idx - 1 and
                series.iloc[min_idx_pos] < series.iloc[min_idx_pos - 1] and
                series.iloc[min_idx_pos] < series.iloc[min_idx_pos + 1]):
                return min_idx_pos
        except (ValueError, KeyError):
            # Handle cases where idxmin() fails
            return None
        
        return None
    
    def _find_pivot_high(self, series: pd.Series, current_idx: int, window: int) -> Optional[int]:
        """Find the most recent pivot high within the window"""
        start_idx = max(0, current_idx - window)
        end_idx = current_idx
        
        if end_idx - start_idx < 3:
            return None
        
        # Get the window slice
        window_slice = series.iloc[start_idx:end_idx]
        
        # Check if the slice is empty or has NaN values
        if window_slice.empty or window_slice.isna().all():
            return None
        
        # Find the maximum in the window
        try:
            max_idx = window_slice.idxmax()
            max_idx_pos = series.index.get_loc(max_idx)
            
            # Check if it's a pivot (higher than neighbors)
            if (max_idx_pos > start_idx and max_idx_pos < end_idx - 1 and
                series.iloc[max_idx_pos] > series.iloc[max_idx_pos - 1] and
                series.iloc[max_idx_pos] > series.iloc[max_idx_pos + 1]):
                return max_idx_pos
        except (ValueError, KeyError):
            # Handle cases where idxmax() fails
            return None
        
        return None 