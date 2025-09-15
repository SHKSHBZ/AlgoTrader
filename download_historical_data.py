#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download 3 years of historical data for backtesting
Optimized for Indian markets with proper IST handling
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data_cache_manager import DataCacheManager
import json
import logging
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def main():
    print("="*60)
    print("📥 HISTORICAL DATA DOWNLOAD")
    print("="*60)
    print(f"Start time: {datetime.now(IST)}")
    print()
    
    # Load configuration to get watchlist
    with open('hybrid_config.json', 'r') as f:
        config = json.load(f)
    
    symbols = config['watchlist']
    print(f"📊 Stocks to download: {len(symbols)}")
    print(f"📊 Stocks: {', '.join(symbols[:5])}... and {len(symbols)-5} more")
    
    # Initialize cache manager
    cache_mgr = DataCacheManager()
    
    # For initial setup, download key timeframes
    # Start with daily and 15min (most important for our strategy)
    timeframes = ['daily', '15min', '60min']  # Skip 5min initially to save time
    
    print(f"📊 Timeframes: {', '.join(timeframes)}")
    print(f"📊 Total operations: {len(symbols) * len(timeframes)}")
    print()
    
    # Ask for confirmation
    response = input("This will take approximately 10-15 minutes. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Download cancelled.")
        return
    
    print("\nStarting download...")
    print("-"*60)
    
    # Download all data
    success_count = 0
    failed_downloads = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Processing {symbol}...")
        
        for timeframe in timeframes:
            try:
                print(f"  📥 Downloading {timeframe}...", end=" ")
                data = cache_mgr.download_historical_data(symbol, timeframe, force_download=True)
                
                if data is not None and not data.empty:
                    print(f"✅ {len(data)} bars")
                    success_count += 1
                else:
                    print(f"❌ No data")
                    failed_downloads.append(f"{symbol}_{timeframe}")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                failed_downloads.append(f"{symbol}_{timeframe}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 DOWNLOAD SUMMARY")
    print("="*60)
    print(f"✅ Successful: {success_count}/{len(symbols) * len(timeframes)}")
    
    if failed_downloads:
        print(f"❌ Failed: {len(failed_downloads)}")
        print(f"   Failed items: {', '.join(failed_downloads[:5])}")
    
    print(f"\nEnd time: {datetime.now(IST)}")
    
    # Show cache summary
    cache_mgr.print_cache_summary()
    
    print("\n✅ Historical data ready for backtesting!")
    print("📂 Data stored in: data_cache/ directory")

if __name__ == "__main__":
    main()