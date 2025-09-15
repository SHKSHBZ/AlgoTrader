"""
Hybrid Trading Orchestrator - Main Entry Point
Replaces ML-based system with rule-based hybrid strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from datetime import datetime, timedelta
import time
import json
import os
from threading import Thread
import signal
import sys
import pytz

# Force IST timezone for all operations
IST = pytz.timezone('Asia/Kolkata')

# Import our hybrid strategy components
from hybrid_strategy import HybridTradingStrategy
from zerodha_loader import EnhancedHybridDataLoader

# Optional Yahoo Finance fallback
try:
    from data_loader import MarketDataLoader
    YAHOO_AVAILABLE = True
except ImportError:
    YAHOO_AVAILABLE = False
    logging.warning("Yahoo Finance not available - using Zerodha only")

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_trading.log'),
        logging.StreamHandler()
    ]
)

class HybridTradingOrchestrator:
    """
    Main orchestrator for hybrid trading system
    Manages data collection, signal generation, and trade execution
    """
    
    def __init__(self, config_file: str = 'hybrid_config.json'):
        """Initialize orchestrator with configuration"""
        
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Initialize components
        self.strategy = HybridTradingStrategy(self.config.get('strategy', {}))
        
        # Use Zerodha as primary data source if enabled
        use_zerodha = self.config.get('data', {}).get('use_zerodha', True)
        if use_zerodha:
            self.data_loader = EnhancedHybridDataLoader(prefer_zerodha=True)
            logging.info("🚀 Using Zerodha as primary data source")
        elif YAHOO_AVAILABLE:
            self.data_loader = MarketDataLoader(self.config.get('data', {}))
            logging.info("📊 Using Yahoo Finance data source")
        else:
            # Fallback to Zerodha-only mode
            self.data_loader = EnhancedHybridDataLoader(prefer_zerodha=True)
            logging.warning("⚠️ Yahoo unavailable, using Zerodha-only mode")
        
        # Trading state
        self.is_running = False
        self.positions = {}
        self.portfolio_value = self.config.get('initial_capital', 250000)
        self.peak_portfolio_value = self.portfolio_value
        self.daily_pnl = 0
        
        # Portfolio tracking
        self.portfolio_history = []
        self.trade_log = []
        
        # Performance metrics
        self.total_signals = 0
        self.buy_signals = 0
        self.sell_signals = 0
        self.successful_trades = 0
        
        # Market state
        self.market_context = {}
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logging.info("🚀 Hybrid Trading Orchestrator initialized")
        logging.info(f"💰 Starting capital: ₹{self.portfolio_value:,.2f}")
        
    def update_trailing_stops(self):
        \"\"\"Update trailing stop losses for all positions\"\"\"
        for symbol, position in self.positions.items():
            if not position.get('trailing_stop_enabled', False):
                continue
                
            try:
                # Get current price
                current_data = self.data_loader.get_historical_data(symbol, period='1d', interval='1m')
                if current_data is None or len(current_data) == 0:
                    continue
                    
                current_price = float(current_data['close'].iloc[-1])
                entry_price = position['entry_price']
                highest_price = position.get('highest_price', entry_price)
                activation_percent = position.get('activation_percent', 0.015)
                trailing_percent = position.get('trailing_stop_percent', 0.02)
                
                # Update highest price
                if current_price > highest_price:
                    position['highest_price'] = current_price
                    highest_price = current_price
                
                # Check if trailing should be activated
                profit_percent = (current_price - entry_price) / entry_price
                if not position.get('trailing_activated', False) and profit_percent >= activation_percent:
                    position['trailing_activated'] = True
                    logging.info(f\"📈 TRAILING ACTIVATED for {symbol} at {profit_percent*100:.1f}% profit\")
                
                # Update trailing stop if activated
                if position.get('trailing_activated', False):
                    new_stop = highest_price * (1 - trailing_percent)
                    current_stop = position['stop_loss']
                    
                    # Only move stop up (for long positions)
                    if new_stop > current_stop:
                        position['stop_loss'] = new_stop
                        logging.info(f\"🔄 TRAILING STOP updated for {symbol}: ₹{current_stop:.2f} → ₹{new_stop:.2f}\")
                        
            except Exception as e:
                logging.error(f\"❌ Error updating trailing stop for {symbol}: {e}\")\n    \n    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            'initial_capital': 250000,
            'trading_hours': {
                'start': '09:15',
                'end': '15:30'
            },
            'analysis_interval': 900,  # 15 minutes
            'max_positions': 5,
            'paper_trading': True,
            'strategy': {
                'buy_threshold': 65,
                'sell_threshold': 35,
                'min_votes': 3,
                'max_risk_per_trade': 0.01,
                'enable_audit': True
            },
            'watchlist': [
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
                'ICICIBANK', 'KOTAKBANK', 'LT', 'ITC', 'AXISBANK'
            ]
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logging.info(f"✅ Configuration loaded from {config_file}")
            except Exception as e:
                logging.warning(f"Error loading config: {e}, using defaults")
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logging.info(f"📁 Created default config file: {config_file}")
            
        return default_config
    
    def is_market_open(self) -> bool:
        """Check if market is currently open (IST timezone)"""
        now_ist = datetime.now(IST).time()
        start_time = datetime.strptime(self.config['trading_hours']['start'], '%H:%M').time()
        end_time = datetime.strptime(self.config['trading_hours']['end'], '%H:%M').time()
        
        # Check if current time is within trading hours (IST)
        is_open = start_time <= now_ist <= end_time
        
        # Check if it's a weekday in IST (Monday = 0, Sunday = 6)
        is_weekday = datetime.now(IST).weekday() < 5
        
        return is_open and is_weekday
    
    def update_market_context(self):
        """Update market context for all symbols"""
        try:
            self.market_context = self.data_loader.get_market_context()
            logging.info(f"📊 Market context updated: VIX={self.market_context.get('vix', 0):.1f}, "
                        f"Breadth={self.market_context.get('market_breadth', 0):.2f}")
        except Exception as e:
            logging.error(f"Error updating market context: {e}")
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """Analyze single symbol and generate trading signal"""
        try:
            # Get historical data
            data = self.data_loader.get_historical_data(symbol, period='6mo', interval='15minute')
            
            if data is None or not self.data_loader.validate_data_quality(data):
                logging.warning(f"❌ Invalid data for {symbol}")
                return {'signal': 'HOLD', 'error': 'Invalid data'}
            
            # Prepare market data for strategy
            market_data = {
                'symbol': symbol,
                'vix': self.market_context.get('vix', 15),
                'sector_strength': self.market_context.get('sector_strength', {}),
                'market_breadth': self.market_context.get('market_breadth', 1.0),
                'account_equity': self.portfolio_value,
                'current_equity': self.portfolio_value,
                'peak_equity': self.peak_portfolio_value,
                'positions': list(self.positions.keys()),
                'correlation_matrix': pd.DataFrame()  # TODO: Add correlation matrix
            }
            
            # Generate trading signal
            signal_result = self.strategy.generate_trading_signal(data, market_data)
            
            if signal_result['success']:
                logging.info(f"📈 {symbol}: {signal_result['signal']} "
                           f"(Score: {signal_result['score']:.1f}, "
                           f"Votes: {signal_result['bullish_votes']}/4, "
                           f"Regime: {signal_result['regime']})")
            else:
                logging.warning(f"⚠️ {symbol}: Analysis failed - {signal_result.get('error', 'Unknown error')}")
            
            return signal_result
            
        except Exception as e:
            logging.error(f"Error analyzing {symbol}: {e}")
            return {'signal': 'HOLD', 'error': str(e), 'success': False}
    
    def execute_trade(self, symbol: str, signal_result: Dict) -> bool:
        """Execute trade based on signal (paper trading)"""
        try:
            signal = signal_result['signal']
            
            if signal == 'HOLD':
                return True
            
            position_size = signal_result.get('position_size', 0)
            price = signal_result.get('price', 0)
            
            if position_size == 0 or price == 0:
                logging.warning(f"❌ Invalid position size or price for {symbol}")
                return False
            
            # Paper trading execution
            if self.config.get('paper_trading', True):
                success = self.execute_paper_trade(symbol, signal, position_size, price, signal_result)
            else:
                # TODO: Implement real trading via broker API
                success = self.execute_real_trade(symbol, signal, position_size, price, signal_result)
            
            if success:
                self.total_signals += 1
                if signal == 'BUY':
                    self.buy_signals += 1
                elif signal == 'SELL':
                    self.sell_signals += 1
            
            return success
            
        except Exception as e:
            logging.error(f"Error executing trade for {symbol}: {e}")
            return False
    
    def execute_paper_trade(self, symbol: str, signal: str, quantity: int, 
                           price: float, signal_result: Dict) -> bool:
        """Execute paper trade (simulation)"""
        try:
            trade_value = quantity * price
            transaction_cost = signal_result['risk_metrics'].get('transaction_cost', 0)
            
            if signal == 'BUY':
                # Check if we have enough capital
                total_cost = trade_value + transaction_cost
                if total_cost > self.portfolio_value * 0.8:  # Keep 20% cash
                    logging.warning(f"💸 Insufficient capital for {symbol} BUY: Need ₹{total_cost:,.2f}")
                    return False
                
                # Check position limits
                if len(self.positions) >= self.config.get('max_positions', 5):
                    logging.warning(f"📊 Maximum positions reached, skipping {symbol} BUY")
                    return False
                
                # Execute BUY
                # Get trailing stop parameters from config
                strategy_config = self.config.get('strategy', {})
                trailing_enabled = strategy_config.get('trailing_stop_enabled', True)
                trailing_percent = strategy_config.get('trailing_stop_percent', 2.0)
                activation_percent = strategy_config.get('trailing_stop_activation_percent', 1.5)
                original_stop = signal_result['risk_metrics'].get('stop_loss', price * 0.95)
                
                self.positions[symbol] = {
                    'quantity': quantity,
                    'entry_price': price,
                    'entry_time': datetime.now(IST),
                    'stop_loss': original_stop,
                    'original_stop_loss': original_stop,
                    'take_profit': signal_result['risk_metrics'].get('take_profit', 0),
                    'signal_data': signal_result,
                    'trailing_stop_enabled': trailing_enabled,
                    'trailing_stop_percent': trailing_percent / 100,
                    'activation_percent': activation_percent / 100,
                    'highest_price': price,
                    'trailing_activated': False
                }
                
                self.portfolio_value -= total_cost
                
                logging.info(f"✅ BUY {quantity} {symbol} @ ₹{price:.2f} "
                           f"(Value: ₹{trade_value:,.2f}, Cost: ₹{transaction_cost:.2f})")
                
            elif signal == 'SELL':
                # Check if we have the position
                if symbol not in self.positions:
                    logging.warning(f"❌ No position to sell for {symbol}")
                    return False
                
                position = self.positions[symbol]
                
                # Execute SELL
                sell_value = quantity * price - transaction_cost
                entry_value = position['quantity'] * position['entry_price']
                pnl = sell_value - entry_value
                
                self.portfolio_value += sell_value
                self.daily_pnl += pnl
                
                # Update peak portfolio value
                if self.portfolio_value > self.peak_portfolio_value:
                    self.peak_portfolio_value = self.portfolio_value
                
                # Log trade result
                self.trade_log.append({
                    'symbol': symbol,
                    'entry_time': position['entry_time'],
                    'exit_time': datetime.now(IST),
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'return_pct': (pnl / entry_value) * 100
                })
                
                # Update strategy with trade result
                trade_id = f"{symbol}_{position['entry_time'].strftime('%Y%m%d_%H%M%S')}"
                self.strategy.update_trade_result(trade_id, pnl, price)
                
                if pnl > 0:
                    self.successful_trades += 1
                
                logging.info(f"✅ SELL {quantity} {symbol} @ ₹{price:.2f} "
                           f"(P&L: ₹{pnl:,.2f}, Return: {(pnl/entry_value)*100:.2f}%)")
                
                # Remove position
                del self.positions[symbol]
            
            # Log portfolio state
            self.log_portfolio_state()
            
            return True
            
        except Exception as e:
            logging.error(f"Paper trading error for {symbol}: {e}")
            return False
    
    def execute_real_trade(self, symbol: str, signal: str, quantity: int, 
                          price: float, signal_result: Dict) -> bool:
        """Execute real trade via Zerodha API"""
        try:
            # Check if we have Zerodha data loader with trading capabilities
            if not hasattr(self.data_loader, 'loaders') or 'zerodha' not in self.data_loader.loaders:
                logging.error("❌ Zerodha not available for real trading")
                return False
            
            zerodha_loader = self.data_loader.loaders['zerodha']
            
            if not zerodha_loader.kite:
                logging.error("❌ Zerodha not authenticated for real trading")
                return False
            
            # Place order through Zerodha
            order_result = zerodha_loader.place_order(
                symbol=symbol,
                quantity=quantity, 
                order_type=signal,  # BUY or SELL
                price=None,  # Market order
                product='MIS'  # Intraday
            )
            
            if order_result.get('success'):
                order_id = order_result['order_id']
                logging.info(f"✅ REAL ORDER PLACED: {signal} {quantity} {symbol} - Order ID: {order_id}")
                
                # Update position tracking
                if signal == 'BUY':
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': datetime.now(IST),
                        'order_id': order_id,
                        'signal_info': signal_result,
                        'stop_loss': price * 0.98,  # 2% stop loss
                        'take_profit': price * 1.04  # 4% take profit
                    }
                    self.portfolio_value -= (price * quantity)
                    
                elif signal == 'SELL' and symbol in self.positions:
                    position = self.positions[symbol]
                    pnl = (price - position['entry_price']) * quantity
                    self.portfolio_value += (price * quantity)
                    self.daily_pnl += pnl
                    
                    if pnl > 0:
                        self.successful_trades += 1
                    
                    # Log the completed trade
                    self.trade_log.append({
                        'symbol': symbol,
                        'action': 'CLOSE',
                        'quantity': quantity,
                        'entry_price': position['entry_price'],
                        'exit_price': price,
                        'pnl': pnl,
                        'hold_time': datetime.now(IST) - position['entry_time'],
                        'order_id': order_id,
                        'timestamp': datetime.now(IST)
                    })
                    
                    del self.positions[symbol]
                
                # Update counters
                if signal == 'BUY':
                    self.buy_signals += 1
                elif signal == 'SELL':
                    self.sell_signals += 1
                
                self.total_signals += 1
                return True
                
            else:
                logging.error(f"❌ Order failed: {order_result.get('error')}")
                return False
                
        except Exception as e:
            logging.error(f"Real trading error for {symbol}: {e}")
            return False
    
    def check_stop_loss_take_profit(self):
        """Check and execute stop loss / take profit orders"""
        # Update trailing stops first
        self.update_trailing_stops()
        
        for symbol, position in list(self.positions.items()):
            try:
                # Get current price
                current_data = self.data_loader.get_historical_data(symbol, period='1d', interval='1m')
                if current_data is None or len(current_data) == 0:
                    continue
                    
                current_price = current_data['close'].iloc[-1]
                entry_price = position['entry_price']
                stop_loss = position['stop_loss']
                take_profit = position['take_profit']
                
                # Check stop loss
                if stop_loss > 0 and current_price <= stop_loss:
                    logging.info(f"🛑 Stop loss triggered for {symbol} @ ₹{current_price:.2f}")
                    signal_result = {'risk_metrics': {'transaction_cost': current_price * position['quantity'] * 0.001}}
                    
                    if self.config.get('paper_trading', True):
                        self.execute_paper_trade(symbol, 'SELL', position['quantity'], current_price, signal_result)
                    else:
                        self.execute_real_trade(symbol, 'SELL', position['quantity'], current_price, signal_result)
                    continue
                
                # Check take profit
                if take_profit > 0 and current_price >= take_profit:
                    logging.info(f"🎯 Take profit triggered for {symbol} @ ₹{current_price:.2f}")
                    signal_result = {'risk_metrics': {'transaction_cost': current_price * position['quantity'] * 0.001}}
                    
                    if self.config.get('paper_trading', True):
                        self.execute_paper_trade(symbol, 'SELL', position['quantity'], current_price, signal_result)
                    else:
                        self.execute_real_trade(symbol, 'SELL', position['quantity'], current_price, signal_result)
                    
            except Exception as e:
                logging.error(f"Error checking stop/profit for {symbol}: {e}")
    
    def log_portfolio_state(self):
        """Log current portfolio state"""
        total_value = self.portfolio_value
        
        # Calculate position values
        position_value = 0
        for symbol, position in self.positions.items():
            try:
                current_data = self.data_loader.get_historical_data(symbol, period='1d', interval='1m')
                if current_data is not None and len(current_data) > 0:
                    current_price = current_data['close'].iloc[-1]
                    pos_value = position['quantity'] * current_price
                    position_value += pos_value
                    total_value += pos_value - (position['quantity'] * position['entry_price'])
            except:
                continue
        
        # Calculate daily return
        initial_value = self.config.get('initial_capital', 250000)
        total_return = ((total_value - initial_value) / initial_value) * 100
        
        # Update peak value
        if total_value > self.peak_portfolio_value:
            self.peak_portfolio_value = total_value
        
        # Calculate drawdown
        drawdown = ((self.peak_portfolio_value - total_value) / self.peak_portfolio_value) * 100
        
        logging.info(f"💼 Portfolio: Cash=₹{self.portfolio_value:,.2f}, "
                    f"Positions={len(self.positions)}, "
                    f"Total=₹{total_value:,.2f}, "
                    f"Return={total_return:.2f}%, "
                    f"Drawdown={drawdown:.2f}%")
    
    def generate_daily_report(self):
        """Generate daily performance report"""
        try:
            report = {
                'date': datetime.now(IST).strftime('%Y-%m-%d'),
                'portfolio_value': self.portfolio_value,
                'positions': len(self.positions),
                'daily_pnl': self.daily_pnl,
                'total_signals': self.total_signals,
                'buy_signals': self.buy_signals,
                'sell_signals': self.sell_signals,
                'successful_trades': self.successful_trades,
                'win_rate': (self.successful_trades / max(1, len(self.trade_log))) * 100,
                'market_context': self.market_context
            }
            
            # Save report
            report_file = f"daily_reports/report_{datetime.now(IST).strftime('%Y%m%d')}.json"
            os.makedirs('daily_reports', exist_ok=True)
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logging.info(f"📊 Daily report saved: {report_file}")
            
            # Print summary
            logging.info("=" * 60)
            logging.info("📈 DAILY TRADING SUMMARY")
            logging.info("=" * 60)
            logging.info(f"💰 Portfolio Value: ₹{self.portfolio_value:,.2f}")
            logging.info(f"📊 Active Positions: {len(self.positions)}")
            logging.info(f"📈 Daily P&L: ₹{self.daily_pnl:,.2f}")
            logging.info(f"🎯 Signals Generated: {self.total_signals} (Buy: {self.buy_signals}, Sell: {self.sell_signals})")
            logging.info(f"✅ Win Rate: {report['win_rate']:.1f}%")
            logging.info("=" * 60)
            
        except Exception as e:
            logging.error(f"Error generating daily report: {e}")
    
    def trading_loop(self):
        """Main trading loop"""
        logging.info("🎯 Starting trading loop...")
        
        last_analysis = datetime.min
        analysis_interval = timedelta(seconds=self.config.get('analysis_interval', 900))
        
        while self.is_running:
            try:
                current_time = datetime.now(IST)
                
                # Check if market is open
                if not self.is_market_open():
                    logging.info("💤 Market is closed, sleeping...")
                    time.sleep(60)  # Check every minute
                    continue
                
                # Check stop loss / take profit
                self.check_stop_loss_take_profit()
                
                # Perform analysis at intervals
                if current_time - last_analysis >= analysis_interval:
                    logging.info(f"🔍 Running analysis cycle at {current_time.strftime('%H:%M:%S')}")
                    
                    # Update market context
                    self.update_market_context()
                    
                    # Analyze watchlist
                    watchlist = self.config.get('watchlist', [])
                    
                    for symbol in watchlist:
                        if not self.is_running:  # Check if we should stop
                            break
                            
                        signal_result = self.analyze_symbol(symbol)
                        
                        if signal_result.get('success', False):
                            self.execute_trade(symbol, signal_result)
                        
                        time.sleep(2)  # Small delay between symbols
                    
                    last_analysis = current_time
                    
                    # Log portfolio state
                    self.log_portfolio_state()
                
                # Sleep until next cycle
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logging.error(f"Error in trading loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def start_trading(self):
        """Start the trading system"""
        if self.is_running:
            logging.warning("⚠️ Trading system is already running")
            return
            
        self.is_running = True
        logging.info("🚀 Starting Hybrid Trading System")
        logging.info(f"📊 Watchlist: {', '.join(self.config.get('watchlist', []))}")
        logging.info(f"💰 Initial Capital: ₹{self.portfolio_value:,.2f}")
        logging.info(f"📈 Strategy: Hybrid (Technical + Price Action + Patterns + Market Context)")
        
        # Start trading in a separate thread
        trading_thread = Thread(target=self.trading_loop, daemon=True)
        trading_thread.start()
        
        logging.info("✅ Trading system started successfully")
        
        return trading_thread
    
    def stop_trading(self):
        """Stop the trading system"""
        if not self.is_running:
            logging.warning("⚠️ Trading system is not running")
            return
            
        logging.info("🛑 Stopping trading system...")
        self.is_running = False
        
        # Generate final report
        self.generate_daily_report()
        
        logging.info("✅ Trading system stopped successfully")
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        logging.info(f"📨 Received signal {sig}, shutting down...")
        self.stop_trading()
        sys.exit(0)

def main():
    """Main entry point"""
    print("🚀 Hybrid Trading System v1.0")
    print("=" * 50)
    print("⚡ NO MACHINE LEARNING REQUIRED")
    print("📈 Technical + Price Action + Patterns + Market Context")
    print("=" * 50)
    
    try:
        # Create orchestrator
        orchestrator = HybridTradingOrchestrator()
        
        # Start trading
        trading_thread = orchestrator.start_trading()
        
        # Keep main thread alive
        try:
            while orchestrator.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("🛑 Keyboard interrupt received")
            orchestrator.stop_trading()
            
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()