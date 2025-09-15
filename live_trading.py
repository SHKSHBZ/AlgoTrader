#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perfect Trader - Live Trading System
REAL MONEY TRADING - Use only after successful paper trading
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from hybrid_trading_orchestrator import HybridTradingOrchestrator

def main():
    """Start live trading system"""
    print("🚨 PERFECT TRADER - LIVE TRADING")
    print("=" * 50)
    print("⚠️  THIS USES REAL MONEY!")
    print("⚠️  ONLY USE AFTER SUCCESSFUL PAPER TRADING")
    print("=" * 50)
    
    # Safety check
    response = input("\nAre you sure you want to trade with REAL money? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Live trading cancelled. Use paper_trading.py to practice.")
        return
    
    print("\n✅ Starting live trading system...")
    
    try:
        # Load configuration
        with open('hybrid_config.json', 'r') as f:
            config = json.load(f)
        
        # Ensure paper trading is disabled
        config['paper_trading'] = False
        
        # Save config
        with open('hybrid_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        # Start orchestrator
        orchestrator = HybridTradingOrchestrator('hybrid_config.json')
        
        print("🚀 Live trading started!")
        print("🛑 Press Ctrl+C to stop")
        print("-" * 50)
        
        # Start trading
        trading_thread = orchestrator.start_trading()
        
        # Keep running
        try:
            while orchestrator.is_running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping live trading...")
            orchestrator.stop_trading()
            
        print("\n✅ Live trading stopped successfully")
        
    except FileNotFoundError:
        print("❌ Configuration files missing!")
        print("   Ensure hybrid_config.json and zerodha_config.json exist")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()