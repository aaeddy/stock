"""
Flask应用主文件，处理所有API请求和静态文件服务

主要功能：
1. 提供RESTful API接口，处理前端的各种请求
2. 集成交易引擎、策略引擎和数据API
3. 提供静态文件服务，加载前端页面

API路由说明：
- /api/account - 获取账户信息
- /api/account/reset - 重置账户
- /api/positions - 获取持仓信息
- /api/trades - 获取交易记录
- /api/stock/search - 搜索股票
- /api/stock/quote - 获取股票行情
- /api/stock/quotes - 批量获取股票行情
- /api/trade/buy - 买入股票
- /api/trade/sell - 卖出股票
- /api/strategy/analyze - 策略分析
- /api/market/index - 获取市场指数
- /api/stock/history - 获取股票历史数据
- /api/market/index/history - 获取指数历史数据
- /api/health - 健康检查
- / - 加载前端页面
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from .config import Config
from .eastmoney_api import EastMoneyAPI
from .trading_engine import DataManager, TradingEngine
from .strategies import StrategyEngine
import os

# 创建Flask应用实例，指定静态文件夹路径
app = Flask(__name__, static_folder='../frontend', static_url_path='')
# 加载配置
app.config.from_object(Config)
# 启用CORS，允许跨域请求
CORS(app)

# 初始化核心组件
data_manager = DataManager()  # 数据管理器，负责数据的读写
trading_engine = TradingEngine(data_manager)  # 交易引擎，处理交易逻辑
eastmoney_api = EastMoneyAPI()  # 东方财富API接口，获取市场数据
strategy_engine = StrategyEngine()  # 策略引擎，执行量化交易策略

@app.route('/api/account', methods=['GET'])
def get_account():
    """
    获取账户信息
    
    Returns:
        JSON: 包含账户信息的响应，包括总资产、可用资金、总盈亏等
    """
    account = trading_engine.get_account()
    return jsonify({
        'success': True,
        'data': account.to_dict()
    })

@app.route('/api/account/reset', methods=['POST'])
def reset_account():
    """
    重置账户
    
    Returns:
        JSON: 重置成功的响应
    """
    trading_engine.reset_account()
    return jsonify({
        'success': True,
        'message': '账户已重置'
    })

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """
    获取持仓信息
    
    Returns:
        JSON: 包含所有持仓信息的列表
    """
    positions = trading_engine.get_positions()
    return jsonify({
        'success': True,
        'data': [pos.to_dict() for pos in positions]
    })

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """
    获取交易记录
    
    Returns:
        JSON: 包含所有交易记录的列表，按时间倒序排列
    """
    trades = trading_engine.get_trades()
    return jsonify({
        'success': True,
        'data': [trade.to_dict() for trade in reversed(trades)]
    })

@app.route('/api/stock/search', methods=['GET'])
def search_stock():
    """
    搜索股票
    
    Args:
        keyword: 搜索关键词（股票代码或名称）
    
    Returns:
        JSON: 包含搜索结果的列表
    """
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
    """
    获取股票实时行情
    
    Args:
        stock_code: 股票代码
    
    Returns:
        JSON: 包含股票行情信息的响应
    """
    stock_code = request.args.get('stock_code')
    if not stock_code:
        return jsonify({'success': False, 'message': '请输入股票代码'})
    
    quote = eastmoney_api.get_stock_quote(stock_code)
    if quote:
        # 更新持仓价格
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
    """
    批量获取股票行情
    
    Args:
        stock_codes: 股票代码列表
    
    Returns:
        JSON: 包含多个股票行情信息的响应
    """
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
        # 批量更新持仓价格
        trading_engine.update_all_positions_price(price_dict)
    
    return jsonify({
        'success': True,
        'data': quotes
    })

@app.route('/api/trade/buy', methods=['POST'])
def buy_stock():
    """
    买入股票
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        price: 买入价格
        shares: 买入数量
    
    Returns:
        JSON: 买入操作的结果
    """
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
    """
    卖出股票
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        price: 卖出价格
        shares: 卖出数量
    
    Returns:
        JSON: 卖出操作的结果
    """
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
    """
    执行策略分析
    
    Args:
        stock_code: 股票代码
        strategy_type: 策略类型（ma, momentum, volume, macd, rsi, bollinger）
    
    Returns:
        JSON: 策略分析结果，包含信号、原因和计算过程
    """
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
    """
    获取市场指数数据
    
    Args:
        index_code: 指数代码，默认为上证指数（000001）
    
    Returns:
        JSON: 包含指数行情信息的响应
    """
    index_code = request.args.get('index_code', '000001')
    index = eastmoney_api.get_market_index(index_code)
    return jsonify({
        'success': True,
        'data': index
    })

@app.route('/api/stock/history', methods=['GET'])
def get_stock_history():
    """
    获取股票历史行情数据
    
    Args:
        stock_code: 股票代码
        period: 周期（day, week, month）
        count: 获取数据条数
    
    Returns:
        JSON: 包含历史K线数据的列表
    """
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
    """
    获取指数历史行情数据
    
    Args:
        index_code: 指数代码，默认为上证指数（000001）
        period: 周期（day, week, month）
        count: 获取数据条数
    
    Returns:
        JSON: 包含历史K线数据的列表
    """
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
    """
    健康检查接口
    
    Returns:
        JSON: 服务器运行状态
    """
    return jsonify({
        'success': True,
        'message': 'Server is running'
    })

@app.route('/')
def index():
    """
    加载前端页面
    
    Returns:
        HTML: 前端页面
    """
    return send_from_directory('../frontend', 'index.html')

if __name__ == '__main__':
    """
    启动Flask应用
    
    运行在0.0.0.0:5000，启用调试模式
    """
    app.run(debug=True, host='0.0.0.0', port=5000)
