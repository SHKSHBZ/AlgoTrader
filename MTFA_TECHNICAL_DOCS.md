# Multi-Timeframe Analysis (MTFA) Technical Documentation

## Overview
The MTFA system implements a sophisticated trading strategy that analyzes multiple timeframes to generate high-confidence trading signals. This document provides technical details for developers and advanced users.

## Strategy Architecture

### Timeframe Hierarchy
```
Daily (1d)     → Trend Filter (30% weight)
├─ 60min (1h)  → Setup Analysis (40% weight)
└─ 15min       → Entry Timing (30% weight)
```

### Signal Generation Process
1. **Data Loading**: Multi-timeframe data from cache
2. **Component Analysis**: Individual timeframe scoring
3. **Voting System**: Bullish/bearish votes per timeframe
4. **Weighted Scoring**: Dynamic weight adjustment
5. **Signal Decision**: 2/3 consensus requirement

## Technical Indicators by Timeframe

### Daily Analysis (Trend Filter)
- **Moving Averages**: SMA 50, SMA 200
- **ADX**: Trend strength measurement
- **Trend Classification**: UP/DOWN/NEUTRAL
- **Purpose**: Filter trades against major trend

### 60-Minute Analysis (Setup)
- **RSI**: 14-period momentum
- **MACD**: Trend momentum confirmation
- **Bollinger Bands**: Support/resistance levels
- **Volume**: Confirmation indicator
- **Purpose**: Identify intermediate setups

### 15-Minute Analysis (Entry)
- **RSI**: 9-period short-term momentum
- **Stochastic**: Overbought/oversold levels
- **Moving Average Alignment**: SMA 10/20
- **Price Action**: Recent 5-bar momentum
- **Purpose**: Precise entry timing

## Configuration Parameters

### Core Thresholds
```python
buy_threshold = 65      # Reduced for more signals
sell_threshold = 35     # Balanced exit
min_components = 2      # 2/3 consensus (moderate)
```

### Dynamic Weights
```python
# Default weights
default_weights = {
    'daily': 0.30,   # Trend direction
    '60min': 0.40,   # Primary signal
    '15min': 0.30    # Entry timing
}

# High volatility adjustment
high_vol_weights = {
    'daily': 0.20,   # Less weight on long-term
    '60min': 0.35,   # 
    '15min': 0.45    # More weight on short-term
}

# Low volatility adjustment
low_vol_weights = {
    'daily': 0.40,   # More weight on long-term
    '60min': 0.40,   #
    '15min': 0.20    # Less weight on short-term
}
```

## Scoring Algorithm

### Component Scoring (0-100 scale)
Each timeframe generates a score where:
- **0-30**: Strong bearish
- **30-45**: Weak bearish
- **45-55**: Neutral
- **55-70**: Weak bullish
- **70-100**: Strong bullish

### Vote Calculation
```python
votes = {
    'daily': daily_score > 55,
    '60min': h1_score > 55,
    '15min': m15_score > 55
}
bullish_votes = sum(votes.values())
```

### Final Score Calculation
```python
final_score = (
    daily_score * weights['daily'] +
    h1_score * weights['60min'] +
    m15_score * weights['15min'] +
    trend_bias
)
```

### Trend Bias Application
- **Bullish Daily Trend**: +10 bias, allows BUY/HOLD only
- **Bearish Daily Trend**: -10 bias, allows SELL/HOLD only
- **Neutral Daily Trend**: No bias, all signals allowed

## Risk Management

### Position Sizing (Kelly Criterion)
```python
max_risk_per_trade = 0.015  # 1.5% of capital
kelly_fraction = 0.35       # Conservative Kelly sizing
entry_price = current_price
stop_loss = h1_support_level or (entry_price * 0.98)
target = entry_price * 2.3  # 2.3x multiplier for take profit

position_size = (capital * max_risk_per_trade) / (entry_price - stop_loss)
kelly_size = capital * kelly_fraction * win_rate * avg_win_loss_ratio
final_size = min(position_size, kelly_size)  # Use more conservative
```

### Advanced Stop Loss System

#### Initial Stop Loss
- **Primary**: 60-min support level from Bollinger Bands
- **Fallback**: 2% below entry price
- **Target**: 2.3x multiplier above entry

#### Trailing Stop Loss
```python
trailing_stop_activation = 1.5  # Activate at 1.5% profit
trailing_stop_percent = 2.0     # Trail by 2%
trailing_step_size = 0.5        # Update in 0.5% increments

# Activation logic
if current_profit_percent >= trailing_stop_activation:
    new_stop = current_price * (1 - trailing_stop_percent / 100)
    position['stop_loss'] = max(position['stop_loss'], new_stop)
```

## Data Requirements

### Historical Data Needs
- **Daily**: 200+ bars (for SMA 200)
- **60min**: 100+ bars (for indicators)
- **15min**: 50+ bars (for short-term analysis)

