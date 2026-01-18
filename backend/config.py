import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123456'
    INITIAL_CAPITAL = 100000.0  # 初始资金10万元
    COMMISSION_RATE = 0.0003    # 手续费率万分之3
    MIN_COMMISSION = 5.0        # 最低手续费5元
    DATA_DIR = 'data'
    ACCOUNT_FILE = os.path.join(DATA_DIR, 'account.json')
    POSITIONS_FILE = os.path.join(DATA_DIR, 'positions.json')
    TRADES_FILE = os.path.join(DATA_DIR, 'trades.json')
