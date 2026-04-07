"""
交易引擎文件，包含数据管理和交易逻辑

主要功能：
1. DataManager - 负责数据的持久化存储和加载
2. TradingEngine - 负责交易逻辑的处理，包括买入、卖出、更新价格等操作
"""
import os
import json
from .models import Account, Position, Trade
from .config import Config

class DataManager:
    """
    数据管理器，负责数据的持久化存储和加载
    
    功能：
        - 确保数据目录存在
        - 保存和加载账户信息
        - 保存和加载持仓信息
        - 保存和加载交易记录
    """
    def __init__(self):
        """
        初始化数据管理器
        """
        self.ensure_data_dir()

    def ensure_data_dir(self):
        """
        确保数据目录存在，如果不存在则创建
        """
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

    def save_account(self, account: Account):
        """
        保存账户信息到文件
        
        Args:
            account: 账户实例
        """
        with open(Config.ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(account.to_dict(), f, ensure_ascii=False, indent=2)

    def load_account(self) -> Account:
        """
        从文件加载账户信息
        
        Returns:
            Account: 账户实例
        """
        if os.path.exists(Config.ACCOUNT_FILE):
            with open(Config.ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Account.from_dict(data)
        return Account(Config.INITIAL_CAPITAL)

    def save_positions(self, positions: list):
        """
        保存持仓信息到文件
        
        Args:
            positions: 持仓列表
        """
        with open(Config.POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([pos.to_dict() for pos in positions], f, ensure_ascii=False, indent=2)

    def load_positions(self) -> list:
        """
        从文件加载持仓信息
        
        Returns:
            list: 持仓列表
        """
        if os.path.exists(Config.POSITIONS_FILE):
            with open(Config.POSITIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Position.from_dict(item) for item in data]
        return []

    def save_trades(self, trades: list):
        """
        保存交易记录到文件
        
        Args:
            trades: 交易记录列表
        """
        with open(Config.TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump([trade.to_dict() for trade in trades], f, ensure_ascii=False, indent=2)

    def load_trades(self) -> list:
        """
        从文件加载交易记录
        
        Returns:
            list: 交易记录列表
        """
        if os.path.exists(Config.TRADES_FILE):
            with open(Config.TRADES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Trade.from_dict(item) for item in data]
        return []

class TradingEngine:
    """
    交易引擎，负责交易逻辑的处理
    
    功能：
        - 管理账户信息
        - 管理持仓信息
        - 管理交易记录
        - 执行买入操作
        - 执行卖出操作
        - 更新持仓价格
        - 计算账户统计信息
    """
    def __init__(self, data_manager: DataManager):
        """
        初始化交易引擎
        
        Args:
            data_manager: 数据管理器实例
        """
        self.data_manager = data_manager
        self.account = data_manager.load_account()
        self.positions = data_manager.load_positions()
        self.trades = data_manager.load_trades()

    def get_account(self) -> Account:
        """
        获取账户信息
        
        Returns:
            Account: 账户实例
        """
        return self.account

    def get_positions(self) -> list:
        """
        获取持仓信息
        
        Returns:
            list: 持仓列表
        """
        return self.positions

    def get_trades(self) -> list:
        """
        获取交易记录
        
        Returns:
            list: 交易记录列表
        """
        return self.trades

    def calculate_commission(self, amount: float) -> float:
        """
        计算交易手续费
        
        Args:
            amount: 交易金额
        
        Returns:
            float: 手续费
        """
        commission = amount * Config.COMMISSION_RATE
        return max(commission, Config.MIN_COMMISSION)

    def buy_stock(self, stock_code: str, stock_name: str, price: float, shares: int) -> tuple[bool, str]:
        """
        买入股票
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            price: 买入价格
            shares: 买入数量
        
        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            amount = price * shares
            commission = self.calculate_commission(amount)
            total_cost = amount + commission

            if total_cost > self.account.available_cash:
                return False, "资金不足"

            self.account.available_cash -= total_cost

            existing_position = next((p for p in self.positions if p.stock_code == stock_code), None)
            if existing_position:
                total_shares = existing_position.shares + shares
                total_cost_amount = existing_position.cost_amount + amount
                existing_position.shares = total_shares
                existing_position.cost_price = total_cost_amount / total_shares
                existing_position.cost_amount = total_cost_amount
                existing_position.update_price(price)
            else:
                position = Position(stock_code, stock_name, shares, price)
                self.positions.append(position)

            trade = Trade('buy', stock_code, stock_name, shares, price, amount, commission)
            self.trades.append(trade)

            self.update_account_stats()
            self.save_all()

            return True, "买入成功"
        except Exception as e:
            return False, f"买入失败: {str(e)}"

    def sell_stock(self, stock_code: str, stock_name: str, price: float, shares: int) -> tuple[bool, str]:
        """
        卖出股票
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            price: 卖出价格
            shares: 卖出数量
        
        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            position = next((p for p in self.positions if p.stock_code == stock_code), None)
            if not position:
                return False, "未持有该股票"

            if shares > position.shares:
                return False, "持仓数量不足"

            amount = price * shares
            commission = self.calculate_commission(amount)
            total_income = amount - commission

            self.account.available_cash += total_income

            if shares == position.shares:
                self.positions.remove(position)
            else:
                position.shares -= shares
                position.cost_amount -= (position.cost_price * shares)
                position.update_price(price)

            trade = Trade('sell', stock_code, stock_name, shares, price, amount, commission)
            self.trades.append(trade)

            self.update_account_stats()
            self.save_all()

            return True, "卖出成功"
        except Exception as e:
            return False, f"卖出失败: {str(e)}"

    def update_positions_price(self, stock_code: str, current_price: float):
        """
        更新单个股票的价格
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
        """
        for position in self.positions:
            if position.stock_code == stock_code:
                position.update_price(current_price)
        self.update_account_stats()
        self.save_all()

    def update_all_positions_price(self, price_dict: dict):
        """
        批量更新股票价格
        
        Args:
            price_dict: 股票代码到价格的映射
        """
        for position in self.positions:
            if position.stock_code in price_dict:
                position.update_price(price_dict[position.stock_code])
        self.update_account_stats()
        self.save_all()

    def update_account_stats(self):
        """
        更新账户统计信息，包括总资产、总盈亏和盈亏比例
        """
        market_value = sum(p.market_value for p in self.positions)
        self.account.total_assets = self.account.available_cash + market_value
        self.account.total_profit = self.account.total_assets - self.account.initial_capital
        self.account.profit_rate = (self.account.total_profit / self.account.initial_capital) * 100

    def save_all(self):
        """
        保存所有数据到文件
        """
        self.data_manager.save_account(self.account)
        self.data_manager.save_positions(self.positions)
        self.data_manager.save_trades(self.trades)

    def reset_account(self):
        """
        重置账户，恢复到初始状态
        """
        self.account = Account(Config.INITIAL_CAPITAL)
        self.positions = []
        self.trades = []
        self.save_all()