### Real-time Data
- **Update Frequency**: Every 15 minutes during market hours
- **Market Hours**: 9:15 AM - 3:30 PM IST
- **Timezone**: Asia/Kolkata (IST)

## Performance Monitoring

### Key Metrics
- **Win Rate**: Target 65-70%
- **Profit Factor**: Target >1.8
- **Annual ROI**: Target 15%
- **Maximum Drawdown**: Target <12%
- **Trailing Stop Efficiency**: Target >90%

### Signal Quality Indicators
```python
# High confidence signals
if bullish_votes == 3 and final_score >= 75:
    confidence = 'high'
elif bullish_votes >= 2 and final_score >= 65:
    confidence = 'medium'
else:
    confidence = 'low'
```

## Error Handling

### Data Validation
```python
def _validate_data(self, data_dict: Dict) -> bool:
    required = ['daily', '60min', '15min']
    for tf in required:
        if tf not in data_dict or len(data_dict[tf]) < 20:
            return False
    return True
```

### Fallback Mechanisms
1. **Missing Indicators**: Skip component, adjust weights
2. **Insufficient Data**: Return HOLD signal
3. **API Failures**: Use cached data
4. **Calculation Errors**: Log error, return neutral score

## Implementation Notes

### Thread Safety
- Cache manager is thread-safe for concurrent access
- Strategy analysis is stateless (no shared state)

### Memory Management
- Historical data cached to disk
- In-memory data limited to recent bars
- Automatic cleanup of old cache files

### Performance Optimization
- Vectorized calculations using NumPy
- TA-Lib for optimized technical indicators
- Efficient data filtering and indexing

## Backtesting Integration

### Walk-Forward Analysis
```python
# Training period: 2022-2023 (when data available)
# Testing period: 2024
# Out-of-sample validation ensures no overfitting
```

### Cost Modeling
```python
commission_per_share = 0.003  # ₹0.003 per share
slippage_percent = 0.0005     # 0.05% market impact
transaction_cost = 0.002      # 0.2% total (includes STT, exchange charges)
```

## Configuration Files

### hybrid_config.json (current)
```json
{
    "initial_capital": 250000,
    "strategy": {
        "buy_threshold": 70,
        "sell_threshold": 30,
        "min_votes": 3,
        "max_risk_per_trade": 0.015,
        "kelly_fraction": 0.35,
        "take_profit_multiplier": 2.3,
        "trailing_stop_enabled": true,
        "trailing_stop_percent": 2.0,
        "trailing_stop_activation_percent": 1.5,
        "trailing_stop_step_size": 0.5
    },
    "performance_target": {
        "annual_roi": 0.15,
        "min_win_rate": 0.65,
        "min_profit_factor": 1.8
    }
}
```

## Future Enhancements

### Planned Features
1. **Machine Learning Integration**: Train models on component scores
2. **Sector Analysis**: Industry-specific weight adjustments  
3. **Market Regime Detection**: Bull/bear/sideways adaptations
4. **Options Integration**: Hedge positions with options

### Scalability Considerations
- **Multi-threading**: Parallel analysis of multiple symbols
- **Cloud Integration**: AWS/Azure for data and computation
- **Real-time Streaming**: WebSocket connections for live data

---

**Maintenance**: Review and update quarterly based on market conditions
**Contact**: Technical issues should be logged with detailed error messages
## New Features (September 2025)

### Trailing Stop Loss Implementation
```python
def update_trailing_stops(self, positions: Dict, current_prices: Dict):
    """Update trailing stops for all profitable positions"""
    for symbol, position in positions.items():
        if symbol not in current_prices:
            continue
            
        current_price = current_prices[symbol]
        entry_price = position['entry_price']
        current_profit_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Activate trailing stop if profit threshold reached
        if current_profit_percent >= self.trailing_activation:
            if 'highest_price' not in position:
                position['highest_price'] = current_price
            else:
                position['highest_price'] = max(position['highest_price'], current_price)
            
            # Calculate new trailing stop
            new_stop = position['highest_price'] * (1 - self.trailing_percent / 100)
            position['stop_loss'] = max(position.get('stop_loss', 0), new_stop)
```

### Position Persistence System
```python
def _save_portfolio_state(self):
    """Save portfolio state for session continuity"""
    state = {
        'last_trading_date': datetime.now(pytz.timezone('Asia/Kolkata')).isoformat(),
        'initial_capital': self.initial_capital,
        'capital': self.capital,
        'positions': self.positions,
        'trade_history': self.trade_history,
        'total_trades': self.total_trades,
        'winning_trades': self.winning_trades
    }
    
    with open(self.portfolio_file, 'w') as f:
        json.dump(state, f, indent=2, default=str)
```

### Enhanced Stock Coverage
- **Universe**: 105 stocks across Large/Mid/Small cap
- **Sectors**: Complete NSE representation
- **Screening**: No artificial limits on stock scanning

**Version**: 3.0 Professional (September 2025)