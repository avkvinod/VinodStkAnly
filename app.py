import requests
import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd

# --- 1. MINIMALIST UI CONFIGURATION ---
st.set_page_config(page_title="Institutional Stock Analysis", layout="wide")

# Custom CSS for a modern, minimalist off-white aesthetic
st.markdown("""
    <style>
    .stApp {
        background-color: #FAFAFA;
        color: #333333;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .css-1d391kg {
        background-color: #FAFAFA;
    }
    .stButton>button {
        background-color: #1E1E1E;
        color: #FAFAFA;
        border-radius: 4px;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #555555;
        color: #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Institutional Grade Stock Analysis")
st.markdown("Select an equity and a framework to generate an automated research report.")
st.markdown("---")

# --- 2. USER INPUTS ---
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    # Pre-populated with top stocks and specific high-growth/defense/realty names
    default_stocks = [
        'KAYNES.NS', 'PFC.NS', 'HUDCO.NS', 'HAL.NS', 'MAZDOCK.NS', 
        'DLF.NS', 'BSE.NS', 'M&M.NS', 'RELIANCE.NS', 'TCS.NS', 
        'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'TATAMOTORS.NS'
    ]
    selected_stock = st.selectbox("Select NSE/BSE Stock Symbol", default_stocks)

with col2:
    model_choice = st.selectbox(
        "Select Analytical Framework", 
        ["Goldman Sachs (Fundamentals)", "Morgan Stanley (Technicals)", "Bridgewater (Risk)"]
    )

with col3:
    api_key = st.text_input("Enter Gemini API Key", type="password", placeholder="AIzaSy...")

# --- 3. PROMPT FRAMEWORKS ---
PROMPTS = {
    "Goldman Sachs (Fundamentals)": """
        You are a senior equity research analyst at Goldman Sachs with 20 years of experience evaluating companies for the firm's $2T+ asset management division. I need a complete fundamental analysis of a stock as if you're writing a research report for institutional investors. 
        
        Using the provided raw financial data, analyze:
        - Business model breakdown: how the company makes money explained simply
        - Revenue streams: each segment with percentage contribution and growth trajectory
        - Profitability analysis: gross margin, operating margin, net margin trends
        - Balance sheet health: debt-to-equity, current ratio, cash position vs total debt
        - Free cash flow analysis: FCF yield, FCF growth rate, and capital allocation priorities
        - Competitive advantages: pricing power, brand strength, switching costs, network effects rated 1-10
        - Management quality: capital allocation track record, insider ownership
        - Valuation snapshot: current P/E, P/S, EV/EBITDA vs sector peers
        - Bull case and bear case with 12-month price targets for each
        - One-paragraph verdict: buy, hold, or avoid with conviction level
        
        Output: Format as a Goldman Sachs-style equity research note with a summary rating box at the top. Use Markdown.
    """,
    "Morgan Stanley (Technicals)": """
        You are a senior technical strategist at Morgan Stanley who advises the firm's largest trading desk on chart patterns, momentum signals, and optimal entry and exit points.
        
        Using the provided raw historical price data, provide a complete technical analysis breakdown covering every major indicator:
        - Trend analysis: primary trend direction
        - Support and resistance: exact price levels where the stock is likely to bounce or stall
        - Moving averages: contextualize the recent price against standard moving averages
        - Volume analysis: is volume confirming or contradicting the current price move
        - Chart pattern identification: head and shoulders, double tops, cup and handle, or flags (infer from data trends)
        - Trade setup: specific entry price, stop-loss level, and two profit targets with risk-reward ratio
        
        Output: Format as a Morgan Stanley-style technical analysis note with a clear trade plan summary at the top. Use Markdown.
    """,
    "Bridgewater (Risk)": """
        You are a senior portfolio risk analyst at Bridgewater Associates trained in Ray Dalio's All Weather principles, managing risk for the world's largest hedge fund with $150B+ in assets.
        
        Using the provided raw financial and price data, provide a complete risk assessment of this stock:
        - Volatility profile: historical volatility vs market averages
        - Beta analysis: how much the stock moves relative to the broader market
        - Maximum drawdown history: estimate peak-to-trough drops based on historical highs/lows
        - Sector concentration risk: industry specific vulnerabilities
        - Interest rate sensitivity: how rising or falling rates impact this stock specifically
        - Recession stress test: estimated price decline in a severe market crash
        - Liquidity risk: average daily volume analysis
        - Hedging recommendation: specific options strategies or inverse positions to protect downside
        
        Output: Format as a Bridgewater-style risk memo with a risk dashboard summary table. Use Markdown.
    """
}

# --- 4. DATA FETCHING & EXECUTION ---
if st.button("Generate Analysis"):
    if not api_key:
        st.error("Please enter your Gemini API Key to proceed.")
    else:
        with st.spinner(f"Fetching data for {selected_stock} from NSE/BSE..."):
            try:
                # Initialize Gemini
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-pro')

                # Fetch Market Data via yfinance
                ticker = yf.Ticker(selected_stock)

                
                # We pull different data scopes based on the model to optimize token usage
                if "Fundamentals" in model_choice or "Risk" in model_choice:
                    info_data = ticker.info
                    # Clean up the massive info dictionary to save context window
                    keys_to_keep = ['sector', 'industry', 'marketCap', 'forwardPE', 'trailingPE', 'pegRatio', 
                                    'priceToBook', 'enterpriseToEbitda', 'profitMargins', 'operatingMargins', 
                                    'returnOnEquity', 'revenueGrowth', 'debtToEquity', 'totalCash', 'beta', 
                                    'fiftyTwoWeekHigh', 'fiftyTwoWeekLow', 'averageVolume']
                    filtered_info = {k: info_data.get(k, 'N/A') for k in keys_to_keep}
                    data_payload = str(filtered_info)
                
                if "Technicals" in model_choice or "Risk" in model_choice:
                    hist_data = ticker.history(period="1y")
                    # Send the last 30 days of price action for technical context
                    tail_data = hist_data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(30).to_string()
                    if "Fundamentals" not in model_choice:
                        data_payload = tail_data
                    else:
                        data_payload += f"\n\nRecent Price Action:\n{tail_data}"

                st.success("Data successfully fetched. Generating institutional report...")

                # Construct and send the prompt
                system_instruction = PROMPTS[model_choice]
                full_prompt = f"{system_instruction}\n\nHere is the raw data for {selected_stock}:\n{data_payload}"
                
                response = model.generate_content(full_prompt)
                
                # Render the output
                st.markdown("---")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"An error occurred: {e}")
