from datetime import datetime

class Account:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.total_assets = initial_capital
        self.total_profit = 0.0
        self.profit_rate = 0.0
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
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
        account = cls(data['initial_capital'])
        account.available_cash = data['available_cash']
        account.total_assets = data['total_assets']
        account.total_profit = data['total_profit']
        account.profit_rate = data['profit_rate']
        account.created_at = data['created_at']
        return account

class Position:
    def __init__(self, stock_code, stock_name, shares, cost_price):
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
        self.current_price = current_price
        self.market_value = self.shares * current_price
        self.profit = self.market_value - self.cost_amount
        self.profit_rate = (self.profit / self.cost_amount) * 100 if self.cost_amount > 0 else 0

    def to_dict(self):
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
        position = cls(data['stock_code'], data['stock_name'], data['shares'], data['cost_price'])
        position.cost_amount = data['cost_amount']
        position.current_price = data['current_price']
        position.market_value = data['market_value']
        position.profit = data['profit']
        position.profit_rate = data['profit_rate']
        return position

class Trade:
    def __init__(self, trade_type, stock_code, stock_name, shares, price, amount, commission):
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
        trade = cls(data['trade_type'], data['stock_code'], data['stock_name'],
                   data['shares'], data['price'], data['amount'], data['commission'])
        trade.total_amount = data['total_amount']
        trade.created_at = data['created_at']
        return trade
