# Perfect Trader - Deployment Guide

## Pre-Deployment Checklist

### ✅ **System Requirements**
- Python 3.8+ installed
- Required packages: `pip install -r requirements.txt`
- Zerodha Kite API credentials
- Stable internet connection
- Windows/Linux/Mac compatible

### ✅ **Data Setup**
```bash
# 1. Download historical data (15-20 minutes) - 105 stocks
python download_historical_data.py

# 2. Quick signal check (2 minutes)
python quick_test.py

# 3. Verify data quality
python -c "from data_cache_manager import DataCacheManager; DataCacheManager().print_cache_summary()"
```

### ✅ **Configuration Files**
Ensure these files are properly configured:
- `zerodha_config.json` - API credentials
- `hybrid_config.json` - Trading parameters
- Verify watchlist contains 105 stocks
- Capital set to ₹250,000 for paper trading
- Trailing stop loss enabled (2% with 1.5% activation)

## Deployment Phases

### 🔹 **Phase 1: Paper Trading (MANDATORY)**
Duration: 2-4 weeks
Virtual Capital: ₹250,000

```bash
# Start paper trading with position persistence
python paper_trading.py

# Check portfolio anytime without trading
python check_portfolio.py
```

**Success Criteria:**
- Win rate ≥ 60% over 20+ trades
- Average return per trade > 0.5%
- Maximum drawdown < 10%
- Trailing stops protecting profits
- Position persistence working correctly
- No system errors or crashes

### 🔹 **Phase 2: Minimal Capital Testing**
Duration: 4-6 weeks
Capital: ₹10,000 - ₹25,000

```bash
# Start live trading with minimal capital
python live_trading.py
```

**Success Criteria:**
- Maintain win rate ≥ 60%
- Positive net returns after costs
- System stability (99%+ uptime)
- Risk management working correctly

### 🔹 **Phase 3: Scaled Deployment**
Duration: Ongoing
Capital: ₹50,000 - ₹200,000+

**Scaling Guidelines:**
- Increase capital by 2x only after 4 weeks of success
- Monitor performance metrics daily
- Review and adjust parameters monthly

## Production Setup

### **System Configuration**

#### 1. **Automated Startup**
Create startup script (`start_trader.bat` for Windows):
```batch
@echo off
cd /d "C:\Users\shaik\OneDrive\Desktop\Project\Perfect_Trader"
python hybrid_trading_orchestrator.py
pause
```

#### 2. **Logging Setup**
Ensure logs directory exists:
```bash
mkdir logs
```

#### 3. **Backup Configuration**
```bash
# Backup critical files daily
cp hybrid_config.json backups/hybrid_config_$(date +%Y%m%d).json
cp zerodha_config.json backups/zerodha_config_$(date +%Y%m%d).json
```

### **Monitoring & Alerts**

#### Daily Monitoring Checklist:
- [ ] System started successfully
- [ ] API connection established
- [ ] Data updates working
- [ ] No error messages in logs
- [ ] Win rate tracking (weekly average)

#### Weekly Review:
- [ ] Performance vs baseline (65% win rate)
- [ ] Risk metrics within limits
- [ ] Capital allocation review
- [ ] System health check

#### Monthly Review:
- [ ] Strategy parameter optimization
- [ ] Watchlist updates if needed
- [ ] Historical data cleanup
- [ ] Performance reporting

## Risk Management

### **Hard Stops**
System will automatically stop trading if:
- Win rate drops below 50% over 30 trades
- Daily loss exceeds 5% of capital
- API connection fails for >30 minutes
- System errors occur repeatedly

### **Position Limits**
- Maximum 20 positions simultaneously
- Maximum 1.5% risk per trade (capital allocation varies)
- Kelly criterion for position sizing
- Trailing stops activate at 1.5% profit
- 2% trailing stop protection

### **Emergency Procedures**

#### Stop All Trading:
```bash
# Create emergency stop file
touch EMERGENCY_STOP

# Or kill the process
pkill -f hybrid_trading_orchestrator.py
```

#### Manual Position Review:
```bash
# Check current positions
python -c "from zerodha_loader import *; print_current_positions()"
```

## Troubleshooting

### **Common Issues**

#### 1. **API Authentication Failures**
```
Solution: Delete token files and re-authenticate
rm access_token.txt enctoken.txt
python hybrid_trading_orchestrator.py
```

#### 2. **Data Download Issues**
```
Solution: Clear cache and re-download
rm -rf data_cache/
python download_historical_data.py
```

#### 3. **Strategy Not Generating Signals**
```
Solution: Check data quality and thresholds
python mtfa_strategy.py  # Test strategy manually
```

#### 4. **High Memory Usage**
```
Solution: Restart system daily during market close
# Add to crontab (Linux/Mac)
0 16 * * 1-5 pkill -f hybrid_trading_orchestrator.py
15 9 * * 1-5 cd /path/to/trader && python hybrid_trading_orchestrator.py
```

### **Log Analysis**
```bash
# Check recent errors
grep -i "error" logs/trading_$(date +%Y%m%d).log

# Monitor win rate
grep -i "trade closed" logs/trading_$(date +%Y%m%d).log | grep "profit"
```

## Performance Optimization

### **System Performance**
- Run on SSD for faster data access
- Minimum 8GB RAM recommended
- Close unnecessary programs during trading hours
- Use wired internet connection (not WiFi)

### **Trading Performance**
- Review and adjust thresholds monthly
- Monitor sector concentration
- Analyze losing trades for patterns
- Consider market regime changes

## Security

### **Data Protection**
- Store API credentials securely
- Regular backup of configuration
- Use strong passwords for system access
- Monitor for unauthorized access

### **Financial Security**
- Start with paper trading
- Use stop-loss orders
- Regular portfolio review
- Keep trading capital separate from savings

## Support & Maintenance

### **Regular Maintenance**
- **Daily**: Check system status and performance
- **Weekly**: Review trading results and metrics
- **Monthly**: Update historical data and optimize parameters
- **Quarterly**: Full system review and potential upgrades

### **Getting Help**
1. Check logs for error messages
2. Review this deployment guide
3. Test individual components in isolation
4. Document issues with timestamps and error messages

## Success Metrics

### **Target Performance** (Monthly)
- Win Rate: 65-70%
- Profit Factor: >1.8
- Annual ROI: 15%
- Maximum Drawdown: <12%
- System Uptime: >99%
- Trailing Stop Efficiency: >90%

### **Warning Signals**
- Win rate drops below 60% for 2+ weeks
- Consecutive losses > 10 trades
- System downtime > 2% of trading hours
- Memory/CPU usage consistently high

---

**Remember**: Trading involves risk. Never invest more than you can afford to lose. This system is a tool to assist your trading decisions, not a guarantee of profits.

**Key Features Added September 2025:**
- ✅ **Trailing Stop Loss**: 2% protection after 1.5% profit
- ✅ **Position Persistence**: Natural holding across sessions
- ✅ **Increased Capital**: ₹250,000 virtual trading
- ✅ **105 Stock Coverage**: Complete NSE universe
- ✅ **Zerodha-Only Data**: Removed Yahoo Finance dependency

**Last Updated**: September 2025 | **Version**: 3.0 Professional