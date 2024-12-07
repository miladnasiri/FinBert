from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import math
from typing import Dict, Any

app = FastAPI(title="Financial Analysis API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FinBERT
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

def clean_float(value: Any) -> float:
    """Clean float values for JSON serialization"""
    if value is None or math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators"""
    try:
        # Ensure data is numeric
        price_series = pd.to_numeric(df['Close'], errors='coerce')
        
        # Moving Averages
        df['MA20'] = price_series.rolling(window=20).mean()
        df['MA50'] = price_series.rolling(window=50).mean()
        
        # RSI
        df['RSI'] = ta.momentum.RSIIndicator(price_series).rsi()
        
        # MACD
        macd = ta.trend.MACD(price_series)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(price_series)
        df['BB_upper'] = bollinger.bollinger_hband()
        df['BB_lower'] = bollinger.bollinger_lband()
        
        # Clean NaN values
        df = df.fillna(method='ffill').fillna(0)
        
        # Convert all numeric columns to float
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = df[col].apply(clean_float)
            
        return df
    except Exception as e:
        print(f"Error calculating technical indicators: {str(e)}")
        return df

def calculate_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate financial metrics"""
    try:
        returns = df['Close'].pct_change().dropna()
        
        metrics = {
            'daily_returns': clean_float(returns.mean()),
            'annual_returns': clean_float(returns.mean() * 252),
            'volatility': clean_float(returns.std() * np.sqrt(252)),
            'max_drawdown': clean_float(((df['Close'].cummax() - df['Close'])/df['Close'].cummax()).max()),
        }
        
        # Sharpe Ratio (assuming risk-free rate of 0.01)
        metrics['sharpe_ratio'] = clean_float(
            (metrics['annual_returns'] - 0.01) / metrics['volatility'] 
            if metrics['volatility'] != 0 else 0
        )
        
        return metrics
    except Exception as e:
        print(f"Error calculating metrics: {str(e)}")
        return {
            'daily_returns': 0.0,
            'annual_returns': 0.0,
            'volatility': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }

async def analyze_sentiment(text: str) -> Dict[str, float]:
    """Analyze text sentiment using FinBERT"""
    try:
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        outputs = model(**inputs)
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        return {
            "negative": float(predictions[0][0]),
            "neutral": float(predictions[0][1]),
            "positive": float(predictions[0][2])
        }
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        return {"negative": 0.0, "neutral": 0.0, "positive": 0.0}

@app.get("/stock/{symbol}")
async def get_stock_data(symbol: str, period: str = "1y"):
    """Get stock data and analysis"""
    try:
        # Fetch stock data
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
            
        # Calculate technical indicators
        df = calculate_technical_indicators(df)
        
        # Calculate metrics
        metrics = calculate_metrics(df)
        
        # Get company info
        info = stock.info
        description = info.get('longBusinessSummary', '')
        
        # Get sentiment analysis
        sentiment = await analyze_sentiment(description)
        
        response = {
            "historical_data": df.reset_index().to_dict('records'),
            "metrics": metrics,
            "company_info": {
                "name": info.get("longName", symbol),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": clean_float(info.get("marketCap", 0)),
                "pe_ratio": clean_float(info.get("forwardPE", 0)),
                "beta": clean_float(info.get("beta", 0)),
                "dividend_yield": clean_float(info.get("dividendYield", 0)),
                "description": description
            },
            "sentiment": sentiment
        }
        
        return response
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Financial Analysis API is running",
        "version": "1.0.0",
        "endpoints": [
            "/stock/{symbol}",
            "/"
        ]
    }
