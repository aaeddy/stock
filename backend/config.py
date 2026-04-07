"""
配置文件，定义应用的全局配置参数

主要配置项：
1. 安全相关：SECRET_KEY - Flask应用的密钥
2. 交易相关：初始资金、手续费率、最低手续费
3. 数据存储：数据目录和文件路径
"""
import os

class Config:
    """应用配置类"""
    # Flask应用密钥，用于会话管理和加密
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123456'
    
    # 初始资金，单位：元
    INITIAL_CAPITAL = 100000.0  # 初始资金10万元
    
    # 交易手续费率，万分之3
    COMMISSION_RATE = 0.0003    # 手续费率万分之3
    
    # 最低手续费，单位：元
    MIN_COMMISSION = 5.0        # 最低手续费5元
    
    # 数据存储目录
    DATA_DIR = 'data'
    
    # 账户数据文件路径
    ACCOUNT_FILE = os.path.join(DATA_DIR, 'account.json')
    
    # 持仓数据文件路径
    POSITIONS_FILE = os.path.join(DATA_DIR, 'positions.json')
    
    # 交易记录文件路径
    TRADES_FILE = os.path.join(DATA_DIR, 'trades.json')
