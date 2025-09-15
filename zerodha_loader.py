"""
Zerodha Kite Connect Integration for Perfect Trader
Real-time data and order execution for Indian markets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import os
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException
import pyotp
import pytz

# Force IST timezone for all operations
IST = pytz.timezone('Asia/Kolkata')

logging.basicConfig(level=logging.INFO)

class ZerodhaDataLoader:
    """
    Zerodha Kite Connect integration for real-time data and trading
    Provides the most reliable data source for Indian markets
    """
    
    def __init__(self, config_file: str = 'zerodha_config.json'):
        """
        Initialize Zerodha connection
        """
        self.config = self.load_config(config_file)
        self.kite = None
        self.access_token = None
        self.instrument_tokens = {}  # Symbol to instrument_token mapping
        
        # Initialize Kite Connect
        if self.config:
            self.initialize_kite()
            logging.info("🚀 Zerodha loader initialized")
        else:
            logging.error("❌ Zerodha config not found. Please setup credentials.")
    
    def load_config(self, config_file: str) -> Dict:
        """Load Zerodha credentials and settings"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create template config file
                template_config = {
                    "api_key": "your_api_key_here",
                    "api_secret": "your_api_secret_here",
                    "totp_key": "your_totp_key_here", 
                    "user_id": "your_user_id_here",
                    "password": "your_password_here",
                    "access_token": "",
                    "request_token": "",
                    "settings": {
                        "auto_login": True,
                        "cache_instruments": True,
                        "default_exchange": "NSE"
                    }
                }
                
                with open(config_file, 'w') as f:
                    json.dump(template_config, f, indent=2)
                
                logging.warning(f"📝 Created template config file: {config_file}")
                logging.warning("Please update with your Zerodha credentials")
                return None
                
        except Exception as e:
            logging.error(f"Error loading Zerodha config: {e}")
            return None
    
    def initialize_kite(self) -> bool:
        """
        Initialize Kite Connect session
        """
        try:
            # Create KiteConnect instance
            self.kite = KiteConnect(api_key=self.config['api_key'])
            
            # Try to use existing access token
            if self.config.get('access_token'):
                self.kite.set_access_token(self.config['access_token'])
                
                # Test connection
                try:
                    profile = self.kite.profile()
                    logging.info(f"✅ Connected to Zerodha as {profile['user_name']}")
                    return True
                except:
                    logging.warning("Stored access token invalid, need to re-authenticate")
            
            # Generate new access token if needed
            return self.authenticate()
            
        except Exception as e:
            logging.error(f"Kite initialization error: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Zerodha and get access token
        """
        try:
            # Step 1: Get login URL
            login_url = self.kite.login_url()
            logging.info(f"🔐 Login URL: {login_url}")
            
            # For automated login (if TOTP key provided)
            if self.config.get('totp_key'):
                return self.auto_authenticate()
            else:
                # Manual authentication
                return self.manual_authenticate()
                
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return False
    
    def auto_authenticate(self) -> bool:
        """
        Automated authentication using TOTP
        """
        try:
            import requests
            from urllib.parse import urlparse, parse_qs
            
            # Generate TOTP
            totp = pyotp.TOTP(self.config['totp_key'])
            current_otp = totp.now()
            
            # Session for maintaining cookies
            session = requests.Session()
            
            # Step 1: Login to Kite
            login_data = {
                'user_id': self.config['user_id'],
                'password': self.config['password']
            }
            
            response = session.post('https://kite.zerodha.com/api/login', data=login_data)
            
            if response.status_code != 200:
                logging.error("Login failed at first step")
                return False
            
            # Step 2: Submit TOTP
            totp_data = {
                'user_id': self.config['user_id'],
                'request_id': response.json()['data']['request_id'],
                'twofa_value': current_otp,
                'twofa_type': 'totp'
            }
            
            response = session.post('https://kite.zerodha.com/api/twofa', data=totp_data)
            
            if response.status_code != 200:
                logging.error("TOTP verification failed")
                return False
            
            # Step 3: Extract request token from redirect
            # This requires browser automation or manual intervention
            logging.warning("⚠️ Automated login partially implemented")
            logging.warning("Please complete manual authentication for first time setup")
            
            return self.manual_authenticate()
            
        except Exception as e:
            logging.error(f"Auto authentication error: {e}")
            return self.manual_authenticate()
    
    def manual_authenticate(self) -> bool:
        """
        Manual authentication - user provides request token
        """
        try:
            login_url = self.kite.login_url()
            print("\n🔐 ZERODHA AUTHENTICATION REQUIRED")
            print("=" * 60)
            print(f"1. Open this URL in browser: {login_url}")
            print("2. Login with your Zerodha credentials")
            print("3. Copy the 'request_token' from the redirect URL")
            print("   (URL will look like: https://127.0.0.1:8080/?request_token=XXXXX&action=login&status=success)")
            
            request_token = input("\n📝 Enter request_token: ").strip()
            
            if not request_token:
                logging.error("No request token provided")
                return False
            
            # Generate access token
            data = self.kite.generate_session(request_token, 
                                            api_secret=self.config['api_secret'])
            
            # Save access token
            self.access_token = data['access_token']
            self.config['access_token'] = self.access_token
            self.config['request_token'] = request_token
            
            # Save updated config
            with open('zerodha_config.json', 'w') as f:
                json.dump(self.config, f, indent=2)
            
            # Set access token in kite
            self.kite.set_access_token(self.access_token)
            
            # Test connection
            profile = self.kite.profile()
            logging.info(f"✅ Successfully authenticated as {profile['user_name']}")
            
            return True
            
        except Exception as e:
            logging.error(f"Manual authentication error: {e}")
            return False
    
    def load_instruments(self) -> bool:
        """
        Load instrument list and create symbol mappings
        """
        try:
            # Download instruments
            instruments = self.kite.instruments("NSE")
            
            # Create symbol to instrument_token mapping
            self.instrument_tokens = {}
            
            for instrument in instruments:
                symbol = instrument['tradingsymbol']
                self.instrument_tokens[symbol] = instrument['instrument_token']
            
            logging.info(f"📊 Loaded {len(self.instrument_tokens)} NSE instruments")
            
            # Cache instruments for faster startup
            if self.config.get('settings', {}).get('cache_instruments', True):
                with open('instruments_cache.json', 'w') as f:
                    json.dump(self.instrument_tokens, f)
            
            return True
            
        except Exception as e:
            logging.error(f"Error loading instruments: {e}")
            return False
    
    def get_instrument_token(self, symbol: str) -> Optional[int]:
        """Get instrument token for symbol"""
        if not self.instrument_tokens:
            self.load_instruments()
        
        return self.instrument_tokens.get(symbol)
    
    def get_historical_data(self, symbol: str, period: str = '60day', 
                           interval: str = '15minute') -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data from Zerodha
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            period: Data period (day, 60day, etc.)
            interval: minute, 3minute, 5minute, 15minute, 30minute, 60minute, day
        """
        try:
            if not self.kite:
                logging.error("Kite not initialized")
                return None
            
            # Get instrument token
            instrument_token = self.get_instrument_token(symbol)
            if not instrument_token:
                logging.error(f"Instrument token not found for {symbol}")
                return None
            
            # Calculate date range
            to_date = datetime.now(IST)
            
            if period == '60day':
                from_date = to_date - timedelta(days=60)
            elif period == '30day':
                from_date = to_date - timedelta(days=30)
            elif period == '7day':
                from_date = to_date - timedelta(days=7)
            else:
                from_date = to_date - timedelta(days=30)  # default
            
            # Fetch data
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if not data:
                logging.warning(f"No data received for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Rename columns to match our system
            df = df.rename(columns={
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            logging.info(f"✅ Fetched {len(df)} bars for {symbol} from Zerodha")
            
            return df
            
        except KiteException as e:
            logging.error(f"Kite API error for {symbol}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error fetching {symbol} data: {e}")
            return None
    
    def get_quote(self, symbols: List[str]) -> Dict:
        """
        Get real-time quotes for multiple symbols
        """
        try:
            if not self.kite:
                return {}
            
            # Convert symbols to instrument tokens
            instruments = []
            for symbol in symbols:
                token = self.get_instrument_token(symbol)
                if token:
                    instruments.append(f"NSE:{symbol}")
            
            if not instruments:
                logging.warning("No valid instruments for quotes")
                return {}
            
            # Get quotes
            quotes = self.kite.quote(instruments)
            
            # Format response
            result = {}
            for instrument, quote_data in quotes.items():
                symbol = instrument.split(':')[-1]  # Extract symbol from NSE:SYMBOL
                result[symbol] = {
                    'price': quote_data['last_price'],
                    'change': quote_data['net_change'],
                    'change_percent': quote_data['net_change'] / quote_data['last_price'] * 100,
                    'volume': quote_data['volume'],
                    'high': quote_data['ohlc']['high'],
                    'low': quote_data['ohlc']['low'],
                    'open': quote_data['ohlc']['open'],
                    'close': quote_data['ohlc']['close']
                }
            
            return result
            
        except Exception as e:
            logging.error(f"Error getting quotes: {e}")
            return {}
    
    def get_market_context(self) -> Dict:
        """
        Get market context data from Zerodha
        """
        try:
            context = {
                'vix': 15.0,  # Default
                'nifty_trend': 'neutral',
                'market_breadth': 1.0,
                'sector_strength': {}
            }
            
            # Get Nifty 50 quote
            nifty_quotes = self.kite.quote(["NSE:NIFTY 50"])
            if nifty_quotes:
                nifty_data = list(nifty_quotes.values())[0]
                nifty_change = nifty_data['net_change'] / nifty_data['last_price'] * 100
                
                if nifty_change > 0.5:
                    context['nifty_trend'] = 'bullish'
                elif nifty_change < -0.5:
                    context['nifty_trend'] = 'bearish'
            
            # Get Bank Nifty for sector strength
            bank_quotes = self.kite.quote(["NSE:BANKNIFTY"])
            if bank_quotes:
                bank_data = list(bank_quotes.values())[0]
                bank_change = bank_data['net_change'] / bank_data['last_price'] * 100
                context['sector_strength']['banking'] = bank_change / 100
            
            # Try to get India VIX
            try:
                vix_quotes = self.kite.quote(["NSE:INDIAVIX"])
                if vix_quotes:
                    vix_data = list(vix_quotes.values())[0]
                    context['vix'] = vix_data['last_price']
            except:
                pass  # Keep default VIX
            
            return context
            
        except Exception as e:
            logging.error(f"Error getting market context: {e}")
            return {'vix': 15.0, 'nifty_trend': 'neutral', 'market_breadth': 1.0, 'sector_strength': {}}
    
    def place_order(self, symbol: str, quantity: int, order_type: str = 'BUY', 
                    price: float = None, product: str = 'MIS') -> Dict:
        """
        Place order through Zerodha
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            order_type: BUY or SELL
            price: Limit price (None for market order)
            product: MIS (intraday), CNC (delivery), NRML (normal)
        """
        try:
            if not self.kite:
                return {'success': False, 'error': 'Kite not initialized'}
            
            # Prepare order parameters
            order_params = {
                'exchange': self.kite.EXCHANGE_NSE,
                'tradingsymbol': symbol,
                'transaction_type': self.kite.TRANSACTION_TYPE_BUY if order_type == 'BUY' else self.kite.TRANSACTION_TYPE_SELL,
                'quantity': quantity,
                'product': product,
                'order_type': self.kite.ORDER_TYPE_MARKET if price is None else self.kite.ORDER_TYPE_LIMIT,
                'validity': self.kite.VALIDITY_DAY
            }
            
            # Add price for limit orders
            if price is not None:
                order_params['price'] = price
            
            # Place order
            order_id = self.kite.place_order(**order_params)
            
            logging.info(f"✅ Order placed: {order_type} {quantity} {symbol} - Order ID: {order_id}")
            
            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'order_type': order_type,
                'price': price
            }
            
        except KiteException as e:
            logging.error(f"Order placement error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logging.error(f"Unexpected order error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            if not self.kite:
                return []
            
            positions = self.kite.positions()
            
            # Filter for open positions
            open_positions = []
            for pos in positions['net']:
                if pos['quantity'] != 0:
                    open_positions.append({
                        'symbol': pos['tradingsymbol'],
                        'quantity': pos['quantity'],
                        'average_price': pos['average_price'],
                        'pnl': pos['pnl'],
                        'product': pos['product']
                    })
            
            return open_positions
            
        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self) -> List[Dict]:
        """Get order history"""
        try:
            if not self.kite:
                return []
            
            orders = self.kite.orders()
            return orders
            
        except Exception as e:
            logging.error(f"Error getting orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            if not self.kite:
                return False
            
            self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=order_id)
            logging.info(f"✅ Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error cancelling order {order_id}: {e}")
            return False


# Integration with existing system
class EnhancedHybridDataLoader:
    """
    Enhanced data loader with Zerodha as primary source
    """
    
    def __init__(self, prefer_zerodha: bool = True):
        """Initialize with Zerodha preference"""
        self.prefer_zerodha = prefer_zerodha
        self.loaders = {}
        
        # Initialize Zerodha loader
        if prefer_zerodha:
            try:
                self.loaders['zerodha'] = ZerodhaDataLoader()
                if self.loaders['zerodha'].kite:
                    logging.info("🚀 Zerodha loader ready - REAL-TIME DATA ENABLED")
                else:
                    logging.warning("⚠️ Zerodha authentication failed, falling back to Yahoo")
                    self.prefer_zerodha = False
            except Exception as e:
                logging.error(f"Zerodha initialization failed: {e}")
                self.prefer_zerodha = False
        
        # No fallback loaders - Zerodha only
        logging.info("📊 Zerodha-only mode enabled")
    
    def get_historical_data(self, symbol: str, **kwargs) -> Optional[pd.DataFrame]:
        """Get data with intelligent source selection"""
        
        # Try Zerodha first if available
        if self.prefer_zerodha and 'zerodha' in self.loaders:
            try:
                data = self.loaders['zerodha'].get_historical_data(symbol, **kwargs)
                if data is not None and len(data) > 0:
                    logging.info(f"✅ Got {symbol} data from Zerodha (real-time)")
                    return data
            except Exception as e:
                logging.warning(f"Zerodha failed for {symbol}, trying Yahoo: {e}")
        
        # No fallback - return None if Zerodha fails
        logging.error(f"❌ Failed to get data for {symbol} - Zerodha only mode")
        
        return None
    
    def validate_data_quality(self, data: pd.DataFrame) -> bool:
        """
        Validate the quality of fetched data
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            True if data quality is acceptable, False otherwise
        """
        if data is None or data.empty:
            return False
        
        # Check for minimum required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            return False
        
        # Check for minimum data points (at least 20 for technical indicators)
        if len(data) < 20:
            return False
        
        # Check for NaN values in critical columns
        if data[['open', 'high', 'low', 'close']].isnull().any().any():
            return False
        
        # Check for invalid price values
        if (data[['open', 'high', 'low', 'close']] <= 0).any().any():
            return False
        
        # Check for proper OHLC relationships
        if not ((data['high'] >= data['low']).all() and 
                (data['high'] >= data['open']).all() and 
                (data['high'] >= data['close']).all()):
            return False
        
        return True
    
    def get_market_context(self) -> Dict:
        """Get market context with Zerodha preference"""
        if self.prefer_zerodha and 'zerodha' in self.loaders:
            try:
                return self.loaders['zerodha'].get_market_context()
            except Exception as e:
                logging.warning(f"Zerodha market context failed: {e}")
        
        # No fallback - use default values
        
        return {'vix': 15.0, 'nifty_trend': 'neutral', 'market_breadth': 1.0, 'sector_strength': {}}
    


if __name__ == "__main__":
    print("🚀 Testing Zerodha Integration...")
    
    # Test Zerodha loader
    loader = ZerodhaDataLoader()
    
    if loader.kite:
        print("✅ Zerodha connected successfully!")
        
        # Test data fetch
        data = loader.get_historical_data('RELIANCE', period='7day', interval='15minute')
        if data is not None:
            print(f"✅ Fetched {len(data)} RELIANCE bars")
            print(f"Latest price: ₹{data['close'].iloc[-1]:.2f}")
        
        # Test quotes
        quotes = loader.get_quote(['RELIANCE', 'TCS'])
        if quotes:
            print(f"✅ Real-time quotes:")
            for symbol, quote in quotes.items():
                print(f"  {symbol}: ₹{quote['price']:.2f} ({quote['change_percent']:+.2f}%)")
        
        # Test positions
        positions = loader.get_positions()
        print(f"📊 Current positions: {len(positions)}")
        
    else:
        print("❌ Zerodha authentication failed")
        print("Please check your credentials in zerodha_config.json")
    
    print("\n🔄 Testing Enhanced Hybrid Loader...")
    hybrid = EnhancedHybridDataLoader(prefer_zerodha=True)
    
    test_data = hybrid.get_historical_data('TCS', period='30day', interval='15minute')
    if test_data is not None:
        print(f"✅ Hybrid loader got {len(test_data)} TCS bars")
    else:
        print("❌ Hybrid loader failed")