const API_BASE = 'http://localhost:5000/api';

let currentStock = null;
let autoTradeInterval = null;
let charts = {};
let currentKlinePeriod = 'day';

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API请求失败:', error);
        return { success: false, message: '网络请求失败' };
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function formatCurrency(value) {
    return '¥' + parseFloat(value).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}

function formatPercent(value) {
    return parseFloat(value).toFixed(2) + '%';
}

function formatNumber(value) {
    return parseFloat(value).toLocaleString();
}

async function loadAccount() {
    const result = await fetchAPI('/account');
    if (result.success) {
        const account = result.data;
        document.getElementById('total-assets').textContent = formatCurrency(account.total_assets);
        document.getElementById('available-cash').textContent = formatCurrency(account.available_cash);
        document.getElementById('market-value').textContent = formatCurrency(account.total_assets - account.available_cash);
        
        const profitElement = document.getElementById('total-profit');
        profitElement.textContent = formatCurrency(account.total_profit);
        profitElement.className = 'stat-value ' + (account.total_profit >= 0 ? 'positive' : 'negative');
        
        const rateElement = document.getElementById('profit-rate');
        rateElement.textContent = formatPercent(account.profit_rate);
        rateElement.className = 'stat-value ' + (account.profit_rate >= 0 ? 'positive' : 'negative');
        
        document.getElementById('initial-capital').textContent = formatCurrency(account.initial_capital);
        
        updatePortfolioChart();
    }
}

