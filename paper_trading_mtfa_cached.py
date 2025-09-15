#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTFA Paper Trading with Cached Data Only
Full strategy without authentication delays
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytz

IST = pytz.timezone('Asia/Kolkata')

class CachedMTFAPaperTrading:
    """
    Full MTFA strategy using only cached data
    No API calls, no authentication needed
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.available_capital = initial_capital
        
        # Virtual portfolio
        self.positions = {}
        self.trade_history = []
        
        # Load config
        with open('hybrid_config.json', 'r') as f:
            self.config = json.load(f)
        
        self.watchlist = self.config['watchlist']
        self.max_positions = 10
        self.risk_per_trade = 0.01
        
        # Costs
        self.transaction_cost = 0.002
        self.slippage = 0.001
        
        # Stats
        self.total_trades = 0
        self.winning_trades = 0
        self.start_time = datetime.now(IST)
        
        # Import MTFA strategy without Zerodha dependencies
        self.strategy = self._get_cached_strategy()
        
    def _get_cached_strategy(self):
        """Get MTFA strategy configured for cached data only"""
        try:
            # Import the strategy
            from mtfa_strategy import MTFAStrategy
            
            # Create strategy instance
            strategy = MTFAStrategy()
            
            # Override the data loading to use cached data only
            original_load = strategy._load_mtf_data
            
            def cached_load(symbol):
                """Load from cache files only"""
                data = {}
                cache_dir = Path('data_cache') / symbol
                
                for timeframe in ['daily', '60min', '15min']:
                    cache_file = cache_dir / f"{timeframe}.csv"
                    if cache_file.exists():
                        try:
                            df = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                            if not df.empty:
                                data[timeframe] = df
                        except:
                            pass
                
                return data
            
            # Replace the method
            strategy._load_mtf_data = cached_load
            
            return strategy
            
        except Exception as e:
            print(f"⚠️ Could not load MTFA strategy: {e}")
            print("   Using simplified signals instead")
            return None
    
    def get_signal(self, symbol: str) -> Dict:
        """Get trading signal for symbol"""
        if self.strategy:
            try:
                # Use full MTFA strategy
                result = self.strategy.analyze(symbol)
                return result
            except Exception as e:
                logging.error(f"MTFA error for {symbol}: {e}")
        
        # Fallback to simple signals
        return self._simple_signal(symbol)
    
    def _simple_signal(self, symbol: str) -> Dict:
        """Simple fallback signal if MTFA fails"""
        try:
            # Check if we have cached data
            cache_file = Path('data_cache') / symbol / '15min.csv'
            if not cache_file.exists():
                return {'signal': 'HOLD', 'score': 50, 'entry_price': 0}
            
            # Load cached data
            data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
            if len(data) < 50:
                return {'signal': 'HOLD', 'score': 50, 'entry_price': 0}
            
            # Get latest price
            current_price = data['close'].iloc[-1]
            
            # Simple indicators
            sma_20 = data['close'].rolling(20).mean().iloc[-1]
            sma_50 = data['close'].rolling(50).mean().iloc[-1]
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Generate signal
            signal = 'HOLD'
            score = 50
            
            if current_price > sma_20 > sma_50 and rsi < 70:
                signal = 'BUY'
                score = 70
            elif current_price < sma_20 < sma_50 and rsi > 30:
                signal = 'SELL'
                score = 30
            
            return {
                'signal': signal,
                'score': score,
                'entry_price': current_price,
                'stop_loss': current_price * 0.98,
                'target': current_price * 1.03
            }
            
        except Exception as e:
            logging.error(f"Simple signal error for {symbol}: {e}")
            return {'signal': 'HOLD', 'score': 50, 'entry_price': 0}
    
    def get_current_price(self, symbol: str) -> float:
        """Get latest price from cached data"""
        try:
            cache_file = Path('data_cache') / symbol / '15min.csv'
            if cache_file.exists():
                data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                if not data.empty:
                    return data['close'].iloc[-1]
        except:
            pass
        return 0
    
    def execute_buy(self, symbol: str, signal_result: Dict) -> bool:
        """Execute virtual buy"""
        if len(self.positions) >= self.max_positions:
            return False
        
        price = signal_result.get('entry_price', 0)
        if price <= 0:
            return False
            
        # Apply slippage
        entry_price = price * (1 + self.slippage)
        stop_loss = signal_result.get('stop_loss', entry_price * 0.98)
        target = signal_result.get('target', entry_price * 1.03)
        
        # Position sizing
        risk_amount = self.capital * self.risk_per_trade
        risk_per_share = entry_price - stop_loss
        shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Check capital
        cost = shares * entry_price * (1 + self.transaction_cost)
        if cost > self.available_capital:
            shares = int(self.available_capital * 0.95 / entry_price)
            cost = shares * entry_price * (1 + self.transaction_cost)
            
        if shares <= 0:
            return False
            
        # Create position
        self.positions[symbol] = {
            'entry_time': datetime.now(IST),
            'entry_price': entry_price,
            'shares': shares,
            'stop_loss': stop_loss,
            'target': target,
            'score': signal_result.get('score', 50),
            'confidence': signal_result.get('confidence', 'low')
        }
        
        self.available_capital -= cost
        self.total_trades += 1
        
        confidence = signal_result.get('confidence', 'unknown')
        components = signal_result.get('components', {})
        
        print(f"🟢 BUY: {symbol} - {shares} shares @ ₹{entry_price:.2f} [{confidence}]")
        print(f"   Stop: ₹{stop_loss:.2f}, Target: ₹{target:.2f}")
        
        if components:
            print(f"   Signals: Daily={components.get('daily', 0):.0f}, "
                  f"60min={components.get('60min', 0):.0f}, "
                  f"15min={components.get('15min', 0):.0f}")
        
        return True
    
    def execute_sell(self, symbol: str, price: float, reason: str) -> bool:
        """Execute virtual sell"""
        if symbol not in self.positions:
            return False
            
        position = self.positions[symbol]
        exit_price = price * (1 - self.slippage)
        
        # Calculate P&L
        proceeds = position['shares'] * exit_price * (1 - self.transaction_cost)
        cost = position['shares'] * position['entry_price'] * (1 + self.transaction_cost)
        pnl = proceeds - cost
        pnl_pct = (pnl / cost) * 100
        
        self.available_capital += proceeds
        
        if pnl > 0:
            self.winning_trades += 1
            status = "🟢 PROFIT"
        else:
            status = "🔴 LOSS"
            
        print(f"{status}: {symbol} - Exit @ ₹{exit_price:.2f}")
        print(f"   P&L: ₹{pnl:,.0f} ({pnl_pct:+.2f}%) - {reason}")
        
        # Record trade
        self.trade_history.append({
            'symbol': symbol,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'duration': (datetime.now(IST) - position['entry_time']).total_seconds() / 3600
        })
        
        del self.positions[symbol]
        return True
    
    def scan_market(self):
        """Scan all stocks for signals"""
        print(f"\n{'='*60}")
        print(f"📊 MARKET SCAN - {datetime.now(IST).strftime('%H:%M:%S')}")
        
        if self.strategy:
            print(f"   Using: MTFA Strategy (Daily + 60min + 15min)")
        else:
            print(f"   Using: Simple Strategy (SMA + RSI)")
        
        print(f"{'='*60}")
        
        signals_found = False
        buy_signals = []
        
        # Scan watchlist
        for i, symbol in enumerate(self.watchlist[:15], 1):  # First 15 stocks
            try:
                print(f"   [{i}/15] {symbol}...", end=" ")
                
                # Check existing position
                if symbol in self.positions:
                    position = self.positions[symbol]
                    current_price = self.get_current_price(symbol)
                    
                    if current_price <= 0:
                        print("NO DATA")
                        continue
                    
                    # Check stop/target
                    if current_price <= position['stop_loss']:
                        print(f"STOP LOSS HIT")
                        self.execute_sell(symbol, current_price, 'STOP_LOSS')
                        signals_found = True
                    elif current_price >= position['target']:
                        print(f"TARGET HIT")
                        self.execute_sell(symbol, current_price, 'TARGET')
                        signals_found = True
                    else:
                        unrealized = (current_price - position['entry_price']) * position['shares']
                        pct = (current_price - position['entry_price']) / position['entry_price'] * 100
                        print(f"HOLDING [{pct:+.1f}%]")
                else:
                    # Get new signal
                    signal_result = self.get_signal(symbol)
                    signal = signal_result.get('signal', 'HOLD')
                    score = signal_result.get('score', 50)
                    
                    if signal == 'BUY':
                        print(f"BUY (Score: {score:.0f})")
                        buy_signals.append((symbol, signal_result))
                    elif signal == 'SELL':
                        print(f"SELL (Score: {score:.0f})")
                    else:
                        print(f"HOLD")
                        
            except Exception as e:
                print(f"ERROR")
                logging.error(f"Error scanning {symbol}: {e}")
        
        # Execute buy signals (best scores first)
        buy_signals.sort(key=lambda x: x[1].get('score', 0), reverse=True)
        for symbol, signal_result in buy_signals[:3]:  # Top 3 signals
            if self.execute_buy(symbol, signal_result):
                signals_found = True
                
        if not signals_found and not self.positions:
            print("\n  ⚪ No trading opportunities found")
    
    def print_status(self):
        """Print portfolio status"""
        total_value = self.available_capital
        
        # Add position values
        for symbol, position in self.positions.items():
            current_price = self.get_current_price(symbol)
            if current_price > 0:
                total_value += position['shares'] * current_price
                
        total_return = (total_value - self.initial_capital) / self.initial_capital * 100
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        print(f"\n💰 PORTFOLIO STATUS")
        print(f"   Value: ₹{total_value:,.0f} ({total_return:+.2f}%)")
        print(f"   Cash: ₹{self.available_capital:,.0f}")
        print(f"   Positions: {len(self.positions)}/{self.max_positions}")
        
        if self.total_trades > 0:
            print(f"   Win Rate: {win_rate:.0f}% ({self.winning_trades}/{self.total_trades})")
            
        if self.trade_history:
            avg_pnl = np.mean([t['pnl_pct'] for t in self.trade_history])
            print(f"   Avg Trade: {avg_pnl:+.2f}%")
    
    def run(self, duration_hours: float = 4.0):
        """Run paper trading session"""
        print("🤖 MTFA PAPER TRADING - CACHED DATA MODE")
        print("="*60)
        print(f"💰 Capital: ₹{self.initial_capital:,.0f}")
        print(f"📊 Strategy: {'MTFA' if self.strategy else 'Simple'}")
        print(f"📈 Stocks: 15 (optimized for speed)")
        print(f"⏱️ Duration: {duration_hours} hours")
        print(f"🔄 Scan Interval: 10 minutes")
        print(f"🛑 Press Ctrl+C to stop")
        print("="*60)
        
        # Check cached data availability
        cache_dir = Path('data_cache')
        if not cache_dir.exists():
            print("\n❌ No cached data found!")
            print("   Run: python download_historical_data.py")
            return
        
        cached_stocks = [d.name for d in cache_dir.iterdir() if d.is_dir()]
        print(f"\n✅ Found cached data for {len(cached_stocks)} stocks")
        
        end_time = datetime.now(IST) + timedelta(hours=duration_hours)
        scan_count = 0
        
        try:
            while datetime.now(IST) < end_time:
                scan_count += 1
                print(f"\n🔍 SCAN #{scan_count}")
                
                self.scan_market()
                self.print_status()
                
                # Wait for next scan
                remaining = (end_time - datetime.now(IST)).total_seconds()
                if remaining > 0:
                    wait_time = min(600, remaining)  # 10 minutes or remaining time
                    if wait_time > 60:
                        print(f"\n⏳ Next scan in {wait_time/60:.0f} minutes...")
                        time.sleep(wait_time)
                    else:
                        break
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
            
        # Close all positions
        if self.positions:
            print("\n📊 Closing all positions...")
            for symbol in list(self.positions.keys()):
                price = self.get_current_price(symbol)
                if price > 0:
                    self.execute_sell(symbol, price, 'SESSION_END')
        
        # Final results
        print("\n" + "="*60)
        print("📊 SESSION COMPLETE")
        print("="*60)
        self.print_status()
        
        # Performance summary
        if self.trade_history:
            winners = [t for t in self.trade_history if t['pnl'] > 0]
            losers = [t for t in self.trade_history if t['pnl'] <= 0]
            
            print(f"\n📈 TRADE ANALYSIS:")
            print(f"   Winners: {len(winners)}")
            print(f"   Losers: {len(losers)}")
            
            if winners:
                avg_win = np.mean([t['pnl_pct'] for t in winners])
                print(f"   Avg Win: {avg_win:+.2f}%")
            if losers:
                avg_loss = np.mean([t['pnl_pct'] for t in losers])
                print(f"   Avg Loss: {avg_loss:+.2f}%")
            
            # Best/worst trades
            if self.trade_history:
                best = max(self.trade_history, key=lambda x: x['pnl_pct'])
                worst = min(self.trade_history, key=lambda x: x['pnl_pct'])
                print(f"   Best Trade: {best['symbol']} ({best['pnl_pct']:+.2f}%)")
                print(f"   Worst Trade: {worst['symbol']} ({worst['pnl_pct']:+.2f}%)")
        
        # Recommendation
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        final_value = self.update_portfolio_value()
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        print(f"\n🎯 RECOMMENDATION:")
        if win_rate >= 60 and total_return > 0:
            print(f"   ✅ Strategy shows promise! Consider live testing.")
        elif self.total_trades < 5:
            print(f"   ⏳ Need more trades for evaluation. Run longer session.")
        else:
            print(f"   ⚠️ Review strategy parameters before live trading.")


def main():
    """Run MTFA paper trading with cached data"""
    engine = CachedMTFAPaperTrading(initial_capital=100000)
    engine.run(duration_hours=4.0)


if __name__ == "__main__":
    main()