import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Financial Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: white;
    }
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 5px;
        margin: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("Analytics Controls")
    symbol = st.text_input("Enter Stock Symbol", value="AAPL")
    period = st.selectbox(
        "Time Period",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3
    )
    analysis_type = st.radio(
        "Analysis Type",
        ["Technical", "Fundamental", "Sentiment"]
    )

def create_candlestick_chart(df):
    """Create candlestick chart with technical indicators"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                       vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='OHLC'
        ),
        row=1, col=1
    )

    # Moving Averages
    if 'MA20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['MA20'],
                      name='20 MA', line=dict(color='yellow', width=1)),
            row=1, col=1
        )
    if 'MA50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['MA50'],
                      name='50 MA', line=dict(color='orange', width=1)),
            row=1, col=1
        )

    # Volume
    fig.add_trace(
        go.Bar(x=df['Date'], y=df['Volume'], name='Volume'),
        row=2, col=1
    )

    fig.update_layout(
        title="Stock Price & Volume",
        yaxis_title="Price ($)",
        yaxis2_title="Volume",
        template="plotly_dark",
        height=800,
        xaxis_rangeslider_visible=False
    )

    return fig

def create_technical_charts(df):
    """Create technical analysis charts"""
    col1, col2 = st.columns(2)
    
    with col1:
        # RSI Chart
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], name='RSI'))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        fig_rsi.update_layout(
            title="RSI Indicator",
            template="plotly_dark",
            height=300
        )
        st.plotly_chart(fig_rsi, use_container_width=True)
    
    with col2:
        # MACD Chart
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], name='MACD'))
        fig_macd.add_trace(go.Scatter(x=df['Date'], y=df['MACD_signal'], name='Signal'))
        fig_macd.update_layout(
            title="MACD Indicator",
            template="plotly_dark",
            height=300
        )
        st.plotly_chart(fig_macd, use_container_width=True)

def display_metrics(metrics, company_info):
    """Display financial metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Annual Returns", f"{metrics['annual_returns']*100:.2f}%")
    with col2:
        st.metric("Volatility", f"{metrics['volatility']*100:.2f}%")
    with col3:
        st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    with col4:
        st.metric("Max Drawdown", f"{metrics['max_drawdown']*100:.2f}%")

def display_sentiment(sentiment, description):
    """Display sentiment analysis"""
    fig_sentiment = go.Figure(data=[
        go.Bar(
            x=['Negative', 'Neutral', 'Positive'],
            y=[sentiment['negative'], sentiment['neutral'], sentiment['positive']],
            marker_color=['red', 'gray', 'green']
        )
    ])
    fig_sentiment.update_layout(
        title="Sentiment Analysis",
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig_sentiment, use_container_width=True)
    
    st.subheader("Company Description")
    st.write(description)

# Main app logic
if symbol:
    try:
        response = requests.get(f"http://localhost:8000/stock/{symbol}")
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['historical_data'])
            df['Date'] = pd.to_datetime(df['Date'], utc=True)
            metrics = data['metrics']
            company_info = data['company_info']
            sentiment = data['sentiment']
            
            # Display company header
            st.title(f"{company_info['name']} ({symbol}) Analysis")
            
            # Key metrics header
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Current Price",
                    f"${df['Close'].iloc[-1]:.2f}",
                    f"{df['Close'].pct_change().iloc[-1]*100:.2f}%"
                )
            with col2:
                st.metric(
                    "Market Cap",
                    f"${company_info['market_cap']/1e9:.2f}B"
                )
            with col3:
                st.metric(
                    "Sector",
                    company_info['sector']
                )
            with col4:
                st.metric(
                    "P/E Ratio",
                    f"{company_info['pe_ratio']:.2f}"
                )
            
            # Display different analyses based on selection
            if analysis_type == "Technical":
                st.plotly_chart(create_candlestick_chart(df), use_container_width=True)
                create_technical_charts(df)
                
            elif analysis_type == "Fundamental":
                st.subheader("Company Overview")
                st.write(company_info['description'])
                
                st.subheader("Financial Metrics")
                display_metrics(metrics, company_info)
                
            else:  # Sentiment
                display_sentiment(sentiment, company_info['description'])
            
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        st.write("Please check if the backend server is running and the stock symbol is valid.")

# Footer
st.markdown("---")
st.markdown("""
### Dashboard Features
- Real-time stock data analysis
- Technical indicators (RSI, MACD, Moving Averages)
- Fundamental analysis
- FinBERT sentiment analysis
- Interactive visualizations
""")