async function loadPositions() {
    const result = await fetchAPI('/positions');
    if (result.success) {
        const tbody = document.getElementById('positions-table');
        tbody.innerHTML = '';
        
        if (result.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#999;">暂无持仓</td></tr>';
            return;
        }
        
        result.data.forEach(position => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${position.stock_code}</strong></td>
                <td>${position.stock_name}</td>
                <td>${formatNumber(position.shares)}</td>
                <td>${position.cost_price.toFixed(2)}</td>
                <td>${position.current_price.toFixed(2)}</td>
                <td>${formatCurrency(position.market_value)}</td>
                <td class="${position.profit >= 0 ? 'positive' : 'negative'}">${formatCurrency(position.profit)}</td>
                <td class="${position.profit_rate >= 0 ? 'positive' : 'negative'}">${formatPercent(position.profit_rate)}</td>
                <td>
                    <button class="btn-action btn-sell-action" onclick="quickSell('${position.stock_code}', '${position.stock_name}', ${position.current_price}, ${position.shares})">卖出</button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        updatePortfolioChart(result.data);
    }
}

async function loadTrades() {
    const result = await fetchAPI('/trades');
    if (result.success) {
        const tbody = document.getElementById('trades-table');
        tbody.innerHTML = '';
        
        if (result.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#999;">暂无交易记录</td></tr>';
            return;
        }
        
        result.data.forEach(trade => {
            const row = document.createElement('tr');
            const typeClass = trade.trade_type === 'buy' ? 'positive' : 'negative';
            const typeText = trade.trade_type === 'buy' ? '买入' : '卖出';
            row.innerHTML = `
                <td>${new Date(trade.created_at).toLocaleString()}</td>
                <td class="${typeClass}">${typeText}</td>
                <td><strong>${trade.stock_code}</strong></td>
                <td>${trade.stock_name}</td>
                <td>${trade.price.toFixed(2)}</td>
                <td>${formatNumber(trade.shares)}</td>
                <td>${formatCurrency(trade.amount)}</td>
                <td>${formatCurrency(trade.commission)}</td>
            `;
            tbody.appendChild(row);
        });
    }
}

async function searchStock() {
    const keyword = document.getElementById('search-input').value.trim();
    if (!keyword) {
        showToast('请输入搜索关键词', 'error');
        return;
    }
    
    const result = await fetchAPI(`/stock/search?keyword=${encodeURIComponent(keyword)}`);
    if (result.success) {
        const container = document.getElementById('search-results');
        container.innerHTML = '';
        
        if (result.data.length === 0) {
            container.innerHTML = '<p class="placeholder-text">未找到相关股票</p>';
            return;
        }
        
        result.data.forEach(stock => {
            const div = document.createElement('div');
            div.className = 'search-result-item';
            div.innerHTML = `
                <span class="stock-code">${stock.stock_code}</span>
                <span class="stock-name">${stock.stock_name}</span>
            `;
            div.onclick = () => selectStock(stock);
            container.appendChild(div);
        });
    }
}

async function selectStock(stock) {
    currentStock = stock;
    document.getElementById('trade-stock-code').value = stock.stock_code;
    document.getElementById('trade-stock-name').value = stock.stock_name;
    document.getElementById('strategy-stock-code').value = stock.stock_code;
    document.getElementById('auto-stock-code').value = stock.stock_code;
    
    const result = await fetchAPI(`/stock/quote?stock_code=${stock.stock_code}`);
    if (result.success) {
        const quote = result.data;
        currentStock.quote = quote;
        document.getElementById('trade-price').value = quote.current_price.toFixed(2);
        updateEstimatedAmount();
        
        const infoDiv = document.getElementById('stock-detail-content');
        infoDiv.innerHTML = `
            <div class="stock-info-grid">
                <div class="info-row">
                    <span class="info-label">股票代码</span>
                    <span class="info-value">${quote.stock_code}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">股票名称</span>
                    <span class="info-value">${quote.stock_name}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">当前价格</span>
                    <span class="info-value ${quote.change_percent >= 0 ? 'positive' : 'negative'}">${quote.current_price.toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">涨跌幅</span>
                    <span class="info-value ${quote.change_percent >= 0 ? 'positive' : 'negative'}">${formatPercent(quote.change_percent)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">开盘价</span>
                    <span class="info-value">${quote.open_price.toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">最高价</span>
                    <span class="info-value">${quote.high_price.toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">最低价</span>
                    <span class="info-value">${quote.low_price.toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">昨收价</span>
                    <span class="info-value">${quote.pre_close.toFixed(2)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">成交量</span>
                    <span class="info-value">${formatNumber(quote.volume)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">成交额</span>
                    <span class="info-value">${formatNumber(quote.amount)}</span>
                </div>
            </div>
        `;
        
        await updateStockKlineChart(quote);
    }
}

function updateEstimatedAmount() {
    const price = parseFloat(document.getElementById('trade-price').value) || 0;
    const shares = parseInt(document.getElementById('trade-shares').value) || 0;
    const amount = price * shares;
    document.getElementById('estimated-amount').textContent = formatCurrency(amount);
}

document.getElementById('trade-price').addEventListener('input', updateEstimatedAmount);
document.getElementById('trade-shares').addEventListener('input', updateEstimatedAmount);

async function executeTrade(type) {
    const stockCode = document.getElementById('trade-stock-code').value;
    const stockName = document.getElementById('trade-stock-name').value;
    const price = parseFloat(document.getElementById('trade-price').value);
    const shares = parseInt(document.getElementById('trade-shares').value);
    
    if (!stockCode || !stockName || !price || !shares) {
        showToast('请填写完整的交易信息', 'error');
        return;
    }
    
    if (shares % 100 !== 0) {
        showToast('交易数量必须是100的整数倍', 'error');
        return;
    }
    
    const endpoint = type === 'buy' ? '/trade/buy' : '/trade/sell';
    const result = await fetchAPI(endpoint, {
        method: 'POST',
        body: JSON.stringify({
            stock_code: stockCode,
            stock_name: stockName,
            price: price,
            shares: shares
        })
    });
    
    if (result.success) {
        showToast(result.message, 'success');
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

async function quickSell(stockCode, stockName, price, maxShares) {
    document.getElementById('trade-stock-code').value = stockCode;
    document.getElementById('trade-stock-name').value = stockName;
    document.getElementById('trade-price').value = price.toFixed(2);
    document.getElementById('trade-shares').value = maxShares;
    updateEstimatedAmount();
    
    switchTab('trading');
    showToast(`已准备卖出 ${stockName}，请确认数量`, 'info');
}

async function analyzeStrategy() {
    const stockCode = document.getElementById('strategy-stock-code').value.trim();
    const strategyType = document.getElementById('strategy-type').value;
    
    if (!stockCode) {
        showToast('请输入股票代码', 'error');
        return;
    }
    
    const result = await fetchAPI('/strategy/analyze', {
        method: 'POST',
        body: JSON.stringify({
            stock_code: stockCode,
            strategy_type: strategyType
        })
    });
    
    if (result.success) {
        const data = result.data;
        const signalClass = `signal-${data.signal}`;
        const signalText = data.signal === 'buy' ? '买入' : (data.signal === 'sell' ? '卖出' : '持有');
        
        let calculationStepsHTML = '';
        if (data.calculation_steps && data.calculation_steps.length > 0) {
            calculationStepsHTML = `
                <div class="calculation-steps">
                    <h5>计算过程</h5>
                    <div class="steps-container">
                        ${data.calculation_steps.map(step => `
                            <div class="step-item">
                                <div class="step-number">${step.step}</div>
                                <div class="step-content">
                                    <div class="step-title">${step.name}</div>
                                    <div class="step-description">${step.description}</div>
                                    ${step.data ? `
                                        <div class="step-data">
                                            <h6>数据:</h6>
                                            <div class="data-grid">
                                                ${Object.entries(step.data).map(([key, value]) => `
                                                    <div class="data-item">
                                                        <span class="data-key">${key}:</span>
                                                        <span class="data-value">${typeof value === 'number' ? value.toFixed(2) : value}</span>
                                                    </div>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                    ${step.formulas ? `
                                        <div class="step-formulas">
                                            <h6>公式:</h6>
                                            ${Object.entries(step.formulas).map(([name, formula]) => `
                                                <div class="formula-item">
                                                    <span class="formula-name">${name}:</span>
                                                    <span class="formula-expression">${formula}</span>
                                                </div>
                                            `).join('')}
                                        </div>
                                    ` : ''}
                                    ${step.formula ? `
                                        <div class="step-formula">
                                            <h6>公式:</h6>
                                            <div class="formula-item">
                                                <span class="formula-expression">${step.formula}</span>
                                            </div>
                                        </div>
                                    ` : ''}
                                    ${step.results ? `
                                        <div class="step-results">
                                            <h6>计算结果:</h6>
                                            <div class="results-grid">
                                                ${Object.entries(step.results).map(([key, value]) => `
                                                    <div class="result-item">
                                                        <span class="result-key">${key}:</span>
                                                        <span class="result-value">${typeof value === 'number' ? value.toFixed(4) : value}</span>
                                                    </div>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                    ${step.result !== undefined ? `
                                        <div class="step-result">
                                            <h6>计算结果:</h6>
                                            <div class="result-value">${typeof step.result === 'number' ? step.result.toFixed(4) : step.result}</div>
                                        </div>
                                    ` : ''}
                                    ${step.rules ? `
                                        <div class="step-rules">
                                            <h6>规则:</h6>
                                            ${Object.entries(step.rules).map(([name, rule]) => `
                                                <div class="rule-item">
                                                    <span class="rule-name">${name}:</span>
                                                    <span class="rule-expression">${rule}</span>
                                                </div>
                                            `).join('')}
                                        </div>
                                    ` : ''}
                                    ${step.analysis ? `
                                        <div class="step-analysis">
                                            <h6>分析:</h6>
                                            <div class="analysis-grid">
                                                ${Object.entries(step.analysis).map(([name, value]) => `
                                                    <div class="analysis-item">
                                                        <span class="analysis-name">${name}:</span>
                                                        <span class="analysis-value ${value ? 'positive' : 'negative'}">${value ? '是' : '否'}</span>
                                                    </div>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        let indicatorsHTML = '';
        if (data.indicators) {
            indicatorsHTML = `
                <div class="strategy-indicators">
                    <h5>指标值</h5>
                    <div class="indicators-grid">
                        ${Object.entries(data.indicators).map(([key, value]) => `
                            <div class="indicator-item">
                                <span class="indicator-name">${key}:</span>
                                <span class="indicator-value">${typeof value === 'number' ? value.toFixed(4) : value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        document.getElementById('strategy-result').innerHTML = `
            <div class="strategy-result-detail">
                <div class="result-header">
                    <h4>${data.stock_name} (${data.stock_code})</h4>
                    <span class="current-price">当前价格: ${data.current_price.toFixed(2)}</span>
                </div>
                <div class="strategy-signal ${signalClass}">${signalText}</div>
                <div class="strategy-info">
                    <p><strong>策略类型:</strong> ${getStrategyName(data.strategy_type)}</p>
                    <p class="strategy-reason">${data.reason}</p>
                </div>
                ${indicatorsHTML}
                ${calculationStepsHTML}
            </div>
        `;
        
        highlightStrategyExplanation(strategyType);
    } else {
        showToast(result.message || '分析失败', 'error');
    }
}

function highlightStrategyExplanation(strategyType) {
    document.querySelectorAll('.strategy-explanation-item').forEach(item => {
        item.style.opacity = '0.4';
        item.style.transform = 'scale(0.98)';
    });
    
    const activeItem = document.querySelector(`.strategy-explanation-item[data-strategy="${strategyType}"]`);
    if (activeItem) {
        activeItem.style.opacity = '1';
        activeItem.style.transform = 'scale(1.02)';
        activeItem.style.boxShadow = '0 10px 30px rgba(99, 102, 241, 0.3)';
        activeItem.style.borderLeftColor = 'var(--accent-primary)';
        
        setTimeout(() => {
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
    }
}

function resetStrategyExplanation() {
    document.querySelectorAll('.strategy-explanation-item').forEach(item => {
        item.style.opacity = '1';
        item.style.transform = 'scale(1)';
        item.style.boxShadow = 'none';
    });
}

function getStrategyName(type) {
    const names = {
        'ma': '均线策略',
        'momentum': '动量策略',
        'volume': '成交量策略',
        'macd': 'MACD策略',
        'rsi': 'RSI策略',
        'bollinger': '布林带策略'
    };
    return names[type] || type;
}

async function startAutoTrade() {
    const stockCode = document.getElementById('auto-stock-code').value.trim();
    const strategyType = document.getElementById('auto-strategy-type').value;
    const tradeAmount = parseFloat(document.getElementById('auto-trade-amount').value);
    const checkInterval = parseInt(document.getElementById('auto-check-interval').value);
    
    if (!stockCode || !tradeAmount || !checkInterval) {
        showToast('请填写完整的自动交易配置', 'error');
        return;
    }
    
    if (autoTradeInterval) {
        showToast('自动交易已在运行中', 'error');
        return;
    }
    
    document.getElementById('auto-trade-status').classList.add('active');
    document.getElementById('auto-trade-status-text').textContent = '运行中';
    document.getElementById('btn-start-auto-trade').disabled = true;
    document.getElementById('btn-stop-auto-trade').disabled = false;
    
    addAutoTradeLog('自动交易已启动', 'success');
    addAutoTradeLog(`股票: ${stockCode}, 策略: ${getStrategyName(strategyType)}, 金额: ${formatCurrency(tradeAmount)}, 间隔: ${checkInterval}秒`, 'info');
    
    autoTradeInterval = setInterval(async () => {
        try {
            const result = await fetchAPI('/strategy/analyze', {
                method: 'POST',
                body: JSON.stringify({
                    stock_code: stockCode,
                    strategy_type: strategyType
                })
            });
            
            if (result.success && result.data) {
                const signal = result.data.signal;
                const quote = await fetchAPI(`/stock/quote?stock_code=${stockCode}`);
                
                if (quote.success) {
                    const price = quote.data.current_price;
                    const shares = Math.floor(tradeAmount / price / 100) * 100;
                    
                    if (signal === 'buy' && shares > 0) {
                        addAutoTradeLog(`策略信号: 买入, 价格: ${price.toFixed(2)}, 数量: ${shares}`, 'info');
                        
                        const buyResult = await fetchAPI('/trade/buy', {
                            method: 'POST',
                            body: JSON.stringify({
                                stock_code: stockCode,
                                stock_name: quote.data.stock_name,
                                price: price,
                                shares: shares
                            })
                        });
                        
                        if (buyResult.success) {
                            addAutoTradeLog(`买入成功: ${shares}股 @ ${price.toFixed(2)}`, 'success');
                        } else {
                            addAutoTradeLog(`买入失败: ${buyResult.message}`, 'error');
                        }
                    } else if (signal === 'sell') {
                        const positionsResult = await fetchAPI('/positions');
                        if (positionsResult.success) {
                            const position = positionsResult.data.find(p => p.stock_code === stockCode);
                            if (position && position.shares > 0) {
                                addAutoTradeLog(`策略信号: 卖出, 价格: ${price.toFixed(2)}, 数量: ${position.shares}`, 'info');
                                
                                const sellResult = await fetchAPI('/trade/sell', {
                                    method: 'POST',
                                    body: JSON.stringify({
                                        stock_code: stockCode,
                                        stock_name: quote.data.stock_name,
                                        price: price,
                                        shares: position.shares
                                    })
                                });
                                
                                if (sellResult.success) {
                                    addAutoTradeLog(`卖出成功: ${position.shares}股 @ ${price.toFixed(2)}`, 'success');
                                } else {
                                    addAutoTradeLog(`卖出失败: ${sellResult.message}`, 'error');
                                }
                            }
                        }
                    }
                }
            }
        } catch (error) {
            addAutoTradeLog(`执行错误: ${error.message}`, 'error');
        }
    }, checkInterval * 1000);
    
    showToast('自动交易已启动', 'success');
}

function stopAutoTrade() {
    if (autoTradeInterval) {
        clearInterval(autoTradeInterval);
        autoTradeInterval = null;
        
        document.getElementById('auto-trade-status').classList.remove('active');
        document.getElementById('auto-trade-status-text').textContent = '已停止';
        document.getElementById('btn-start-auto-trade').disabled = false;
        document.getElementById('btn-stop-auto-trade').disabled = true;
        
        addAutoTradeLog('自动交易已停止', 'info');
        showToast('自动交易已停止', 'info');
    }
}

function addAutoTradeLog(message, type = 'info') {
    const logContent = document.getElementById('auto-trade-log-content');
    const timestamp = new Date().toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `
        <span class="timestamp">[${timestamp}]</span>
        <span class="message">${message}</span>
    `;
    
    if (logContent.querySelector('.placeholder-text')) {
        logContent.innerHTML = '';
    }
    
    logContent.insertBefore(entry, logContent.firstChild);
    
    const entries = logContent.querySelectorAll('.log-entry');
    if (entries.length > 100) {
        logContent.removeChild(entries[entries.length - 1]);
    }
}

function clearAutoTradeLog() {
    const logContent = document.getElementById('auto-trade-log-content');
    logContent.innerHTML = '<p class="placeholder-text">暂无交易日志</p>';
    showToast('日志已清空', 'info');
}

async function resetAccount() {
    if (confirm('确定要重置账户吗？这将清除所有交易记录和持仓。')) {
        const result = await fetchAPI('/account/reset', { method: 'POST' });
        if (result.success) {
            showToast('账户已重置', 'success');
            refreshAll();
        }
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    const navItem = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }
    
    const tabContent = document.getElementById(`tab-${tabName}`);
    if (tabContent) {
        tabContent.classList.add('active');
    }
    
    const titles = {
        'dashboard': '仪表盘',
        'trading': '交易',
        'positions': '持仓',
        'strategy': '策略',
        'auto-trade': '自动交易',
        'history': '历史记录'
    };
    
    document.getElementById('page-title').textContent = titles[tabName] || '仪表盘';
    
    if (tabName === 'dashboard') {
        setTimeout(() => updateMarketData(), 100);
    } else if (tabName === 'trading' && currentStock && currentStock.quote) {
        setTimeout(async () => await updateStockKlineChart(currentStock.quote), 100);
    }
}

async function fetchMarketIndex() {
    const result = await fetchAPI('/market/index?index_code=000001');
    return result;
}

async function fetchMarketIndexHistory(index_code = '000001', period = 'day', count = 30) {
    const result = await fetchAPI(`/market/index/history?index_code=${index_code}&period=${period}&count=${count}`);
    return result;
}

async function fetchStockHistory(stock_code, period = 'day', count = 30) {
    const result = await fetchAPI(`/stock/history?stock_code=${stock_code}&period=${period}&count=${count}`);
    return result;
}

async function initMarketChart(marketData = null) {
    const chartDom = document.getElementById('market-chart');
    if (!chartDom) return;
    
    if (charts.market) {
        charts.market.dispose();
    }
    
    charts.market = echarts.init(chartDom);
    
    let timestamps = [];
    let prices = [];
    let useRealData = false;
    
    // 获取真实历史数据
    const historyResult = await fetchMarketIndexHistory('000001', 'day', 30);
    if (historyResult.success && historyResult.data && historyResult.data.length > 0) {
        useRealData = true;
        // 使用真实历史数据
        historyResult.data.forEach(item => {
            timestamps.push(item.date);
            prices.push(item.close);
        });
    } else {
        // 生成基于真实价格的模拟数据（备用方案）
        const realPrice = marketData ? marketData.current_price : 4101.91;
        const basePrice = realPrice;
        timestamps = ['09:30', '10:00', '10:30', '11:00', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00'];
        prices = timestamps.map((time, index) => {
            const randomFactor = (Math.random() - 0.5) * 20;
            return basePrice + randomFactor;
        });
    }
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: timestamps,
            axisLine: {
                lineStyle: {
                    color: '#a0aec0'
                }
            },
            axisLabel: {
                color: '#a0aec0',
                rotate: useRealData ? 45 : 0
            }
        },
        yAxis: {
            type: 'value',
            axisLine: {
                lineStyle: {
                    color: '#a0aec0'
                }
            },
            axisLabel: {
                color: '#a0aec0'
            },
            splitLine: {
                lineStyle: {
                    color: '#2d3748'
                }
            },
            // 设置合适的y轴范围
            min: Math.min(...prices) - 5,
            max: Math.max(...prices) + 5
        },
        series: [{
            name: '上证指数',
            type: 'line',
            smooth: true,
            data: prices,
            lineStyle: {
                width: 3,
                color: marketData && marketData.change_percent >= 0 ? '#ef4444' : '#10b981'
            },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: marketData && marketData.change_percent >= 0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)' },
                    { offset: 1, color: marketData && marketData.change_percent >= 0 ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }
                ])
            }
        }]
    };
    
    charts.market.setOption(option);
}

async function updateMarketData() {
    const result = await fetchMarketIndex();
    if (result.success) {
        const indexData = result.data;
        if (indexData) {
            // 显示真实的上证指数数字
            const marketStatusText = document.getElementById('market-status-text');
            if (marketStatusText) {
                const changePercent = indexData.change_percent;
                const statusClass = changePercent >= 0 ? 'positive' : 'negative';
                marketStatusText.innerHTML = `上证指数: ${indexData.current_price.toFixed(2)} <span class="${statusClass}">${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%</span>`;
            }
            
            // 更新走势图
            initMarketChart(indexData);
        }
    }
}

function updatePortfolioChart(positions = []) {
    const chartDom = document.getElementById('portfolio-chart');
    if (!chartDom) return;
    
    if (charts.portfolio) {
        charts.portfolio.dispose();
    }
    
    charts.portfolio = echarts.init(chartDom);
    
    if (positions.length === 0) {
        charts.portfolio.setOption({
            backgroundColor: 'transparent',
            title: {
                text: '暂无持仓',
                left: 'center',
                top: 'center',
                textStyle: {
                    color: '#718096',
                    fontSize: 14
                }
            }
        });
        return;
    }
    
    const data = positions.map(p => ({
        name: p.stock_name,
        value: p.market_value
    }));
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: {
                color: '#a0aec0'
            }
        },
        series: [{
            name: '持仓分布',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['40%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#1e2445',
                borderWidth: 2
            },
            label: {
                show: false,
                position: 'center'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold',
                    color: '#ffffff'
                }
            },
            labelLine: {
                show: false
            },
            data: data
        }]
    };
    
    charts.portfolio.setOption(option);
}

async function updateStockKlineChart(quote) {
    const chartDom = document.getElementById('stock-kline-chart');
    if (!chartDom) return;
    
    if (charts.kline) {
        charts.kline.dispose();
    }
    
    charts.kline = echarts.init(chartDom);
    
    const dates = [];
    const values = [];
    const currentPrice = quote.current_price;
    
    let useRealData = false;
    let days = 30;
    
    if (currentKlinePeriod === 'week') {
        days = 20;
    } else if (currentKlinePeriod === 'month') {
        days = 12;
    }
    
    // 获取真实历史数据
    const historyResult = await fetchStockHistory(quote.stock_code, currentKlinePeriod, days);
    if (historyResult.success && historyResult.data && historyResult.data.length > 0) {
        useRealData = true;
        // 使用真实历史数据
        historyResult.data.forEach(item => {
            dates.push(item.date);
            values.push(item.close);
        });
    } else {
        // 生成基于真实价格的模拟数据（备用方案）
        const openPrice = quote.open_price;
        const highPrice = quote.high_price;
        const lowPrice = quote.low_price;
        const preClose = quote.pre_close;
        
        let basePrice = preClose;
        
        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - 1 - i));
            dates.push(`${date.getMonth() + 1}/${date.getDate()}`);
            
            const volatility = (highPrice - lowPrice) / 4;
            const randomChange = (Math.random() - 0.5) * volatility;
            basePrice += randomChange;
            
            if (i === days - 1) {
                basePrice = currentPrice;
            }
            
            values.push(parseFloat(basePrice.toFixed(2)));
        }
    }
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            },
            formatter: function(params) {
                const date = params[0].name;
                const price = params[0].value;
                return `日期: ${date}<br/>价格: ¥${price.toFixed(2)}`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLine: {
                lineStyle: {
                    color: '#a0aec0'
                }
            },
            axisLabel: {
                color: '#a0aec0',
                rotate: useRealData ? 45 : 0
            }
        },
        yAxis: {
            type: 'value',
            axisLine: {
                lineStyle: {
                    color: '#a0aec0'
                }
            },
            axisLabel: {
                color: '#a0aec0',
                formatter: function(value) {
                    return '¥' + value.toFixed(2);
                }
            },
            splitLine: {
                lineStyle: {
                    color: '#2d3748'
                }
            }
        },
        series: [{
            name: '股价',
            type: 'line',
            smooth: true,
            data: values,
            lineStyle: {
                width: 2,
                color: quote.change_percent >= 0 ? '#ef4444' : '#10b981'
            },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: quote.change_percent >= 0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)' },
                    { offset: 1, color: quote.change_percent >= 0 ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }
                ])
            },
            markPoint: {
                data: [
                    {
                        name: '当前价格',
                        coord: [dates[dates.length - 1], currentPrice],
                        value: currentPrice,
                        itemStyle: {
                            color: quote.change_percent >= 0 ? '#ef4444' : '#10b981'
                        },
                        label: {
                            show: true,
                            position: 'top',
                            formatter: '¥{c}',
                            color: quote.change_percent >= 0 ? '#ef4444' : '#10b981',
                            fontWeight: 'bold'
                        }
                    }
                ]
            }
        }]
    };
    
    charts.kline.setOption(option);
}

