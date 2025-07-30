@dataclass
class SwingFailureConfig:
    lookback_period: int = 5      # Reduced from 10 to 5 bars
    min_swing_size: float = 0.001  # Reduced from 0.2% to 0.1%
    breach_threshold: float = 0.0002  # Reduced from 0.05% to 0.02%
    reversal_threshold: float = 0.0005  # Reduced from 0.1% to 0.05%
    max_confirmation_bars: int = 2  # Reduced from 3 to 2 bars

class SwingFailureDetector(DetectionStrategy):
    """Detects swing failure patterns (SFP) based on SMC framework"""
    
    def __init__(self, config: SwingFailureConfig):
        self.config = config
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect swing failures"""
        results = []
        data = data.copy()
        
        print("\nStarting swing failure detection...")
        print(f"Data range: {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")
        print(f"Total bars: {len(data)}")
        
        # Find swing points and potential failures
        for i in range(self.config.lookback_period, len(data)-self.config.max_confirmation_bars):
            # Find recent swing high/low
            swing_high = self._get_recent_swing_high(data, i)
            swing_low = self._get_recent_swing_low(data, i)
            
            if i % 100 == 0:  # Print progress every 100 bars
                print(f"Processing bar {i}/{len(data)}")
            
            # Check for high/low breaks and failures
            if swing_high is not None:
                print(f"\nFound swing high at {data['timestamp'].loc[swing_high]}")
                print(f"Price: {data['High'].loc[swing_high]:.2f}")
                if self._check_high_failure(data, i, swing_high):
                    print(f"Found swing high failure at {data['timestamp'].iloc[i]}")
                    results.append(self._create_failure_result(data, i, swing_high, is_high=True))
            
            if swing_low is not None:
                print(f"\nFound swing low at {data['timestamp'].loc[swing_low]}")
                print(f"Price: {data['Low'].loc[swing_low]:.2f}")
                if self._check_low_failure(data, i, swing_low):
                    print(f"Found swing low failure at {data['timestamp'].iloc[i]}")
                    results.append(self._create_failure_result(data, i, swing_low, is_high=False))
        
        print(f"\nDetection complete. Found {len(results)} swing failures.")
        return results
    
    def _get_recent_swing_high(self, data: pd.DataFrame, current_idx: int) -> Optional[int]:
        """Find the most recent valid swing high"""
        window = data.iloc[current_idx-self.config.lookback_period:current_idx]
        for i in range(len(window)-2, 0, -1):
            idx = window.index[i]
            # Changed to check only immediate neighbors
            if data['High'].loc[idx] > data['High'].loc[idx-1] and data['High'].loc[idx] > data['High'].loc[idx+1]:
                # Check if swing is significant
                swing_size = data['High'].loc[idx] / data['Low'].loc[idx-1:idx+1].min() - 1
                if swing_size >= self.config.min_swing_size:
                    return idx
        return None
    
    def _get_recent_swing_low(self, data: pd.DataFrame, current_idx: int) -> Optional[int]:
        """Find the most recent valid swing low"""
        window = data.iloc[current_idx-self.config.lookback_period:current_idx]
        for i in range(len(window)-2, 0, -1):
            idx = window.index[i]
            # Changed to check only immediate neighbors
            if data['Low'].loc[idx] < data['Low'].loc[idx-1] and data['Low'].loc[idx] < data['Low'].loc[idx+1]:
                # Check if swing is significant
                swing_size = data['High'].loc[idx-1:idx+1].max() / data['Low'].loc[idx] - 1
                if swing_size >= self.config.min_swing_size:
                    return idx
        return None
    
    def _check_high_failure(self, data: pd.DataFrame, current_idx: int, swing_high_idx: int) -> bool:
        """Check for valid swing high failure"""
        swing_high_price = data['High'].loc[swing_high_idx]
        
        # 1. Check if price breaches the swing high
        breach_size = data['High'].iloc[current_idx] / swing_high_price - 1
        print(f"Breach size: {breach_size:.4%}")
        if breach_size < self.config.breach_threshold:
            print("Failed breach threshold check")
            return False
            
        # 2. Check for immediate reversal within confirmation period
        confirm_window = slice(current_idx+1, current_idx+self.config.max_confirmation_bars+1)
        reversal_low = data['Low'].iloc[confirm_window].min()
        reversal_size = data['High'].iloc[current_idx] / reversal_low - 1
        print(f"Reversal size: {reversal_size:.4%}")
        
        # 3. Price must close below the swing high within confirmation period
        closes_below = (data['Close'].iloc[confirm_window] < swing_high_price).any()
        print(f"Closes below swing high: {closes_below}")
        
        if reversal_size >= self.config.reversal_threshold and closes_below:
            print("Valid swing high failure detected!")
            return True
        print("Failed reversal or close condition")
        return False
    
    def _check_low_failure(self, data: pd.DataFrame, current_idx: int, swing_low_idx: int) -> bool:
        """Check for valid swing low failure"""
        swing_low_price = data['Low'].loc[swing_low_idx]
        
        # 1. Check if price breaches the swing low
        breach_size = swing_low_price / data['Low'].iloc[current_idx] - 1
        print(f"Breach size: {breach_size:.4%}")
        if breach_size < self.config.breach_threshold:
            print("Failed breach threshold check")
            return False
            
        # 2. Check for immediate reversal within confirmation period
        confirm_window = slice(current_idx+1, current_idx+self.config.max_confirmation_bars+1)
        reversal_high = data['High'].iloc[confirm_window].max()
        reversal_size = reversal_high / data['Low'].iloc[current_idx] - 1
        print(f"Reversal size: {reversal_size:.4%}")
        
        # 3. Price must close above the swing low within confirmation period
        closes_above = (data['Close'].iloc[confirm_window] > swing_low_price).any()
        print(f"Closes above swing low: {closes_above}")
        
        if reversal_size >= self.config.reversal_threshold and closes_above:
            print("Valid swing low failure detected!")
            return True
        print("Failed reversal or close condition")
        return False
    
    def _create_failure_result(self, data: pd.DataFrame, current_idx: int, swing_idx: int, is_high: bool) -> DetectionResult:
        """Create swing failure detection result"""
        if is_high:
            pattern_type = "SWING_HIGH_FAILURE"
            entry_price = data['Close'].iloc[current_idx+1]  # Enter on next candle
            stop_loss = data['High'].iloc[current_idx] * 1.001  # 0.1% above breach
            # Target the previous swing low or 2x the reversal size
            reversal_size = data['High'].iloc[current_idx] - data['Low'].iloc[current_idx+1:current_idx+self.config.max_confirmation_bars+1].min()
            take_profit = entry_price - (reversal_size * 2)
        else:
            pattern_type = "SWING_LOW_FAILURE"
            entry_price = data['Close'].iloc[current_idx+1]  # Enter on next candle
            stop_loss = data['Low'].iloc[current_idx] * 0.999  # 0.1% below breach
            # Target the previous swing high or 2x the reversal size
            reversal_size = data['High'].iloc[current_idx+1:current_idx+self.config.max_confirmation_bars+1].max() - data['Low'].iloc[current_idx]
            take_profit = entry_price + (reversal_size * 2)
            
        # Calculate confidence based on breach and reversal size
        breach_size = abs(data['Close'].iloc[current_idx] / data['Close'].loc[swing_idx] - 1)
        reversal_size = abs(data['Close'].iloc[current_idx+1] / data['Close'].iloc[current_idx] - 1)
        confidence = min(0.9, (breach_size * 0.4 + reversal_size * 0.6) * 100)  # Weight reversal more than breach
            
        return DetectionResult(
            pattern_type=pattern_type,
            timestamp=data['timestamp'].iloc[current_idx],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            metadata={
                'swing_price': data['High' if is_high else 'Low'].loc[swing_idx],
                'breach_size': breach_size,
                'reversal_size': reversal_size,
                'bars_to_swing': current_idx - swing_idx
            }
        )
    
    def get_required_columns(self) -> List[str]:
        return ['timestamp', 'Open', 'High', 'Low', 'Close'] 