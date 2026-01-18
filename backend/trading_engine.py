import os
import json
from .models import Account, Position, Trade
from .config import Config

class DataManager:
    def __init__(self):
        self.ensure_data_dir()

    def ensure_data_dir(self):
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

    def save_account(self, account: Account):
        with open(Config.ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(account.to_dict(), f, ensure_ascii=False, indent=2)

    def load_account(self) -> Account:
        if os.path.exists(Config.ACCOUNT_FILE):
            with open(Config.ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Account.from_dict(data)
        return Account(Config.INITIAL_CAPITAL)

    def save_positions(self, positions: list):
        with open(Config.POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([pos.to_dict() for pos in positions], f, ensure_ascii=False, indent=2)

    def load_positions(self) -> list:
        if os.path.exists(Config.POSITIONS_FILE):
            with open(Config.POSITIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Position.from_dict(item) for item in data]
        return []

    def save_trades(self, trades: list):
        with open(Config.TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump([trade.to_dict() for trade in trades], f, ensure_ascii=False, indent=2)

    def load_trades(self) -> list:
        if os.path.exists(Config.TRADES_FILE):
            with open(Config.TRADES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Trade.from_dict(item) for item in data]
        return []

class TradingEngine:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.account = data_manager.load_account()
        self.positions = data_manager.load_positions()
        self.trades = data_manager.load_trades()

    def get_account(self) -> Account:
        return self.account

    def get_positions(self) -> list:
        return self.positions

    def get_trades(self) -> list:
        return self.trades

    def calculate_commission(self, amount: float) -> float:
        commission = amount * Config.COMMISSION_RATE
        return max(commission, Config.MIN_COMMISSION)

    def buy_stock(self, stock_code: str, stock_name: str, price: float, shares: int) -> tuple[bool, str]:
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
        for position in self.positions:
            if position.stock_code == stock_code:
                position.update_price(current_price)
        self.update_account_stats()
        self.save_all()

    def update_all_positions_price(self, price_dict: dict):
        for position in self.positions:
            if position.stock_code in price_dict:
                position.update_price(price_dict[position.stock_code])
        self.update_account_stats()
        self.save_all()

    def update_account_stats(self):
        market_value = sum(p.market_value for p in self.positions)
        self.account.total_assets = self.account.available_cash + market_value
        self.account.total_profit = self.account.total_assets - self.account.initial_capital
        self.account.profit_rate = (self.account.total_profit / self.account.initial_capital) * 100

    def save_all(self):
        self.data_manager.save_account(self.account)
        self.data_manager.save_positions(self.positions)
        self.data_manager.save_trades(self.trades)

    def reset_account(self):
        self.account = Account(Config.INITIAL_CAPITAL)
        self.positions = []
        self.trades = []
        self.save_all()