function toggleTheme() {
    showToast('主题切换功能开发中', 'info');
}

async function refreshAll() {
    await Promise.all([
        loadAccount(),
        loadPositions(),
        loadTrades(),
        updateMarketData()  // 添加刷新市场指数数据
    ]);
    
    if (currentStock) {
        await selectStock(currentStock);
    }
}

async function refreshPositions() {
    await loadPositions();
    showToast('持仓已刷新', 'success');
}

async function refreshTrades() {
    await loadTrades();
    showToast('交易记录已刷新', 'success');
}

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const tabName = item.getAttribute('data-tab');
        switchTab(tabName);
    });
});

document.getElementById('search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchStock();
    }
});

document.querySelectorAll('.chart-btn[data-period]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        const period = e.target.getAttribute('data-period');
        currentKlinePeriod = period;
        
        document.querySelectorAll('.chart-btn[data-period]').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        if (currentStock && currentStock.quote) {
            await updateStockKlineChart(currentStock.quote);
        }
    });
});

window.addEventListener('resize', () => {
    Object.values(charts).forEach(chart => {
        if (chart) {
            chart.resize();
        }
    });
});

window.onload = () => {
    refreshAll();
    updateMarketData();
    showToast('欢迎使用QuantTrade智能量化交易平台', 'info');
};
