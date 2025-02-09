from flask import Flask, request, jsonify, render_template, send_file
import requests
from datetime import datetime, timedelta
import traceback
import random
from io import BytesIO

app = Flask(__name__)

# Initialize a simple user account
user_account = {
    "username": "retail_investor",
    "cash": 100000,  # Start with $100,000 virtual money
    "portfolio": {}  # Dictionary to hold stock holdings
}

API_KEY = 'KKNHA1296M1PA54C'
BASE_URL = "https://www.alphavantage.co/query"

def get_stock_price(symbol):
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': API_KEY
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if 'Global Quote' in data and '05. price' in data['Global Quote']:
            return float(data['Global Quote']['05. price'])
        return None
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return None
    except ValueError as e:
        print(f"JSON parsing error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buy', methods=['POST'])
def buy_stock():
    try:
        symbol = request.form.get('symbol', '').upper().strip()
        quantity = request.form.get('quantity', '').strip()
        if not symbol or not quantity.isdigit():
            return jsonify({"error": "Invalid input."}), 400
        quantity = int(quantity)
        price = get_stock_price(symbol)
        if price is None:
            return jsonify({"error": "Stock price unavailable."}), 400
        total_cost = price * quantity
        if user_account['cash'] >= total_cost:
            user_account['cash'] -= total_cost
            user_account['portfolio'][symbol] = user_account['portfolio'].get(symbol, 0) + quantity
            return jsonify({"message": f"Bought {quantity} shares of {symbol} at ${price:.2f}."})
        return jsonify({"error": "Not enough cash."}), 400
    except Exception as e:
        return jsonify({"error": "Transaction error."}), 400

@app.route('/sell', methods=['POST'])
def sell_stock():
    try:
        symbol = request.form.get('symbol', '').upper().strip()
        quantity = request.form.get('quantity', '').strip()
        if not symbol or not quantity.isdigit():
            return jsonify({"error": "Invalid input."}), 400
        quantity = int(quantity)
        if user_account['portfolio'].get(symbol, 0) < quantity:
            return jsonify({"error": "Not enough shares."}), 400
        price = get_stock_price(symbol)
        if price is None:
            return jsonify({"error": "Invalid stock symbol."}), 400
        user_account['cash'] += price * quantity
        user_account['portfolio'][symbol] -= quantity
        if user_account['portfolio'][symbol] == 0:
            del user_account['portfolio'][symbol]
        return jsonify({"message": f"Sold {quantity} shares of {symbol} at ${price:.2f}."})
    except Exception as e:
        return jsonify({"error": "Transaction error."}), 400

@app.route('/search', methods=['POST'])
def search_stock():
    try:
        symbol = request.form.get('symbol', '').upper().strip()
        if not symbol:
            return jsonify({"error": "Invalid stock symbol."}), 400
        price = get_stock_price(symbol)
        if price is not None:
            return jsonify({"price": price})
        return jsonify({"error": "Stock not found."}), 400
    except Exception as e:
        return jsonify({"error": "Search error."}), 400

@app.route('/portfolio')
def display_portfolio():
    total_value = user_account['cash']
    portfolio_data = []
    
    for symbol, quantity in user_account['portfolio'].items():
        current_price = get_stock_price(symbol)
        if current_price is not None:
            value = current_price * quantity
            total_value += value
            portfolio_data.append({
                "symbol": symbol,
                "quantity": quantity,
                "current_price": current_price,
                "value": value
            })
    
    return jsonify({
        "cash": user_account['cash'],
        "portfolio": portfolio_data,
        "total_value": total_value
    })

@app.route('/export_portfolio_txt', methods=['GET'])
def export_portfolio_txt():
    try:
        content_str = "Portfolio Report\n\n"
        content_str += f"Cash: ${user_account['cash']:.2f}\n\n"
        content_str += "Holdings:\n"
        
        for symbol, quantity in user_account['portfolio'].items():
            price = get_stock_price(symbol)
            if price is not None:
                value = price * quantity
                content_str += f"{symbol}: {quantity} shares, Current Price: ${price:.2f}, Value: ${value:.2f}\n"
        
        txt_io = BytesIO()
        txt_io.write(content_str.encode('utf-8'))
        txt_io.seek(0)
        
        return send_file(
            txt_io,
            as_attachment=True,
            download_name='portfolio.txt',
            mimetype='text/plain'
        )
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "An error occurred while exporting the portfolio."}), 500

if __name__ == '__main__':
    app.run(debug=True)
