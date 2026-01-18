// 使用当前页面的主机名作为API基础URL，解决手机连接局域网时的问题
const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000/api`;

let currentStock = null;
let autoTradeInterval = null;
let charts = {};
let currentKlinePeriod = 'day';

// 记录自动交易的原始状态，用于开盘时恢复
let autoTradeOriginalState = {
    isRunning: false,
    stockCode: '',
    strategyType: '',
    tradeAmount: null,
    useAllCash: false,
    checkInterval: 60
};

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
    const useAllCash = document.getElementById('use-all-cash').checked;
    const tradeAmountInput = document.getElementById('auto-trade-amount');
    const checkInterval = parseInt(document.getElementById('auto-check-interval').value);
    
    if (!stockCode || !checkInterval) {
        showToast('请填写完整的自动交易配置', 'error');
        return;
    }
    
    if (!useAllCash && (!tradeAmountInput.value || parseFloat(tradeAmountInput.value) <= 0)) {
        showToast('请填写交易金额或选择使用全部可用资金', 'error');
        return;
    }
    
    if (autoTradeInterval) {
        showToast('自动交易已在运行中', 'error');
        return;
    }
    
    // 检查当前时间是否处于交易时间
    const now = new Date();
    const isTradingTime = isInTradingHours(now);
    if (!isTradingTime) {
        showToast('当前处于非交易时间，无法启动自动交易', 'error');
        return;
    }
    
    document.getElementById('auto-trade-status').classList.add('active');
    document.getElementById('auto-trade-status-text').textContent = '运行中';
    document.getElementById('btn-start-auto-trade').disabled = true;
    document.getElementById('btn-stop-auto-trade').disabled = false;
    
    addAutoTradeLog('自动交易已启动', 'success');
    
    // 获取初始交易金额
    let tradeAmount = useAllCash ? null : parseFloat(tradeAmountInput.value);
    
    // 保存自动交易配置到localStorage
    const autoTradeConfig = {
        isRunning: true,
        stockCode: stockCode,
        strategyType: strategyType,
        tradeAmount: tradeAmount,
        useAllCash: useAllCash,
        checkInterval: checkInterval
    };
    localStorage.setItem('autoTradeConfig', JSON.stringify(autoTradeConfig));
    
    // 保存自动交易的原始状态
    autoTradeOriginalState = {
        isRunning: true,
        stockCode: stockCode,
        strategyType: strategyType,
        tradeAmount: tradeAmount,
        useAllCash: useAllCash,
        checkInterval: checkInterval
    };
    
    autoTradeInterval = setInterval(async () => {
        try {
            // 获取可用资金（如果需要）
            if (useAllCash) {
                const accountResult = await fetchAPI('/account');
                if (accountResult.success) {
                    tradeAmount = accountResult.data.available_cash;
                }
            }
            
            // 确定使用的策略
            let currentStrategy = strategyType;
            if (strategyType === 'auto') {
                // 自动选择策略（平衡六种策略）
                currentStrategy = selectBestStrategy(stockCode);
            }
            
            addAutoTradeLog(`正在使用 ${getStrategyName(currentStrategy)} 进行分析...`, 'info');
            
            const result = await fetchAPI('/strategy/analyze', {
                method: 'POST',
                body: JSON.stringify({
                    stock_code: stockCode,
                    strategy_type: currentStrategy
                })
            });
            
            if (result.success && result.data) {
                // 显示计算过程
                displayCalculationProcess(result.data);
                
                const signal = result.data.signal;
                const quote = await fetchAPI(`/stock/quote?stock_code=${stockCode}`);
                
                if (quote.success) {
                            const price = quote.data.current_price;
                            // 计算可买股数（A股交易最小单位为100股）
                            const maxShares = Math.floor(tradeAmount / price / 100) * 100;
                            
                            addAutoTradeLog(`策略信号: ${signal}, 当前价格: ${price.toFixed(2)}, 可用资金: ${formatCurrency(tradeAmount)}, 可买股数: ${maxShares}股`, 'info');
                            
                            if (signal === 'buy' && maxShares > 0) {
                                addAutoTradeLog(`执行买入操作: ${maxShares}股 @ ${price.toFixed(2)}`, 'info');
                                
                                const buyResult = await fetchAPI('/trade/buy', {
                                    method: 'POST',
                                    body: JSON.stringify({
                                        stock_code: stockCode,
                                        stock_name: quote.data.stock_name,
                                        price: price,
                                        shares: maxShares
                                    })
                                });
                                
                                if (buyResult.success) {
                                    addAutoTradeLog(`买入成功: ${maxShares}股 @ ${price.toFixed(2)}`, 'success');
                                    // 刷新持仓数据
                                    loadPositions();
                                } else {
                                    addAutoTradeLog(`买入失败: ${buyResult.message}`, 'error');
                                }
                            } else if (signal === 'buy' && maxShares <= 0) {
                                addAutoTradeLog(`可用资金不足，无法买入 ${quote.data.stock_name}。当前价格: ${price.toFixed(2)}元，可用资金: ${formatCurrency(tradeAmount)}元，需要至少 ${formatCurrency(price * 100)}元才能买入100股。`, 'warning');
                            } else if (signal === 'sell') {
                        const positionsResult = await fetchAPI('/positions');
                        if (positionsResult.success) {
                            const position = positionsResult.data.find(p => p.stock_code === stockCode);
                            if (position && position.shares > 0) {
                                addAutoTradeLog(`执行卖出操作: ${position.shares}股 @ ${price.toFixed(2)}`, 'info');
                                
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
                                    // 刷新持仓数据
                                    loadPositions();
                                } else {
                                    addAutoTradeLog(`卖出失败: ${sellResult.message}`, 'error');
                                }
                            } else {
                                addAutoTradeLog('没有持仓可卖出', 'info');
                            }
                        }
                    } else {
                        addAutoTradeLog('策略信号为持有，不执行交易', 'info');
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
        
        // 更新原始状态为非运行状态
        autoTradeOriginalState.isRunning = false;
        
        // 从localStorage中移除自动交易配置
        localStorage.removeItem('autoTradeConfig');
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

/**
 * 自动选择最佳策略（平衡六种策略）
 */
function selectBestStrategy(stockCode) {
    const strategies = ['ma', 'momentum', 'volume', 'macd', 'rsi', 'bollinger'];
    
    // 使用时间戳的模运算来平衡选择策略，确保六种策略都能被均匀使用
    const now = Date.now();
    const strategyIndex = now % strategies.length;
    
    return strategies[strategyIndex];
}

/**
 * 显示计算过程的可视化反馈
 */
function displayCalculationProcess(strategyData) {
    if (!strategyData || !strategyData.calculation_steps) {
        return;
    }
    
    const steps = strategyData.calculation_steps;
    
    // 添加策略名称到日志
    addAutoTradeLog(`=== ${getStrategyName(strategyData.strategy_type)} 计算过程 ===`, 'info');
    
    // 添加关键步骤到日志
    steps.forEach(step => {
        let stepMessage = `${step.step}. ${step.name}: ${step.description}`;
        
        // 添加关键数据到日志
        if (step.results) {
            const results = Object.entries(step.results)
                .map(([key, value]) => `${key}: ${typeof value === 'number' ? value.toFixed(4) : value}`)
                .join(', ');
            stepMessage += ` | 结果: ${results}`;
        }
        
        addAutoTradeLog(stepMessage, 'info');
    });
    
    // 添加最终信号到日志
    addAutoTradeLog(`最终信号: ${strategyData.signal} | ${strategyData.reason}`, 'success');
}

// 全局变量，记录当前市场指数图的周期
let currentMarketPeriod = 'day';

async function initMarketChart(marketData = null, period = 'day') {
    const chartDom = document.getElementById('market-chart');
    if (!chartDom) return;
    
    // 更新当前周期
    currentMarketPeriod = period;
    
    if (charts.market) {
        charts.market.dispose();
    }
    
    charts.market = echarts.init(chartDom);
    
    let timestamps = [];
    let prices = [];
    let useRealData = false;
    
    // 获取不同周期的历史数据
    let count = 30; // 默认获取30条数据
    if (period === 'week') {
        count = 20; // 周线获取20周数据
    } else if (period === 'month') {
        count = 12; // 月线获取12月数据
    }
    
    // 获取真实历史数据
    const historyResult = await fetchMarketIndexHistory('000001', period, count);
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
        timestamps = [];
        prices = [];
        
        // 根据不同周期生成模拟数据
        for (let i = count - 1; i >= 0; i--) {
            const date = new Date();
            if (period === 'day') {
                date.setDate(date.getDate() - i);
                timestamps.push(`${date.getMonth() + 1}/${date.getDate()}`);
            } else if (period === 'week') {
                date.setDate(date.getDate() - i * 7);
                timestamps.push(`${date.getMonth() + 1}/${date.getDate()}`);
            } else if (period === 'month') {
                date.setMonth(date.getMonth() - i);
                timestamps.push(`${date.getFullYear()}/${date.getMonth() + 1}`);
            }
            
            const randomFactor = (Math.random() - 0.5) * 20;
            prices.push(basePrice + randomFactor);
        }
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
            
            // 更新走势图，传递当前周期
            await initMarketChart(indexData, currentMarketPeriod);
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

/**
 * 切换主题（深色/浅色）
 */
function toggleTheme() {
    const body = document.body;
    // 检查当前主题
    const isLightTheme = body.classList.contains('light-theme');
    
    if (isLightTheme) {
        // 切换到深色主题
        body.classList.remove('light-theme');
        localStorage.setItem('theme', 'dark');
        showToast('已切换到深色主题', 'success');
    } else {
        // 切换到浅色主题
        body.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
        showToast('已切换到浅色主题', 'success');
    }
    
    // 重新初始化图表，确保主题样式生效
    if (currentStock && currentStock.quote) {
        updateStockKlineChart(currentStock.quote);
    }
    updateMarketData();
}

/**
 * 显示当前时间和交易状态
 */
function updateCurrentTime() {
    const now = new Date();
    
    // 格式化当前时间
    const timeStr = now.toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    const dateStr = now.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
    
    // 判断是否处于交易时间
    const isTradingTime = isInTradingHours(now);
    const tradingStatusText = isTradingTime ? '市场交易中' : '非交易时间';
    
    // 更新页面上的时间和交易状态
    const timeElement = document.createElement('div');
    timeElement.className = 'current-time';
    timeElement.innerHTML = `${dateStr} ${timeStr} | ${tradingStatusText}`;
    
    // 找到market-status元素，在其前面插入时间元素
    const marketStatusElement = document.querySelector('.market-status');
    const existingTimeElement = document.querySelector('.current-time');
    
    if (existingTimeElement) {
        existingTimeElement.remove();
    }
    
    marketStatusElement.parentNode.insertBefore(timeElement, marketStatusElement);
}

/**
 * 判断当前时间是否处于A股交易时间
 * 交易时间：周一至周五
 * 上午：9:30-11:30
 * 下午：13:00-15:00
 */
function isInTradingHours(date) {
    const day = date.getDay();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    
    // 周末不交易
    if (day === 0 || day === 6) {
        return false;
    }
    
    // 上午交易时间
    const isMorningTrading = hours >= 9 && (hours > 9 || minutes >= 30) && hours < 11 || (hours === 11 && minutes <= 30);
    
    // 下午交易时间
    const isAfternoonTrading = hours >= 13 && hours < 15;
    
    return isMorningTrading || isAfternoonTrading;
}

/**
 * 监测交易时间，自动调整自动交易状态
 * 在收盘时暂停自动交易，开盘时自动启动自动交易
 */
function monitorTradingTime() {
    const now = new Date();
    const isTradingTime = isInTradingHours(now);
    
    // 检查自动交易当前状态
    const isAutoTradeRunning = autoTradeInterval !== null;
    
    if (!isTradingTime && isAutoTradeRunning) {
        // 非交易时间且自动交易正在运行，暂停自动交易
        addAutoTradeLog('非交易时间，自动暂停自动交易', 'warning');
        stopAutoTrade();
    } else if (isTradingTime && !isAutoTradeRunning) {
        // 交易时间且自动交易不在运行，尝试自动启动
        
        // 检查是否有自动交易配置
        const stockCode = document.getElementById('auto-stock-code').value.trim();
        const checkInterval = parseInt(document.getElementById('auto-check-interval').value);
        const useAllCash = document.getElementById('use-all-cash').checked;
        const tradeAmountInput = document.getElementById('auto-trade-amount');
        
        // 检查必要配置是否已填写
        if (stockCode && checkInterval) {
            if (useAllCash || (tradeAmountInput.value && parseFloat(tradeAmountInput.value) > 0)) {
                addAutoTradeLog('交易时间，自动启动自动交易', 'success');
                
                // 启动自动交易
                startAutoTrade();
            } else {
                addAutoTradeLog('交易时间，但自动交易配置不完整，无法自动启动', 'warning');
            }
        } else {
            addAutoTradeLog('交易时间，但自动交易配置不完整，无法自动启动', 'warning');
        }
    }
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

/**
 * 切换交易金额输入框的可用性
 */
function toggleTradeAmountInput() {
    const useAllCash = document.getElementById('use-all-cash').checked;
    const tradeAmountInput = document.getElementById('auto-trade-amount');
    
    if (useAllCash) {
        tradeAmountInput.value = '';
        tradeAmountInput.disabled = true;
        tradeAmountInput.placeholder = '使用全部可用资金';
    } else {
        tradeAmountInput.disabled = false;
        tradeAmountInput.placeholder = '输入交易金额';
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
        
        // 检查是否是市场指数图的周期切换按钮
        const chartCard = e.target.closest('.chart-card');
        if (chartCard && chartCard.querySelector('#market-chart')) {
            // 更新市场指数图周期
            currentMarketPeriod = period;
            
            // 更新按钮状态
            document.querySelectorAll('.chart-card .chart-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            // 重新加载市场指数数据
            await updateMarketData();
        } else {
            // 股票K线图周期切换
            currentKlinePeriod = period;
            
            document.querySelectorAll('.chart-btn[data-period]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            if (currentStock && currentStock.quote) {
                await updateStockKlineChart(currentStock.quote);
            }
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
    // 初始化主题
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }
    
    refreshAll();
    updateMarketData();
    showToast('欢迎使用QuantTrade智能量化交易平台', 'info');
    
    // 初始化时间显示
    updateCurrentTime();
    // 设置定时器，每秒更新时间
    setInterval(updateCurrentTime, 1000);
    
    // 启动交易时间监测，每分钟检查一次
    setInterval(monitorTradingTime, 60000);
    
    // 检查localStorage中是否有自动交易配置，如果有则自动启动
    const autoTradeConfig = localStorage.getItem('autoTradeConfig');
    if (autoTradeConfig) {
        try {
            const config = JSON.parse(autoTradeConfig);
            if (config.isRunning) {
                // 恢复自动交易配置
                document.getElementById('auto-stock-code').value = config.stockCode;
                document.getElementById('auto-strategy-type').value = config.strategyType;
                document.getElementById('auto-trade-amount').value = config.tradeAmount || '';
                document.getElementById('use-all-cash').checked = config.useAllCash;
                document.getElementById('auto-check-interval').value = config.checkInterval;
                
                // 恢复交易金额输入框的状态
                toggleTradeAmountInput();
                
                // 更新原始状态
                autoTradeOriginalState = {
                    isRunning: true,
                    stockCode: config.stockCode,
                    strategyType: config.strategyType,
                    tradeAmount: config.tradeAmount,
                    useAllCash: config.useAllCash,
                    checkInterval: config.checkInterval
                };
                
                // 显示自动交易正在恢复的提示
                showToast('正在恢复自动交易...', 'info');
                
                // 延迟启动自动交易，确保页面完全加载
                setTimeout(() => {
                    startAutoTrade();
                }, 1000);
            }
        } catch (error) {
            console.error('恢复自动交易配置失败:', error);
        }
    }
};
