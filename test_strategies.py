#!/usr/bin/env python3
"""
测试策略引擎的计算结果
"""

import sys
import os

# 添加backend目录到Python路径
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# 使用__import__函数动态导入模块，避免相对导入问题
sys.modules.pop('strategies', None)
sys.modules.pop('eastmoney_api', None)

# 导入模块
strategies = __import__('strategies')
eastmoney_api = __import__('eastmoney_api')

# 获取类
StrategyEngine = strategies.StrategyEngine
EastMoneyAPI = eastmoney_api.EastMoneyAPI

def test_strategies():
    """测试所有策略"""
    print("开始测试策略引擎...")
    
    # 创建策略引擎实例
    engine = StrategyEngine()
    api = EastMoneyAPI()
    
    # 测试股票代码：贵州茅台（600519）
    stock_code = "600519"
    
    # 测试1：获取股票实时数据
    print(f"\n1. 获取股票 {stock_code} 实时数据...")
    quote = api.get_stock_quote(stock_code)
    if quote:
        print(f"   股票名称: {quote['stock_name']}")
        print(f"   当前价格: {quote['current_price']:.2f}元")
        print(f"   涨跌幅: {quote['change_percent']:.2f}%")
    else:
        print("   获取实时数据失败")
        return False
    
    # 测试2：获取历史数据
    print(f"\n2. 获取股票 {stock_code} 历史数据...")
    history_data = api.get_stock_history(stock_code, 'day', 60)
    if history_data and len(history_data) > 0:
        print(f"   成功获取 {len(history_data)} 条历史数据")
        print(f"   最近一条数据日期: {history_data[-1]['date']}")
        print(f"   最近一条数据收盘价: {history_data[-1]['close']:.2f}元")
    else:
        print("   获取历史数据失败")
        return False
    
    # 测试3：测试MA策略
    print(f"\n3. 测试MA策略...")
    ma_result = engine.ma_strategy(quote, history_data)
    print(f"   信号: {ma_result['signal']}")
    print(f"   原因: {ma_result['reason']}")
    print(f"   指标: {ma_result['indicators']}")
    print(f"   计算步骤: {len(ma_result['calculation_steps'])} 步")
    
    # 测试4：测试MACD策略
    print(f"\n4. 测试MACD策略...")
    macd_result = engine.macd_strategy(quote, history_data)
    print(f"   信号: {macd_result['signal']}")
    print(f"   原因: {macd_result['reason']}")
    print(f"   指标: {macd_result['indicators']}")
    print(f"   计算步骤: {len(macd_result['calculation_steps'])} 步")
    
    # 测试5：测试RSI策略
    print(f"\n5. 测试RSI策略...")
    rsi_result = engine.rsi_strategy(quote, history_data)
    print(f"   信号: {rsi_result['signal']}")
    print(f"   原因: {rsi_result['reason']}")
    print(f"   指标: {rsi_result['indicators']}")
    print(f"   计算步骤: {len(rsi_result['calculation_steps'])} 步")
    
    # 测试6：测试布林带策略
    print(f"\n6. 测试布林带策略...")
    bollinger_result = engine.bollinger_strategy(quote, history_data)
    print(f"   信号: {bollinger_result['signal']}")
    print(f"   原因: {bollinger_result['reason']}")
    print(f"   指标: {bollinger_result['indicators']}")
    print(f"   计算步骤: {len(bollinger_result['calculation_steps'])} 步")
    
    # 测试7：测试动量策略
    print(f"\n7. 测试动量策略...")
    momentum_result = engine.momentum_strategy(quote, history_data)
    print(f"   信号: {momentum_result['signal']}")
    print(f"   原因: {momentum_result['reason']}")
    print(f"   指标: {momentum_result['indicators']}")
    print(f"   计算步骤: {len(momentum_result['calculation_steps'])} 步")
    
    # 测试8：测试成交量策略
    print(f"\n8. 测试成交量策略...")
    volume_result = engine.volume_strategy(quote, history_data)
    print(f"   信号: {volume_result['signal']}")
    print(f"   原因: {volume_result['reason']}")
    print(f"   指标: {volume_result['indicators']}")
    print(f"   计算步骤: {len(volume_result['calculation_steps'])} 步")
    
    print("\n所有策略测试完成！")
    return True

if __name__ == "__main__":
    test_strategies()
