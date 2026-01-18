# A股量化交易模拟系统

一个基于Web的A股量化交易模拟学习系统，使用Python Flask作为后端，对接东方财富API获取真实行情数据。

## 功能特性

- 股票实时行情查询
- 虚拟资金账户管理（初始资金10万元）
- 模拟买入/卖出交易
- 持仓管理和收益计算
- 交易记录查询
- 基础量化策略分析（均线、动量、成交量）

## 技术栈

- 后端：Python + Flask
- 前端：HTML + CSS + JavaScript（原生）
- 数据源：东方财富API
- 数据存储：JSON文件

## 项目结构

```
stock/
├── backend/
│   ├── app.py              # Flask应用主文件
│   ├── config.py           # 配置文件
│   ├── models.py           # 数据模型
│   ├── eastmoney_api.py    # 东方财富API对接
│   ├── trading_engine.py   # 交易引擎
│   ├── strategies.py       # 量化策略
│   └── requirements.txt    # Python依赖
├── frontend/
│   ├── index.html          # 前端页面
│   ├── style.css           # 样式文件
│   └── app.js              # 前端逻辑
├── data/                   # 数据存储目录（自动创建）
│   ├── account.json        # 账户信息
│   ├── positions.json      # 持仓信息
│   └── trades.json         # 交易记录
├── start.bat               # Windows启动脚本
└── README.md               # 说明文档
```

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装步骤

1. 安装Python依赖：

```bash
cd backend
pip install -r requirements.txt
```

2. 启动后端服务：

```bash
cd backend
python app.py
```

后端服务将在 http://localhost:5000 启动

3. 打开前端页面：

直接在浏览器中打开 `frontend/index.html` 文件

或者使用启动脚本（Windows）：

```bash
start.bat
```

## 使用说明

### 账户管理

- 系统自动创建初始资金10万元的虚拟账户
- 可以查看总资产、可用资金、盈亏等信息
- 支持重置账户功能（清除所有交易记录）

### 股票查询

- 在搜索框输入股票代码或名称
- 点击搜索或按回车键
- 点击搜索结果选择股票

### 模拟交易

1. 选择股票后，在交易面板填写：
   - 价格（默认为当前市价）
   - 数量（必须是100的整数倍）

2. 点击"买入"或"卖出"按钮
3. 系统自动计算手续费（万分之3，最低5元）

### 持仓管理

- 查看当前持仓列表
- 显示成本价、现价、市值、盈亏等信息
- 支持快速卖出操作

### 量化策略分析

- 选择策略类型：
  - 均线策略：基于价格与均线的关系
  - 动量策略：基于价格涨跌幅度
  - 成交量策略：基于成交量变化

- 输入股票代码进行分析
- 系统给出买入/卖出/持有建议

### 交易记录

- 查看所有历史交易记录
- 显示交易时间、类型、价格、数量等信息

## API接口

### 账户相关

- `GET /api/account` - 获取账户信息
- `POST /api/account/reset` - 重置账户

### 持仓相关

- `GET /api/positions` - 获取持仓列表

### 交易相关

- `GET /api/trades` - 获取交易记录
- `POST /api/trade/buy` - 买入股票
- `POST /api/trade/sell` - 卖出股票

### 股票相关

- `GET /api/stock/search?keyword=xxx` - 搜索股票
- `GET /api/stock/quote?stock_code=xxx` - 获取股票行情
- `POST /api/stock/quotes` - 批量获取股票行情

### 策略相关

- `POST /api/strategy/analyze` - 策略分析

## 注意事项

1. 本系统仅供学习使用，不构成任何投资建议
2. 数据来源于东方财富API，可能存在延迟
3. 交易手续费按照实际标准计算（万分之3，最低5元）
4. 数据存储在本地JSON文件中，请定期备份

## 扩展开发

### 添加新的量化策略

在 `backend/strategies.py` 中添加新的策略方法：

```python
def new_strategy(self, quote: dict) -> dict:
    # 实现策略逻辑
    return {
        'signal': 'buy/sell/hold',
        'reason': '策略原因'
    }
```

### 自定义初始资金

修改 `backend/config.py` 中的 `INITIAL_CAPITAL` 值

### 修改手续费率

修改 `backend/config.py` 中的 `COMMISSION_RATE` 和 `MIN_COMMISSION` 值

## 许可证

MIT License
