"""
Stock Market Data Integration Tool
"""
import sqlite3
import yfinance as yf # type: ignore
import pandas as pd # type: ignore
from typing import Dict, List, Any
from datetime import datetime, timedelta
import asyncio

class StockDataTool:
    def __init__(self):
        self.db_path = "data/stock_data.db"
        self.init_database()
        
        # Sector stock mappings
        self.sector_stocks = {
            'technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA'],
            'healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'TMO'],
            'finance': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
            'energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG']
        }
    
    def init_database(self):
        """Initialize SQLite database for stock data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY,
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                market_cap REAL,
                pe_ratio REAL,
                updated_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sector_analysis (
                id INTEGER PRIMARY KEY,
                sector TEXT,
                analysis_date TEXT,
                avg_performance REAL,
                top_performer TEXT,
                analysis_summary TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_stock_data(self, ticker: str) -> Dict[str, Any]:
        """Get basic stock data (sync version for LangChain tool)"""
        return asyncio.run(self.get_stock_data_async(ticker))
    
    async def get_stock_data_async(self, ticker: str) -> Dict[str, Any]:
        """Get stock data asynchronously"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="3mo")
            
            if hist.empty:
                return {"error": f"No data found for ticker {ticker}"}
            
            latest_price = hist['Close'].iloc[-1]
            
            stock_data = {
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'price': float(latest_price),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'high_52w': float(hist['High'].max()),
                'low_52w': float(hist['Low'].min()),
                'volume': int(hist['Volume'].iloc[-1]),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown')
            }
            
            # Store in database
            self._store_stock_data(stock_data)
            
            return stock_data
            
        except Exception as e:
            return {"error": f"Error fetching data for {ticker}: {str(e)}"}
    
    async def analyze_sector_stocks(self, sector: str) -> Dict[str, Any]:
        """Analyze stocks in a specific sector"""
        
        if sector not in self.sector_stocks:
            return {"error": f"Sector {sector} not supported"}
        
        sector_tickers = self.sector_stocks[sector]
        sector_data = []
        
        print(f"    📈 Analyzing {len(sector_tickers)} stocks in {sector} sector...")
        
        for ticker in sector_tickers:
            stock_data = await self.get_stock_data_async(ticker)
            if 'error' not in stock_data:
                sector_data.append(stock_data)
        
        if not sector_data:
            return {"error": f"No data available for {sector} sector"}
        
        # Calculate sector metrics
        total_market_cap = sum(s['market_cap'] for s in sector_data if s['market_cap'])
        avg_pe_ratio = sum(s['pe_ratio'] for s in sector_data if s['pe_ratio']) / len(sector_data)
        
        # Find best and worst performers (3-month basis)
        best_performer = max(sector_data, key=lambda x: x['price'])
        worst_performer = min(sector_data, key=lambda x: x['price'])
        
        analysis = {
            'sector': sector,
            'total_stocks_analyzed': len(sector_data),
            'total_market_cap': total_market_cap,
            'average_pe_ratio': avg_pe_ratio,
            'best_performer': {
                'ticker': best_performer['ticker'],
                'name': best_performer['name'],
                'price': best_performer['price']
            },
            'worst_performer': {
                'ticker': worst_performer['ticker'], 
                'name': worst_performer['name'],
                'price': worst_performer['price']
            },
            'stocks': sector_data,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Store sector analysis
        self._store_sector_analysis(analysis)
        
        return analysis
    
    async def get_detailed_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get detailed stock analysis with scoring"""
        
        stock_data = await self.get_stock_data_async(ticker)
        if 'error' in stock_data:
            return stock_data
        
        # Calculate analysis score (simplified)
        score = 5  # Base score
        
        # PE ratio scoring
        if stock_data['pe_ratio'] > 0:
            if stock_data['pe_ratio'] < 15:
                score += 2
            elif stock_data['pe_ratio'] < 25:
                score += 1
            else:
                score -= 1
        
        # Market cap scoring
        if stock_data['market_cap'] > 100_000_000_000:  # 100B+
            score += 2
        elif stock_data['market_cap'] > 10_000_000_000:  # 10B+
            score += 1
        
        # Price position scoring (simplified)
        price_range = stock_data['high_52w'] - stock_data['low_52w']
        current_position = (stock_data['price'] - stock_data['low_52w']) / price_range
        
        if current_position > 0.8:
            score += 1
        elif current_position < 0.2:
            score -= 1
        
        stock_data['analysis_score'] = min(10, max(1, score))
        
        return stock_data
    
    def _store_stock_data(self, stock_data: Dict):
        """Store stock data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO stock_data 
            (ticker, date, open, high, low, close, volume, market_cap, pe_ratio, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            stock_data['ticker'],
            datetime.now().strftime('%Y-%m-%d'),
            stock_data['price'],  # Using current price as open
            stock_data['high_52w'],
            stock_data['low_52w'],
            stock_data['price'],
            stock_data['volume'],
            stock_data['market_cap'],
            stock_data['pe_ratio'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _store_sector_analysis(self, analysis: Dict):
        """Store sector analysis in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        summary = f"Analyzed {analysis['total_stocks_analyzed']} stocks. Best: {analysis['best_performer']['ticker']}, Avg PE: {analysis['average_pe_ratio']:.2f}"
        
        cursor.execute('''
            INSERT INTO sector_analysis 
            (sector, analysis_date, avg_performance, top_performer, analysis_summary)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            analysis['sector'],
            datetime.now().strftime('%Y-%m-%d'),
            analysis['average_pe_ratio'],
            analysis['best_performer']['ticker'],
            summary
        ))
        
        conn.commit()
        conn.close()