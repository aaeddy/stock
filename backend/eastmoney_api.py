import requests
import json
from typing import Dict, List, Optional

class EastMoneyAPI:
    BASE_URL = "http://push2.eastmoney.com/api/qt"

    @staticmethod
    def get_stock_quote(stock_code: str) -> Optional[Dict]:
        """
        获取股票实时行情数据
        
        API说明：
        - URL结构：http://push2.eastmoney.com/api/qt/stock/get?secid={full_code}&fields={fields}
        - 参数说明：
          - secid: 完整股票代码，格式为"市场代码.股票代码"（沪市为1，深市为0）
          - fields: 要获取的字段列表，具体含义如下：
            * f43: 最新价（单位：分）
            * f44: 最高价（单位：分）
            * f45: 最低价（单位：分）
            * f46: 开盘价（单位：分）
            * f47: 成交量（单位：手）
            * f48: 成交额（单位：元）
            * f49: 竞买价（单位：分）
            * f50: 竞卖价（单位：分）
            * f51: 内盘（单位：手）
            * f52: 外盘（单位：手）
            * f57: 股票编号
            * f58: 股票名称
            * f60: 前收盘价（单位：分）
            * f107: 时间戳
            * f116: 总市值
            * f117: 流通市值
            * f168: 换手率（单位：%）
          - ut: 认证参数，固定值
        - 返回值：包含股票行情信息的字典，已将价格单位转换为元，其他单位保持不变
        - 字段转换说明：价格字段（如f43,f44等）除以100转换为元，其他字段直接使用API返回值
        
        直接点击示例URL：
        - 沪市股票（贵州茅台600519）：http://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f60,f107,f116,f117,f168,f169,f170
        - 深市股票（比亚迪002594）：http://push2.eastmoney.com/api/qt/stock/get?secid=0.002594&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f60,f107,f116,f117,f168,f169,f170
        
        Args:
            stock_code: 股票代码，如"600519"（贵州茅台）、"002594"（比亚迪）
            
        Returns:
            包含股票行情信息的字典，失败返回None
        """
        try:
            if stock_code.startswith('6'):
                market = '1'
                full_code = f"1.{stock_code}"
            elif stock_code.startswith(('0', '3')):
                market = '0'
                full_code = f"0.{stock_code}"
            else:
                return None

            url = f"{EastMoneyAPI.BASE_URL}/stock/get"
            params = {
                'secid': full_code,
                'fields': 'f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f60,f107,f116,f117,f168,f169,f170',
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data and data.get('data'):
                quote_data = data['data']
                return {
                    'stock_code': stock_code,
                    'stock_name': quote_data.get('f58', ''),
                    'current_price': quote_data.get('f43', 0) / 100,
                    'open_price': quote_data.get('f46', 0) / 100,
                    'high_price': quote_data.get('f44', 0) / 100,
                    'low_price': quote_data.get('f45', 0) / 100,
                    'pre_close': quote_data.get('f60', 0) / 100,
                    'volume': quote_data.get('f47', 0),
                    'amount': quote_data.get('f48', 0),
                    'change': quote_data.get('f169', 0) / 100,
                    'change_percent': quote_data.get('f170', 0) / 100,
                    'timestamp': quote_data.get('f107', 0)
                }
            return None
        except Exception as e:
            print(f"获取股票行情失败: {e}")
            return None

    @staticmethod
    def search_stock(keyword: str) -> List[Dict]:
        """
        根据关键字搜索股票
        
        API说明：
        - URL结构：http://searchapi.eastmoney.com/api/suggest/get?input={keyword}&type={type}&token={token}
        - 参数说明：
          - input: 搜索关键字，可以是股票代码或股票名称
          - type: 搜索类型，14代表股票搜索
          - token: 认证参数，固定值
        - 返回值：包含搜索结果的列表，每个结果包含股票代码、股票名称和市场信息
        
        直接点击示例URL：
        - 搜索贵州茅台：http://searchapi.eastmoney.com/api/suggest/get?input=贵州茅台&type=14
        - 搜索比亚迪：http://searchapi.eastmoney.com/api/suggest/get?input=比亚迪&type=14
        - 搜索代码600519：http://searchapi.eastmoney.com/api/suggest/get?input=600519&type=14
        
        Args:
            keyword: 搜索关键字，股票代码或股票名称
            
        Returns:
            包含搜索结果的列表，每个结果是包含股票信息的字典
        """
        try:
            url = "http://searchapi.eastmoney.com/api/suggest/get"
            params = {
                'input': keyword,
                'type': '14',
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data and data.get('QuotationCodeTable'):
                results = []
                for item in data['QuotationCodeTable']['Data']:
                    results.append({
                        'stock_code': item['Code'],
                        'stock_name': item['Name'],
                        'market': item.get('Market', '')
                    })
                return results[:10]
            return []
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []

    @staticmethod
    def get_market_index(index_code: str = '000001') -> Optional[Dict]:
        """
        获取市场指数数据
        
        API说明：
        - URL结构：http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}
        - 参数说明：
          - secid: 完整指数代码，格式为"1.{index_code}"（指数统一使用1作为市场代码）
          - fields: 要获取的字段列表，具体含义如下：
            * f43: 最新价（单位：分）
            * f44: 最高价（单位：分）
            * f45: 最低价（单位：分）
            * f46: 开盘价（单位：分）
            * f60: 前收盘价（单位：分）
            * f170: 涨跌幅（单位：%）
          - ut: 认证参数，固定值
        - 返回值：包含指数行情信息的字典，已将价格单位转换为元，其他单位保持不变
        - 字段转换说明：价格字段（如f43,f44等）除以100转换为元，其他字段直接使用API返回值
        
        直接点击示例URL：
        - 上证指数（000001）：http://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43,f44,f45,f46,f60,f170
      
        Args:
            index_code: 指数代码，默认为上证指数（000001）
            
        Returns:
            包含指数行情信息的字典，失败返回None
        """
        try:
            url = f"{EastMoneyAPI.BASE_URL}/stock/get"
            params = {
                'secid': f'1.{index_code}',
                'fields': 'f43,f44,f45,f46,f60,f170',
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data and data.get('data'):
                quote_data = data['data']
                return {
                    'index_code': index_code,
                    'current_price': quote_data.get('f43', 0) / 100,
                    'open_price': quote_data.get('f46', 0) / 100,
                    'high_price': quote_data.get('f44', 0) / 100,
                    'low_price': quote_data.get('f45', 0) / 100,
                    'pre_close': quote_data.get('f60', 0) / 100,
                    'change_percent': quote_data.get('f170', 0) / 100
                }
            return None
        except Exception as e:
            print(f"获取指数行情失败: {e}")
            return None
    
    @staticmethod
    def get_stock_history(stock_code: str, period: str = 'day', count: int = 30) -> Optional[List[Dict]]:
        """
        获取股票历史行情数据
        
        API说明：
        - URL结构：https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={klt}&fqt={fqt}&end={end}&lmt={count}
        - 参数说明：
          - secid: 完整股票代码，格式为"市场代码.股票代码"（沪市为1，深市为0）
          - fields1: 基础字段
          - fields2: K线数据字段
          - klt: 周期，101=日线，102=周线，103=月线
          - fqt: 复权类型，0=不复权，1=前复权，2=后复权
          - end: 结束时间，格式为YYYYMMDD，默认为当前日期
          - lmt: 数据条数
        - 返回值：包含历史K线数据的列表，每条数据包含日期、开盘价、收盘价、最高价、最低价、成交量等信息
        - 字段转换说明：价格字段除以100转换为元，其他字段直接使用API返回值
        
        直接点击示例URL：
        - 贵州茅台（600519）日线数据：https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600519&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20251231&lmt=30
      
        Args:
            stock_code: 股票代码，如"600519"（贵州茅台）、"002594"（比亚迪）
            period: 周期，可选值：day（日线）、week（周线）、month（月线）
            count: 获取数据条数，默认为30条
            
        Returns:
            包含历史K线数据的列表，失败返回None
        """
        try:
            if stock_code.startswith('6'):
                market = '1'
                full_code = f"1.{stock_code}"
            elif stock_code.startswith(('0', '3')):
                market = '0'
                full_code = f"0.{stock_code}"
            else:
                return None
            
            # 周期映射
            period_map = {
                'day': 101,
                'week': 102,
                'month': 103
            }
            
            # 设置当前日期为默认结束日期（YYYYMMDD格式）
            from datetime import datetime
            current_date = datetime.now().strftime('%Y%m%d')
            
            url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': full_code,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': period_map.get(period, 101),
                'fqt': 1,  # 前复权
                'end': current_date,  # 默认为当前日期
                'lmt': count
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data and data.get('data'):
                klines = data['data'].get('klines', [])
                history_data = []
                
                for kline in klines:
                    parts = kline.split(',')
                    if len(parts) >= 11:
                        history_data.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': int(parts[5]),
                            'amount': float(parts[6]),
                            'change': float(parts[2]) - float(parts[1]),
                            'change_percent': (float(parts[2]) - float(parts[1])) / float(parts[1]) * 100 if float(parts[1]) > 0 else 0
                        })
                
                return history_data
            return []
        except Exception as e:
            print(f"获取股票历史数据失败: {e}")
            return None
    
    @staticmethod
    def get_index_history(index_code: str = '000001', period: str = 'day', count: int = 30) -> Optional[List[Dict]]:
        """
        获取指数历史行情数据
        
        API说明：
        - URL结构：https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={klt}&fqt={fqt}&end={end}&lmt={count}
        - 参数说明：
          - secid: 完整指数代码，格式为"1.{index_code}"（指数统一使用1作为市场代码）
          - fields1: 基础字段
          - fields2: K线数据字段
          - klt: 周期，101=日线，102=周线，103=月线
          - fqt: 复权类型，0=不复权，1=前复权，2=后复权
          - end: 结束时间，格式为YYYYMMDD，默认为当前日期
          - lmt: 数据条数
        - 返回值：包含历史K线数据的列表，每条数据包含日期、开盘价、收盘价、最高价、最低价、成交量等信息
        - 字段转换说明：价格字段除以100转换为元，其他字段直接使用API返回值
        
        直接点击示例URL：
        - 上证指数（000001）日线数据：https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&end=20251231&lmt=30
      
        Args:
            index_code: 指数代码，默认为上证指数（000001）
            period: 周期，可选值：day（日线）、week（周线）、month（月线）
            count: 获取数据条数，默认为30条
            
        Returns:
            包含历史K线数据的列表，失败返回None
        """
        try:
            full_code = f"1.{index_code}"
            
            # 周期映射
            period_map = {
                'day': 101,
                'week': 102,
                'month': 103
            }
            
            # 设置当前日期为默认结束日期（YYYYMMDD格式）
            from datetime import datetime
            current_date = datetime.now().strftime('%Y%m%d')
            
            url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': full_code,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': period_map.get(period, 101),
                'fqt': 0,  # 指数不需要复权
                'end': current_date,  # 默认为当前日期
                'lmt': count
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data and data.get('data'):
                klines = data['data'].get('klines', [])
                history_data = []
                
                for kline in klines:
                    parts = kline.split(',')
                    if len(parts) >= 11:
                        history_data.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': int(parts[5]),
                            'amount': float(parts[6]),
                            'change': float(parts[2]) - float(parts[1]),
                            'change_percent': (float(parts[2]) - float(parts[1])) / float(parts[1]) * 100 if float(parts[1]) > 0 else 0
                        })
                
                return history_data
            return []
        except Exception as e:
            print(f"获取指数历史数据失败: {e}")
            return None