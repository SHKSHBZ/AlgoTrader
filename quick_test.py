#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Signal Test - 2 Minute Demo
Fast check of current trading signals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from pathlib import Path

def quick_test():
    """Quick test of trading signals"""
    print("🚀 QUICK SIGNAL TEST")
    print("=" * 40)
    
    try:
        # Load config
        with open('hybrid_config.json', 'r') as f:
            config = json.load(f)
        
        total_stocks = len(config['watchlist'])
        # Test a sample from each category 
        large_cap_sample = config['watchlist'][:5]      # First 5 large cap
        mid_cap_sample = config['watchlist'][35:40]     # 5 mid cap  
        small_cap_sample = config['watchlist'][70:75]   # 5 small cap
        watchlist = large_cap_sample + mid_cap_sample + small_cap_sample
        
        print(f"📊 Total Stocks Available: {total_stocks}")
        print(f"📊 Testing Sample: {len(watchlist)} (5 Large + 5 Mid + 5 Small)")
        print("-" * 40)
        
        # Check if we have data
        cache_dir = Path('data_cache')
        if not cache_dir.exists():
            print("❌ No data found!")
            print("   Run: python download_historical_data.py")
            return
        
        # Try to load strategy
        try:
            from mtfa_strategy import MTFAStrategy
            strategy = MTFAStrategy()
            
            # Override data loading for cached data
            def cached_load(symbol):
                data = {}
                symbol_cache = cache_dir / symbol
                for tf in ['daily', '60min', '15min']:
                    file_path = symbol_cache / f"{tf}.csv"
                    if file_path.exists():
                        import pandas as pd
                        try:
                            df = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
                            if not df.empty:
                                data[tf] = df
                        except:
                            pass
                return data
            
            strategy._load_mtf_data = cached_load
            strategy_type = "MTFA"
            
        except:
            strategy = None
            strategy_type = "Simple"
        
        print(f"Strategy: {strategy_type}")
        print("-" * 40)
        
        # Test signals
        buy_signals = []
        sell_signals = []
        
        for i, symbol in enumerate(watchlist, 1):
            try:
                # Show category
                if i <= 5:
                    cat = "L"  # Large
                elif i <= 10:
                    cat = "M"  # Mid 
                else:
                    cat = "S"  # Small
                    
                print(f"[{i:2}/15] {symbol:<12} {cat}", end=" ")
                
                if strategy:
                    result = strategy.analyze(symbol)
                    signal = result.get('signal', 'HOLD')
                    score = result.get('score', 50)
                    confidence = result.get('confidence', 'low')
                    
                    if signal == 'BUY':
                        buy_signals.append(symbol)
                        print(f"🟢 BUY ({score:.0f}, {confidence})")
                    elif signal == 'SELL':
                        sell_signals.append(symbol)
                        print(f"🔴 SELL ({score:.0f}, {confidence})")
                    else:
                        print(f"⚪ HOLD ({score:.0f})")
                else:
                    # Simple fallback
                    cache_file = cache_dir / symbol / '15min.csv'
                    if cache_file.exists():
                        import pandas as pd
                        data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                        if len(data) >= 50:
                            current = data['close'].iloc[-1]
                            sma20 = data['close'].rolling(20).mean().iloc[-1]
                            sma50 = data['close'].rolling(50).mean().iloc[-1]
                            
                            if current > sma20 > sma50:
                                buy_signals.append(symbol)
                                print("🟢 BUY")
                            elif current < sma20 < sma50:
                                sell_signals.append(symbol)
                                print("🔴 SELL")
                            else:
                                print("⚪ HOLD")
                        else:
                            print("⚪ HOLD")
                    else:
                        print("❌ NO DATA")
                        
            except Exception as e:
                print("❌ ERROR")
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 SIGNAL SUMMARY")
        print("=" * 40)
        print(f"🟢 BUY Signals:  {len(buy_signals)}")
        if buy_signals:
            print(f"   {', '.join(buy_signals)}")
        
        print(f"🔴 SELL Signals: {len(sell_signals)}")
        if sell_signals:
            print(f"   {', '.join(sell_signals)}")
        
        total_signals = len(buy_signals) + len(sell_signals)
        print(f"\nSignal Rate: {total_signals}/10 ({total_signals*10}%)")
        
        # Next steps
        print(f"\n🎯 NEXT STEPS:")
        if buy_signals:
            print(f"   ✅ Found {len(buy_signals)} opportunities!")
            print(f"   📊 Run: python paper_trading.py")
        else:
            print(f"   ⏳ No signals right now")
            print(f"   🔄 Try again in 30 minutes")
        
        print("=" * 40)
        
    except FileNotFoundError:
        print("❌ Configuration file not found!")
        print("   Ensure hybrid_config.json exists")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    quick_test()