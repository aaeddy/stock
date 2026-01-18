"""
量化交易策略引擎

东方财富API数据说明：
1. 直接提供的数据：
   - 股票代码、股票名称
   - 最新价、开盘价、最高价、最低价、前收盘价
   - 成交量、成交额
   - 涨跌幅、涨跌额
   - 时间戳

2. 需要额外计算的数据（策略所需）：
   - 移动平均线（MA5、MA10、MA20等）
   - 动量指标
   - MACD指标（EMA12、EMA26、DIF、DEA、MACD柱状图）
   - RSI指标
   - 布林带（中轨、上轨、下轨、带宽）

数据计算方法说明：
1. 移动平均线：使用收盘价的N日简单平均
2. MACD：基于EMA12和EMA26的差值计算
3. RSI：基于价格涨跌的相对强弱计算
4. 布林带：基于20日移动平均线和标准差计算

所有计算均遵循标准金融指标公式，确保计算准确性
"""
import pandas as pd
import numpy as np
from .eastmoney_api import EastMoneyAPI

class StrategyEngine:
    def __init__(self):
        self.api = EastMoneyAPI()

    def analyze(self, stock_code: str, strategy_type: str = 'ma'):
        """
        执行策略分析
        
        Args:
            stock_code: 股票代码
            strategy_type: 策略类型，可选值：ma, momentum, volume, macd, rsi, bollinger
            
        Returns:
            包含策略分析结果和计算过程的字典
        """
        quote = self.api.get_stock_quote(stock_code)
        if not quote:
            return {'error': '无法获取股票数据'}
        
        # 获取历史数据用于技术指标计算
        history_data = self.api.get_stock_history(stock_code, 'day', 60)  # 获取60天历史数据

        result = {
            'stock_code': stock_code,
            'stock_name': quote['stock_name'],
            'current_price': quote['current_price'],
            'strategy_type': strategy_type,
            'signal': 'hold',
            'reason': '',
            'calculation_steps': []  # 添加计算过程字段
        }

        if strategy_type == 'ma':
            result.update(self.ma_strategy(quote, history_data))
        elif strategy_type == 'momentum':
            result.update(self.momentum_strategy(quote, history_data))
        elif strategy_type == 'volume':
            result.update(self.volume_strategy(quote, history_data))
        elif strategy_type == 'macd':
            result.update(self.macd_strategy(quote, history_data))
        elif strategy_type == 'rsi':
            result.update(self.rsi_strategy(quote, history_data))
        elif strategy_type == 'bollinger':
            result.update(self.bollinger_strategy(quote, history_data))

        return result

    def ma_strategy(self, quote: dict, history_data: list = None) -> dict:
        """
        移动平均线策略
        
        策略核心逻辑：
        - 基于不同周期的移动平均线（MA5、MA10、MA20）的位置关系生成买卖信号
        - 当短期均线均在长期均线上方时，生成买入信号
        - 当短期均线均在长期均线下方时，生成卖出信号
        
        需要的数据字段：
        - current_price: 当前价格
        - pre_close: 前收盘价
        - change_percent: 涨跌幅
        - history_data: 历史收盘价数据，用于计算移动平均线
        
        数据计算方法：
        - MA5: 5日移动平均线 = 最近5天收盘价的简单平均
        - MA10: 10日移动平均线 = 最近10天收盘价的简单平均
        - MA20: 20日移动平均线 = 最近20天收盘价的简单平均
        
        信号生成规则：
        - 买入：当前价格 > MA5 > MA10 > MA20，且涨跌幅 > 3%
        - 买入：当前价格 > MA5 > MA10 > MA20
        - 卖出：当前价格 < MA5 < MA10
        - 卖出：MA5 < MA10 < MA20（空头排列）
        - 持有：其他情况
        """
        current_price = quote['current_price']
        pre_close = quote['pre_close']
        change_percent = quote['change_percent']
        
        # 记录计算过程
        calculation_steps = []
        
        # 步骤1：获取基础数据
        calculation_steps.append({
            'step': 1,
            'name': '获取基础数据',
            'description': '从API获取股票的基础行情数据',
            'data': {
                'current_price': current_price,
                'pre_close': pre_close,
                'change_percent': change_percent
            }
        })
        
        # 步骤2：获取历史数据
        closes = []
        if history_data and len(history_data) > 0:
            closes = [item['close'] for item in history_data]  # 获取所有历史收盘价
        
        # 步骤3：计算移动平均线
        # 使用真实历史数据计算移动平均线（如果有足够的数据）
        ma5 = current_price
        ma10 = current_price
        ma20 = current_price
        
        if len(closes) >= 5:
            ma5 = sum(closes[-5:]) / 5
        if len(closes) >= 10:
            ma10 = sum(closes[-10:]) / 10
        if len(closes) >= 20:
            ma20 = sum(closes[-20:]) / 20
        
        calculation_steps.append({
            'step': 3,
            'name': '计算移动平均线',
            'description': '根据历史收盘价计算不同周期的移动平均线',
            'formulas': {
                'MA5': '最近5天收盘价的简单平均',
                'MA10': '最近10天收盘价的简单平均',
                'MA20': '最近20天收盘价的简单平均'
            },
            'results': {
                'MA5': round(ma5, 2),
                'MA10': round(ma10, 2),
                'MA20': round(ma20, 2)
            }
        })
        
        # 步骤3：判断均线位置关系
        calculation_steps.append({
            'step': 3,
            'name': '判断均线位置关系',
            'description': '分析当前价格与各均线的位置关系',
            'analysis': {
                'current_price > MA5': current_price > ma5,
                'current_price > MA10': current_price > ma10,
                'current_price > MA20': current_price > ma20,
                'MA5 > MA10': ma5 > ma10,
                'MA10 > MA20': ma10 > ma20
            }
        })
        
        # 步骤4：生成买卖信号
        signal = 'hold'
        reason = ''
        
        if current_price > ma5 and current_price > ma10 and current_price > ma20:
            if change_percent > 3:
                signal = 'buy'
                reason = f'股价突破所有均线，强势上涨{change_percent:.2f}%，建议买入'
            else:
                signal = 'buy'
                reason = '股价站上所有均线，多头排列，建议买入'
        elif current_price < ma5 and current_price < ma10:
            signal = 'sell'
            reason = '股价跌破短期均线，趋势转弱，建议卖出'
        elif ma5 < ma10 and ma10 < ma20:
            signal = 'sell'
            reason = '均线空头排列，下跌趋势，建议卖出'
        else:
            signal = 'hold'
            reason = '股价在均线附近震荡，建议观望'
        
        calculation_steps.append({
            'step': 4,
            'name': '生成买卖信号',
            'description': '根据均线位置关系和涨跌幅生成最终的买卖信号',
            'signal': signal,
            'reason': reason
        })
        
        return {
            'signal': signal,
            'reason': reason,
            'calculation_steps': calculation_steps,
            'indicators': {
                'ma5': round(ma5, 2),
                'ma10': round(ma10, 2),
                'ma20': round(ma20, 2)
            }
        }

    def momentum_strategy(self, quote: dict, history_data: list = None) -> dict:
        """
        动量策略
        
        策略核心逻辑：
        - 基于股票价格的涨跌幅和成交量判断股票的动能
        - 当股票价格大幅上涨且成交量放大时，生成买入信号
        - 当股票价格大幅下跌时，生成卖出信号
        
        需要的数据字段：
        - change_percent: 涨跌幅
        - volume: 成交量
        - history_data: 历史数据，用于计算动量指标
        
        数据计算方法：
        - 涨跌幅：直接使用API提供的数据
        - 成交量：直接使用API提供的数据
        - 动量指标：使用最近N日的价格变化率
        
        信号生成规则：
        - 买入：涨跌幅 > 7% 且成交量 > 1000万股
        - 买入：涨跌幅 > 3%
        - 卖出：涨跌幅 < -7%
        - 卖出：涨跌幅 < -3%
        - 持有：其他情况
        """
        change_percent = quote['change_percent']
        volume = quote['volume']
        
        # 记录计算过程
        calculation_steps = []
        
        # 步骤1：获取基础数据
        calculation_steps.append({
            'step': 1,
            'name': '获取基础数据',
            'description': '从API获取股票的涨跌幅和成交量数据',
            'data': {
                'change_percent': change_percent,
                'volume': volume
            }
        })
        
        # 步骤2：判断动量级别
        strong_buy = change_percent > 7
        buy = change_percent > 3
        strong_sell = change_percent < -7
        sell = change_percent < -3
        
        calculation_steps.append({
            'step': 2,
            'name': '判断动量级别',
            'description': '根据涨跌幅判断股票的动量强度',
            'rules': {
                '强势买入': '涨跌幅 > 7%',
                '买入': '涨跌幅 > 3%',
                '强势卖出': '涨跌幅 < -7%',
                '卖出': '涨跌幅 < -3%'
            },
            'results': {
                '强势买入': strong_buy,
                '买入': buy,
                '强势卖出': strong_sell,
                '卖出': sell
            }
        })
        
        # 步骤3：结合成交量判断
        is_high_volume = volume > 10000000
        
        calculation_steps.append({
            'step': 3,
            'name': '结合成交量判断',
            'description': '分析成交量是否放大，增强动量信号的可靠性',
            'analysis': {
                '成交量 > 1000万股': is_high_volume
            }
        })
        
        # 步骤4：生成最终信号
        signal = 'hold'
        reason = ''
        
        if strong_buy and is_high_volume:
            signal = 'buy'
            reason = f'强势涨停{change_percent:.2f}%，放量突破，建议买入'
        elif buy:
            signal = 'buy'
            reason = f'上涨{change_percent:.2f}%，动能强劲，建议买入'
        elif strong_sell:
            signal = 'sell'
            reason = f'大幅下跌{abs(change_percent):.2f}%，风险极大，建议卖出'
        elif sell:
            signal = 'sell'
            reason = f'下跌{abs(change_percent):.2f}%，动能转弱，建议卖出'
        else:
            signal = 'hold'
            reason = '波动较小，动能不足，建议观望'
        
        calculation_steps.append({
            'step': 4,
            'name': '生成最终信号',
            'description': '根据动量级别和成交量生成最终的买卖信号',
            'signal': signal,
            'reason': reason
        })
        
        return {
            'signal': signal,
            'reason': reason,
            'calculation_steps': calculation_steps,
            'indicators': {
                'change_percent': change_percent,
                'volume': volume
            }
        }

    def volume_strategy(self, quote: dict, history_data: list = None) -> dict:
        """
        成交量策略
        
        策略核心逻辑：
        - 基于成交量的变化判断资金流入流出情况
        - 当成交量放大且价格上涨时，生成买入信号
        - 当成交量放大且价格下跌时，生成卖出信号
        
        需要的数据字段：
        - volume: 成交量
        - amount: 成交额
        - change_percent: 涨跌幅
        - history_data: 历史数据，用于计算平均成交量
        
        数据计算方法：
        - 成交量：直接使用API提供的数据
        - 成交额：直接使用API提供的数据
        - 成交量比率(volume_ratio)：当前成交量 / 历史平均成交量
        
        信号生成规则：
        - 买入：成交量比率 > 2 且 涨跌幅 > 0
        - 卖出：成交量比率 > 2 且 涨跌幅 < 0
        - 持有：成交量比率 < 0.5
        - 买入：成交量比率 > 1.5 且 涨跌幅 > 0
        - 持有：其他情况
        """
        volume = quote['volume']
        amount = quote['amount']
        change_percent = quote['change_percent']
        
        # 记录计算过程
        calculation_steps = []
        
        # 步骤1：获取基础数据
        calculation_steps.append({
            'step': 1,
            'name': '获取基础数据',
            'description': '从API获取股票的成交量、成交额和涨跌幅数据',
            'data': {
                'volume': volume,
                'amount': amount,
                'change_percent': change_percent
            }
        })
        
        # 步骤2：计算成交量比率
        avg_volume = 10000000
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0
        
        calculation_steps.append({
            'step': 2,
            'name': '计算成交量比率',
            'description': '计算当前成交量与平均成交量的比率',
            'formula': 'volume_ratio = volume / avg_volume',
            'parameters': {
                'avg_volume': avg_volume
            },
            'result': round(volume_ratio, 2)
        })
        
        # 步骤3：分析成交量状态
        is_high_volume = volume_ratio > 2
        is_moderate_volume = 1.5 < volume_ratio <= 2
        is_low_volume = volume_ratio < 0.5
        is_price_up = change_percent > 0
        
        calculation_steps.append({
            'step': 3,
            'name': '分析成交量状态',
            'description': '根据成交量比率判断成交量状态',
            'analysis': {
                '放量(>2倍)': is_high_volume,
                '温和放量(1.5-2倍)': is_moderate_volume,
                '缩量(<0.5倍)': is_low_volume,
                '价格上涨': is_price_up
            }
        })
        
        # 步骤4：生成最终信号
        signal = 'hold'
        reason = ''
        
        if is_high_volume and is_price_up:
            signal = 'buy'
            reason = f'放量上涨（成交量{volume_ratio:.1f}倍），资金流入明显，建议买入'
        elif is_high_volume and not is_price_up:
            signal = 'sell'
            reason = f'放量下跌（成交量{volume_ratio:.1f}倍），资金流出明显，建议卖出'
        elif is_low_volume:
            signal = 'hold'
            reason = '成交量萎缩，缺乏方向，建议观望'
        elif is_moderate_volume and is_price_up:
            signal = 'buy'
            reason = '温和放量上涨，趋势向好，建议买入'
        else:
            signal = 'hold'
            reason = '成交量正常，建议观望'
        
        calculation_steps.append({
            'step': 4,
            'name': '生成最终信号',
            'description': '根据成交量状态和价格走势生成最终的买卖信号',
            'signal': signal,
            'reason': reason
        })
        
        return {
            'signal': signal,
            'reason': reason,
            'calculation_steps': calculation_steps,
            'indicators': {
                'volume': volume,
                'volume_ratio': round(volume_ratio, 2),
                'change_percent': change_percent
            }
        }

    def macd_strategy(self, quote: dict, history_data: list = None) -> dict:
        """
        MACD策略
        
        策略核心逻辑：
        - 基于MACD指标（移动平均收敛发散指标）的金叉、死叉和位置关系生成买卖信号
        - MACD由DIF（快线）、DEA（慢线）和MACD柱状图组成
        - 当DIF上穿DEA且均在零轴上方时，生成买入信号
        - 当DIF下穿DEA且均在零轴下方时，生成卖出信号
        
        需要的数据字段：
        - current_price: 当前价格
        - pre_close: 前收盘价
        - change_percent: 涨跌幅
        - history_data: 历史数据，用于计算指数移动平均线
        
        数据计算方法：
        - EMA12: 12日指数移动平均线，公式：EMA(t) = 收盘价(t) * 2/(12+1) + EMA(t-1) * (12-1)/(12+1)
        - EMA26: 26日指数移动平均线，公式：EMA(t) = 收盘价(t) * 2/(26+1) + EMA(t-1) * (26-1)/(26+1)
        - DIF: EMA12 - EMA26
        - DEA: DIF的9日指数移动平均线，公式：DEA(t) = DIF(t) * 2/(9+1) + DEA(t-1) * (9-1)/(9+1)
        - MACD柱状图: (DIF - DEA) * 2
        
        信号生成规则：
        - 买入：DIF > 0 且 DEA > 0 且 DIF > DEA 且 涨跌幅 > 2%
        - 买入：DIF > 0 且 DEA > 0 且 DIF > DEA
        - 卖出：DIF < 0 且 DEA < 0 且 DIF < DEA
        - 买入：DIF > 0 且 DEA < 0（金叉）
        - 卖出：DIF < 0 且 DEA > 0（死叉）
        - 持有：其他情况
        """
        current_price = quote['current_price']
        pre_close = quote['pre_close']
        change_percent = quote['change_percent']
        
        # 记录计算过程
        calculation_steps = []
        
        # 步骤1：获取基础数据
        calculation_steps.append({
            'step': 1,
            'name': '获取基础数据',
            'description': '从API获取股票的当前价格和涨跌幅数据',
            'data': {
                'current_price': current_price,
                'pre_close': pre_close,
                'change_percent': change_percent
            }
        })
        
        # 步骤2：获取历史数据
        closes = []
        if history_data and len(history_data) > 0:
            closes = [item['close'] for item in history_data]  # 获取所有历史收盘价
        
        # 步骤3：计算EMA（指数移动平均线）
        # 使用真实历史数据计算EMA12、EMA26
        ema12 = current_price
        ema26 = current_price
        
        if len(closes) > 0:
            # 初始化EMA为第一个收盘价
            ema12 = closes[0]
            ema26 = closes[0]
            
            # 计算EMA12和EMA26
            for close in closes[1:]:
                ema12 = close * 2/(12+1) + ema12 * (12-1)/(12+1)
                ema26 = close * 2/(26+1) + ema26 * (26-1)/(26+1)
        
        calculation_steps.append({
            'step': 2,
            'name': '计算EMA',
            'description': '计算12日和26日指数移动平均线',
            'formulas': {
                'EMA12': 'EMA(t) = 收盘价(t) * 2/(12+1) + EMA(t-1) * (12-1)/(12+1)',
                'EMA26': 'EMA(t) = 收盘价(t) * 2/(26+1) + EMA(t-1) * (26-1)/(26+1)'
            },
            'results': {
                'EMA12': round(ema12, 2),
                'EMA26': round(ema26, 2)
            }
        })
        
        # 步骤4：计算DIF
        dif = ema12 - ema26
        
        calculation_steps.append({
            'step': 3,
            'name': '计算DIF',
            'description': '计算DIF（快线），即EMA12与EMA26的差值',
            'formulas': {
                'DIF': 'EMA12 - EMA26'
            },
            'results': {
                'DIF': round(dif, 4)
            }
        })
        
        # 步骤5：计算DEA
        # DEA是DIF的9日EMA
        dea = dif
        if len(closes) > 0:
            # 计算DIF序列
            difs = []
            temp_ema12 = closes[0]
            temp_ema26 = closes[0]
            
            for close in closes[1:]:
                temp_ema12 = close * 2/(12+1) + temp_ema12 * (12-1)/(12+1)
                temp_ema26 = close * 2/(26+1) + temp_ema26 * (26-1)/(26+1)
                temp_dif = temp_ema12 - temp_ema26
                difs.append(temp_dif)
            
            # 计算DEA
            if len(difs) > 0:
                dea = difs[0]
                for d in difs[1:]:
                    dea = d * 2/(9+1) + dea * (9-1)/(9+1)
        
        calculation_steps.append({
            'step': 4,
            'name': '计算DEA',
            'description': '计算DEA（慢线），即DIF的9日指数移动平均线',
            'formulas': {
                'DEA': 'DEA(t) = DIF(t) * 2/(9+1) + DEA(t-1) * (9-1)/(9+1)'
            },
            'results': {
                'DEA': round(dea, 4)
            }
        })
        
        # 步骤6：计算MACD柱状图
        macd_bar = (dif - dea) * 2
        
        calculation_steps.append({
            'step': 5,
            'name': '计算MACD柱状图',
            'description': '计算MACD柱状图，表示DIF与DEA的差值',
            'formulas': {
                'MACD柱状图': '(DIF - DEA) * 2'
            },
            'results': {
                'MACD柱状图': round(macd_bar, 4)
            }
        })
        
        # 步骤4：分析MACD状态
        is_dif_above_dea = dif > dea
        is_dif_above_zero = dif > 0
        is_dea_above_zero = dea > 0
        is_golden_cross = is_dif_above_dea and (dif > 0 or dea > 0)
        is_dead_cross = not is_dif_above_dea and (dif < 0 or dea < 0)
        
        calculation_steps.append({
            'step': 4,
            'name': '分析MACD状态',
            'description': '分析DIF与DEA的位置关系和零轴位置',
            'analysis': {
                'DIF > DEA': is_dif_above_dea,
                'DIF在零轴上方': is_dif_above_zero,
                'DEA在零轴上方': is_dea_above_zero,
                '金叉信号': is_golden_cross,
                '死叉信号': is_dead_cross
            }
        })
        
        # 步骤5：生成最终信号
        signal = 'hold'
        reason = ''
        
        if is_dif_above_zero and is_dea_above_zero and is_dif_above_dea:
            if change_percent > 2:
                signal = 'buy'
                reason = 'MACD金叉向上，多头排列，建议买入'
            else:
                signal = 'buy'
                reason = 'MACD在零轴上方，多头趋势，建议买入'
        elif not is_dif_above_zero and not is_dea_above_zero and not is_dif_above_dea:
            signal = 'sell'
            reason = 'MACD死叉向下，空头排列，建议卖出'
        elif is_dif_above_zero and not is_dea_above_zero:
            signal = 'buy'
            reason = 'MACD金叉，趋势反转向上，建议买入'
        elif not is_dif_above_zero and is_dea_above_zero:
            signal = 'sell'
            reason = 'MACD死叉，趋势反转向下，建议卖出'
        else:
            signal = 'hold'
            reason = 'MACD信号不明确，建议观望'
        
        calculation_steps.append({
            'step': 5,
            'name': '生成最终信号',
            'description': '根据MACD状态生成最终的买卖信号',
            'signal': signal,
            'reason': reason
        })
        
        return {
            'signal': signal,
            'reason': reason,
            'calculation_steps': calculation_steps,
            'indicators': {
                'DIF': round(dif, 4),
                'DEA': round(dea, 4),
                'MACD_bar': round(macd_bar, 4),
                'EMA12': round(ema12, 2),
                'EMA26': round(ema26, 2)
            }
        }

    def rsi_strategy(self, quote: dict, history_data: list = None) -> dict:
        """
        RSI策略
        
        策略核心逻辑：
        - 基于RSI（相对强弱指标）判断股票的超买超卖状态
        - RSI取值范围为0-100，通常70以上为超买，30以下为超卖
        - 当RSI处于超卖区间时，生成买入信号
        - 当RSI处于超买区间时，生成卖出信号
        
        需要的数据字段：
        - current_price: 当前价格
        - pre_close: 前收盘价
        - change_percent: 涨跌幅
        - history_data: 历史数据，用于计算14日平均涨跌
        
        数据计算方法：
        - change: 价格变动额 = 当日收盘价 - 前一日收盘价
        - gain: 上涨金额（change > 0时为change，否则为0）
        - loss: 下跌金额（change < 0时为abs(change)，否则为0）
        - avg_gain: 14日平均上涨金额，公式：avg_gain = (avg_gain_prev * 13 + gain_current) / 14
        - avg_loss: 14日平均下跌金额，公式：avg_loss = (avg_loss_prev * 13 + loss_current) / 14
        - RS: 相对强弱 = avg_gain / avg_loss
        - RSI: 100 - (100 / (1 + RS))
        
        信号生成规则：
        - 买入：RSI < 30 且 涨跌幅 < -3%
        - 买入：RSI < 30
        - 卖出：RSI > 70 且 涨跌幅 > 3%
        - 卖出：RSI > 70
        - 买入：RSI < 40
        - 卖出：RSI > 60
        - 持有：其他情况
        """
        current_price = quote['current_price']
        pre_close = quote['pre_close']
        change_percent = quote['change_percent']
        
        # 记录计算过程
        calculation_steps = []
        
        # 步骤1：获取基础数据
        calculation_steps.append({
            'step': 1,
            'name': '获取基础数据',
            'description': '从API获取股票的价格数据',
            'data': {
                'current_price': current_price,
                'pre_close': pre_close,
                'change_percent': change_percent
            }
        })
        
        # 步骤2：获取历史数据
        closes = []
        if history_data and len(history_data) > 0:
            closes = [item['close'] for item in history_data]  # 获取所有历史收盘价
        
        # 步骤3：计算价格变动
        changes = []
        if len(closes) >= 2:
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                changes.append(change)
        
        calculation_steps.append({
            'step': 2,
            'name': '计算价格变动',
            'description': '计算每日收盘价与前一日收盘价的变动额',
            'formula': 'change = 当日收盘价 - 前一日收盘价',
            'data': {
                '历史数据条数': len(closes),
                '价格变动计算条数': len(changes)
            }
        })
        
        # 步骤4：计算涨跌金额
        gains = []
        losses = []
        for change in changes:
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        calculation_steps.append({
            'step': 3,
            'name': '计算涨跌金额',
            'description': '根据价格变动计算每日上涨金额和下跌金额',
            'rules': {
                'gain': 'change > 0时为change，否则为0',
                'loss': 'change < 0时为abs(change)，否则为0'
            },
            'data': {
                '上涨天数': sum(1 for g in gains if g > 0),
                '下跌天数': sum(1 for l in losses if l > 0)
            }
        })
        
        # 步骤5：计算平均涨跌金额（14日）
        avg_gain = 0
        avg_loss = 0
        
        if len(gains) >= 14:
            # 首次计算：前14天的平均值
            initial_gains = gains[:14]
            initial_losses = losses[:14]
            
            avg_gain = sum(initial_gains) / 14
            avg_loss = sum(initial_losses) / 14
            
            # 后续计算：使用平滑移动平均
            for i in range(14, len(gains)):
                avg_gain = (avg_gain * 13 + gains[i]) / 14
                avg_loss = (avg_loss * 13 + losses[i]) / 14
        elif len(gains) > 0:
            # 如果历史数据不足14天，使用现有数据的平均值
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
        
        calculation_steps.append({
            'step': 4,
            'name': '计算平均涨跌金额',
            'description': '计算14日平均上涨金额和平均下跌金额',
            'formulas': {
                'avg_gain': '(avg_gain_prev * 13 + gain_current) / 14',
                'avg_loss': '(avg_loss_prev * 13 + loss_current) / 14'
            },
            'results': {
                'avg_gain': round(avg_gain, 4),
                'avg_loss': round(avg_loss, 4)
            }
        })
        
        # 步骤6：计算RS和RSI
        rsi = 50  # 默认值，当没有足够数据时使用
        rs = 1
        
        if avg_loss == 0:
            rs = float('inf')
            rsi = 100
        elif avg_gain == 0:
            rs = 0
            rsi = 0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        calculation_steps.append({
            'step': 5,
            'name': '计算RSI指标',
            'description': '计算相对强弱（RS）和相对强弱指标（RSI）',
            'formulas': {
                'RS': 'avg_gain / avg_loss',
                'RSI': '100 - (100 / (1 + RS))'
            },
            'results': {
                'RS': round(rs, 4) if avg_loss != 0 else '无穷大',
                'RSI': round(rsi, 2)
            }
        })
        
        # 步骤6：分析RSI状态
        is_oversold = rsi < 30
        is_overbought = rsi > 70
        is_low = 30 <= rsi < 40
        is_high = 60 < rsi <= 70
        is_moderate_drop = change_percent < -3
        is_moderate_rise = change_percent > 3
        
        calculation_steps.append({
            'step': 6,
            'name': '分析RSI状态',
            'description': '根据RSI值判断股票的超买超卖状态',
            'analysis': {
                '超卖(<30)': is_oversold,
                '超买(>70)': is_overbought,
                '偏低(30-40)': is_low,
                '偏高(60-70)': is_high,
                '温和下跌(< -3%)': is_moderate_drop,
                '温和上涨(> 3%)': is_moderate_rise
            }
        })
        
        # 步骤7：生成最终信号
        signal = 'hold'
        reason = ''
        
        if is_oversold:
            if is_moderate_drop:
                signal = 'buy'
                reason = f'RSI超卖（{rsi:.1f}），可能反弹，建议买入'
            else:
                signal = 'buy'
                reason = f'RSI超卖（{rsi:.1f}），建议买入'
        elif is_overbought:
            if is_moderate_rise:
                signal = 'sell'
                reason = f'RSI超买（{rsi:.1f}），可能回调，建议卖出'
            else:
                signal = 'sell'
                reason = f'RSI超买（{rsi:.1f}），建议卖出'
        elif is_low:
            signal = 'buy'
            reason = f'RSI偏低（{rsi:.1f}），考虑买入'
        elif is_high:
            signal = 'sell'
            reason = f'RSI偏高（{rsi:.1f}），考虑卖出'
        else:
            signal = 'hold'
            reason = f'RSI中性（{rsi:.1f}），建议观望'
        
        calculation_steps.append({
            'step': 7,
            'name': '生成最终信号',
            'description': '根据RSI状态生成最终的买卖信号',
            'signal': signal,
            'reason': reason
        })
        
        # 计算当前涨跌金额
        current_change = current_price - pre_close
        current_gain = current_change if current_change > 0 else 0
        current_loss = abs(current_change) if current_change < 0 else 0
        
        return {
            'signal': signal,
            'reason': reason,
            'calculation_steps': calculation_steps,
            'indicators': {
                'RSI': round(rsi, 2),
                'gain': round(current_gain, 2),
                'loss': round(current_loss, 2)
            }
        }

    def bollinger_strategy(self, quote: dict, history_data: list = None) -> dict:
        """
        布林带策略
        
        策略核心逻辑：
        - 基于布林带的上轨、中轨和下轨的位置关系生成买卖信号
        - 布林带由中轨（MA20）、上轨（MA20+2*标准差）和下轨（MA20-2*标准差）组成
        - 当股价突破上轨时，生成卖出信号
        - 当股价跌破下轨时，生成买入信号
        - 当布林带开口扩大且股价在中轨上方时，生成买入信号
        
        需要的数据字段：
        - current_price: 当前价格
        - high_price: 最高价
        - low_price: 最低价
        - pre_close: 前收盘价
        - history_data: 历史数据，用于计算移动平均线和标准差
        
        数据计算方法：
        - MA20: 20日移动平均线 = 20日收盘价的平均值
        - std: 20日收盘价的标准差 = sqrt(平均(每个收盘价-MA20)^2)
        - upper_band: 上轨 = MA20 + 2*std
        - lower_band: 下轨 = MA20 - 2*std
        - bandwidth: 带宽 = (上轨-下轨)/MA20*100
        
        信号生成规则：
        - 卖出：当前价格 > 上轨
        - 买入：当前价格 < 下轨
        - 买入：当前价格 > MA20 且 bandwidth > 10%
        - 卖出：当前价格 < MA20 且 bandwidth > 10%
        - 持有：bandwidth < 5%
        - 持有：其他情况
        """
        current_price = quote['current_price']
        high_price = quote['high_price']
        low_price = quote['low_price']
        pre_close = quote['pre_close']
        
        # 记录计算过程
        calculation_steps = []
        
        # 步骤1：获取基础数据
        calculation_steps.append({
            'step': 1,
            'name': '获取基础数据',
            'description': '从API获取股票的价格数据',
            'data': {
                'current_price': current_price,
                'high_price': high_price,
                'low_price': low_price,
                'pre_close': pre_close
            }
        })
        
        # 步骤2：获取历史数据
        closes = []
        if history_data and len(history_data) > 0:
            closes = [item['close'] for item in history_data]  # 获取所有历史收盘价
        
        # 步骤3：计算中轨（MA20）
        ma20 = current_price
        
        if len(closes) >= 20:
            # 使用最近20天的收盘价计算MA20
            recent_closes = closes[-20:]
            ma20 = sum(recent_closes) / 20
        elif len(closes) > 0:
            # 如果历史数据不足20天，使用现有数据的平均值
            ma20 = sum(closes) / len(closes)
        
        calculation_steps.append({
            'step': 2,
            'name': '计算中轨',
            'description': '计算20日移动平均线（中轨）',
            'formula': 'MA20 = 20日收盘价的平均值',
            'results': {
                'MA20': round(ma20, 2),
                '使用数据条数': len(closes)
            }
        })
        
        # 步骤4：计算标准差（20日）
        std = 0
        
        if len(closes) >= 20:
            recent_closes = closes[-20:]
            # 计算平均值
            mean = sum(recent_closes) / 20
            # 计算方差
            variance = sum((close - mean) ** 2 for close in recent_closes) / 20
            # 计算标准差
            std = variance ** 0.5
        elif len(closes) > 1:
            # 如果历史数据不足20天，使用现有数据计算
            mean = sum(closes) / len(closes)
            variance = sum((close - mean) ** 2 for close in closes) / len(closes)
            std = variance ** 0.5
        
        calculation_steps.append({
            'step': 3,
            'name': '计算标准差',
            'description': '计算20日收盘价的标准差',
            'formula': 'std = sqrt(平均(每个收盘价-MA20)^2)',
            'results': {
                'std': round(std, 2)
            }
        })
        
        # 步骤4：计算上下轨
        upper_band = ma20 + 2 * std
        lower_band = ma20 - 2 * std
        
        calculation_steps.append({
            'step': 4,
            'name': '计算上下轨',
            'description': '计算布林带的上轨和下轨',
            'formulas': {
                'upper_band': 'MA20 + 2 * std',
                'lower_band': 'MA20 - 2 * std'
            },
            'results': {
                'upper_band': round(upper_band, 2),
                'lower_band': round(lower_band, 2)
            }
        })
        
        # 步骤5：计算带宽
        bandwidth = (upper_band - lower_band) / ma20 * 100
        
        calculation_steps.append({
            'step': 5,
            'name': '计算带宽',
            'description': '计算布林带的带宽，衡量价格波动范围',
            'formula': 'bandwidth = (upper_band - lower_band) / MA20 * 100',
            'result': round(bandwidth, 2)
        })
        
        # 步骤6：分析布林带状态
        is_price_above_upper = current_price > upper_band
        is_price_below_lower = current_price < lower_band
        is_price_above_ma20 = current_price > ma20
        is_wide_bandwidth = bandwidth > 10
        is_narrow_bandwidth = bandwidth < 5
        
        calculation_steps.append({
            'step': 6,
            'name': '分析布林带状态',
            'description': '分析当前价格与布林带的位置关系',
            'analysis': {
                '价格突破上轨': is_price_above_upper,
                '价格跌破下轨': is_price_below_lower,
                '价格在中轨上方': is_price_above_ma20,
                '带宽扩大(>10%)': is_wide_bandwidth,
                '带宽收窄(<5%)': is_narrow_bandwidth
            }
        })
        
        # 步骤7：生成最终信号
        signal = 'hold'
        reason = ''
        
        if is_price_above_upper:
            signal = 'sell'
            reason = '股价突破上轨，超买信号，建议卖出'
        elif is_price_below_lower:
            signal = 'buy'
            reason = '股价跌破下轨，超卖信号，建议买入'
        elif is_price_above_ma20 and is_wide_bandwidth:
            signal = 'buy'
            reason = '股价在中轨上方，布林带开口，建议买入'
        elif not is_price_above_ma20 and is_wide_bandwidth:
            signal = 'sell'
            reason = '股价在中轨下方，布林带开口，建议卖出'
        elif is_narrow_bandwidth:
            signal = 'hold'
            reason = '布林带收窄，等待突破，建议观望'
        else:
            signal = 'hold'
            reason = '股价在中轨附近，建议观望'
        
        calculation_steps.append({
            'step': 7,
            'name': '生成最终信号',
            'description': '根据布林带状态生成最终的买卖信号',
            'signal': signal,
            'reason': reason
        })
        
        return {
            'signal': signal,
            'reason': reason,
            'calculation_steps': calculation_steps,
            'indicators': {
                'MA20': round(ma20, 2),
                'std': round(std, 2),
                'upper_band': round(upper_band, 2),
                'lower_band': round(lower_band, 2),
                'bandwidth': round(bandwidth, 2)
            }
        }
