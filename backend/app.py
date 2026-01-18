from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from .config import Config
from .eastmoney_api import EastMoneyAPI
from .trading_engine import DataManager, TradingEngine
from .strategies import StrategyEngine
import os

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)
CORS(app)

data_manager = DataManager()
trading_engine = TradingEngine(data_manager)
eastmoney_api = EastMoneyAPI()
strategy_engine = StrategyEngine()

@app.route('/api/account', methods=['GET'])
def get_account():
    account = trading_engine.get_account()
    return jsonify({
        'success': True,
        'data': account.to_dict()
    })

@app.route('/api/account/reset', methods=['POST'])
def reset_account():
    trading_engine.reset_account()
    return jsonify({
        'success': True,
        'message': '账户已重置'
    })

@app.route('/api/positions', methods=['GET'])
def get_positions():
    positions = trading_engine.get_positions()
    return jsonify({
        'success': True,
        'data': [pos.to_dict() for pos in positions]
    })

@app.route('/api/trades', methods=['GET'])
def get_trades():
    trades = trading_engine.get_trades()
    return jsonify({
        'success': True,
        'data': [trade.to_dict() for trade in reversed(trades)]
    })

@app.route('/api/stock/search', methods=['GET'])
def search_stock():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'})
    
    results = eastmoney_api.search_stock(keyword)
    return jsonify({
        'success': True,
        'data': results
    })

@app.route('/api/stock/quote', methods=['GET'])
def get_stock_quote():
    stock_code = request.args.get('stock_code')
    if not stock_code:
        return jsonify({'success': False, 'message': '请输入股票代码'})
    
    quote = eastmoney_api.get_stock_quote(stock_code)
    if quote:
        trading_engine.update_positions_price(stock_code, quote['current_price'])
        return jsonify({
            'success': True,
            'data': quote
        })
    else:
        return jsonify({
            'success': False,
            'message': '获取股票行情失败'
        })

@app.route('/api/stock/quotes', methods=['POST'])
def get_stock_quotes():
    stock_codes = request.json.get('stock_codes', [])
    if not stock_codes:
        return jsonify({'success': False, 'message': '请提供股票代码列表'})
    
    quotes = {}
    price_dict = {}
    for code in stock_codes:
        quote = eastmoney_api.get_stock_quote(code)
        if quote:
            quotes[code] = quote
            price_dict[code] = quote['current_price']
    
    if price_dict:
        trading_engine.update_all_positions_price(price_dict)
    
    return jsonify({
        'success': True,
        'data': quotes
    })

@app.route('/api/trade/buy', methods=['POST'])
def buy_stock():
    data = request.json
    stock_code = data.get('stock_code')
    stock_name = data.get('stock_name')
    price = float(data.get('price', 0))
    shares = int(data.get('shares', 0))
    
    if not all([stock_code, stock_name, price, shares]):
        return jsonify({'success': False, 'message': '参数不完整'})
    
    success, message = trading_engine.buy_stock(stock_code, stock_name, price, shares)
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/trade/sell', methods=['POST'])
def sell_stock():
    data = request.json
    stock_code = data.get('stock_code')
    stock_name = data.get('stock_name')
    price = float(data.get('price', 0))
    shares = int(data.get('shares', 0))
    
    if not all([stock_code, stock_name, price, shares]):
        return jsonify({'success': False, 'message': '参数不完整'})
    
    success, message = trading_engine.sell_stock(stock_code, stock_name, price, shares)
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/strategy/analyze', methods=['POST'])
def analyze_strategy():
    data = request.json
    stock_code = data.get('stock_code')
    strategy_type = data.get('strategy_type', 'ma')
    
    if not stock_code:
        return jsonify({'success': False, 'message': '请提供股票代码'})
    
    result = strategy_engine.analyze(stock_code, strategy_type)
    return jsonify({
        'success': True,
        'data': result
    })

@app.route('/api/market/index', methods=['GET'])
def get_market_index():
    index_code = request.args.get('index_code', '000001')
    index = eastmoney_api.get_market_index(index_code)
    return jsonify({
        'success': True,
        'data': index
    })

@app.route('/api/stock/history', methods=['GET'])
def get_stock_history():
    stock_code = request.args.get('stock_code')
    period = request.args.get('period', 'day')
    count = int(request.args.get('count', 30))
    
    if not stock_code:
        return jsonify({'success': False, 'message': '请输入股票代码'})
    
    history = eastmoney_api.get_stock_history(stock_code, period, count)
    return jsonify({
        'success': True,
        'data': history
    })

@app.route('/api/market/index/history', methods=['GET'])
def get_market_index_history():
    index_code = request.args.get('index_code', '000001')
    period = request.args.get('period', 'day')
    count = int(request.args.get('count', 30))
    
    history = eastmoney_api.get_index_history(index_code, period, count)
    return jsonify({
        'success': True,
        'data': history
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'message': 'Server is running'
    })

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
