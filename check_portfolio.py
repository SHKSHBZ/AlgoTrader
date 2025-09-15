#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Portfolio Status Checker
View your current paper trading portfolio without running full trading session
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Windows console compatibility
import locale
if sys.platform.startswith('win'):
    locale.setlocale(locale.LC_ALL, 'C')

from paper_trading import PerfectTraderPaperTrading
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def main():
    print("=" * 60)
    print("📊 PAPER TRADING PORTFOLIO STATUS")
    print("=" * 60)
    print(f"🕐 Current Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    # Create trader instance (will load existing portfolio)
    trader = PerfectTraderPaperTrading()
    
    # Display detailed portfolio status
    trader.print_status()
    
    # Show recent trade history if available
    if trader.trade_history:
        print(f"\n📈 RECENT TRADES (Last 5):")
        recent_trades = trader.trade_history[-5:]
        
        print(f"   {'Stock':<10} | {'Action':<4} | {'Qty':<3} | {'Price':<8} | {'P&L%':<6} | {'Time'}")
        print(f"   {'-'*60}")
        
        for trade in recent_trades:
            action = trade.get('action', 'N/A')
            symbol = trade.get('symbol', 'N/A')
            qty = trade.get('shares', 0)
            price = trade.get('price', trade.get('entry_price', trade.get('exit_price', 0)))
            pnl_pct = trade.get('pnl_pct', 0)
            time_str = trade.get('exit_time', trade.get('entry_time', 'N/A'))
            
            if isinstance(time_str, str) and len(time_str) > 10:
                time_str = time_str[11:16]  # Extract HH:MM
            
            print(f"   {symbol:<10} | {action:<4} | {qty:>3} | ₹{price:>7.2f} | {pnl_pct:>+5.1f}% | {time_str}")
    
    print("\n" + "=" * 60)
    print("💡 Run 'python paper_trading.py' to start live trading")
    print("=" * 60)

if __name__ == "__main__":
    main()