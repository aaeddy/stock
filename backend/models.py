"""
数据模型文件，定义系统中的核心数据结构

主要包含三个模型类：
1. Account - 账户模型，记录账户资金和盈亏情况
2. Position - 持仓模型，记录股票持仓信息
3. Trade - 交易模型，记录交易历史
"""
from datetime import datetime

class Account:
    """
    账户模型，记录账户资金和盈亏情况
    
    属性：
        initial_capital: 初始资金
        available_cash: 可用资金
        total_assets: 总资产
        total_profit: 总盈亏
        profit_rate: 盈亏比例
        created_at: 创建时间
    """
    def __init__(self, initial_capital):
        """
        初始化账户
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.total_assets = initial_capital
        self.total_profit = 0.0
        self.profit_rate = 0.0
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        """
        转换为字典格式
        
        Returns:
            dict: 账户信息字典
        """
        return {
            'initial_capital': self.initial_capital,
            'available_cash': self.available_cash,
            'total_assets': self.total_assets,
            'total_profit': self.total_profit,
            'profit_rate': self.profit_rate,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        """
        从字典创建账户实例
        
        Args:
            data: 账户信息字典
        
        Returns:
            Account: 账户实例
        """
        account = cls(data['initial_capital'])
        account.available_cash = data['available_cash']
        account.total_assets = data['total_assets']
        account.total_profit = data['total_profit']
        account.profit_rate = data['profit_rate']
        account.created_at = data['created_at']
        return account

class Position:
    """
    持仓模型，记录股票持仓信息
    
    属性：
        stock_code: 股票代码
        stock_name: 股票名称
        shares: 持仓数量
        cost_price: 成本价
        cost_amount: 成本金额
        current_price: 当前价格
        market_value: 市值
        profit: 盈亏
        profit_rate: 盈亏比例
    """
    def __init__(self, stock_code, stock_name, shares, cost_price):
        """
        初始化持仓
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            shares: 持仓数量
            cost_price: 成本价
        """
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.shares = shares
        self.cost_price = cost_price
        self.cost_amount = shares * cost_price
        self.current_price = cost_price
        self.market_value = self.cost_amount
        self.profit = 0.0
        self.profit_rate = 0.0

    def update_price(self, current_price):
        """
        更新股票价格，重新计算市值和盈亏
        
        Args:
            current_price: 当前价格
        """
        self.current_price = current_price
        self.market_value = self.shares * current_price
        self.profit = self.market_value - self.cost_amount
        self.profit_rate = (self.profit / self.cost_amount) * 100 if self.cost_amount > 0 else 0

    def to_dict(self):
        """
        转换为字典格式
        
        Returns:
            dict: 持仓信息字典
        """
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'shares': self.shares,
            'cost_price': self.cost_price,
            'cost_amount': self.cost_amount,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'profit': self.profit,
            'profit_rate': self.profit_rate
        }

    @classmethod
    def from_dict(cls, data):
        """
        从字典创建持仓实例
        
        Args:
            data: 持仓信息字典
        
        Returns:
            Position: 持仓实例
        """
        position = cls(data['stock_code'], data['stock_name'], data['shares'], data['cost_price'])
        position.cost_amount = data['cost_amount']
        position.current_price = data['current_price']
        position.market_value = data['market_value']
        position.profit = data['profit']
        position.profit_rate = data['profit_rate']
        return position

class Trade:
    """
    交易模型，记录交易历史
    
    属性：
        trade_type: 交易类型（buy或sell）
        stock_code: 股票代码
        stock_name: 股票名称
        shares: 交易数量
        price: 交易价格
        amount: 交易金额
        commission: 手续费
        total_amount: 总金额（含手续费）
        created_at: 交易时间
    """
    def __init__(self, trade_type, stock_code, stock_name, shares, price, amount, commission):
        """
        初始化交易记录
        
        Args:
            trade_type: 交易类型（buy或sell）
            stock_code: 股票代码
            stock_name: 股票名称
            shares: 交易数量
            price: 交易价格
            amount: 交易金额
            commission: 手续费
        """
        self.trade_type = trade_type  # 'buy' or 'sell'
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.shares = shares
        self.price = price
        self.amount = amount
        self.commission = commission
        self.total_amount = amount + commission if trade_type == 'buy' else amount - commission
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        """
        转换为字典格式
        
        Returns:
            dict: 交易信息字典
        """
        return {
            'trade_type': self.trade_type,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'shares': self.shares,
            'price': self.price,
            'amount': self.amount,
            'commission': self.commission,
            'total_amount': self.total_amount,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        """
        从字典创建交易实例
        
        Args:
            data: 交易信息字典
        
        Returns:
            Trade: 交易实例
        """
        trade = cls(data['trade_type'], data['stock_code'], data['stock_name'],
                   data['shares'], data['price'], data['amount'], data['commission'])
        trade.total_amount = data['total_amount']
        trade.created_at = data['created_at']
        return trade
