from flask import Flask, render_template, request, redirect, url_for
import requests
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

app = Flask(__name__)

# Alpha Vantage API Key
API_KEY = '您的API密钥'  # 确保使用有效的 API 密钥

def get_stock_data(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # 如果请求失败，这将引发异常
        data = response.json()
        print(f"API 响应: {data}")  # 打印 API 响应
        if 'Time Series (Daily)' not in data:
            if 'Error Message' in data:
                raise ValueError(f"API 错误: {data['Error Message']}")
            else:
                raise ValueError("API 返回的数据格式不正确")
        return data['Time Series (Daily)']
    except requests.RequestException as e:
        print(f"API 请求失败: {e}")
        return None
    except ValueError as e:
        print(f"数据处理错误: {e}")
        return None

def plot_stock_data(data, symbol):
    if not data:
        return None
    
    # 只取最近30天的数据
    dates = sorted(data.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'), reverse=True)[:30]
    dates = sorted(dates)
    prices = [float(data[date]['4. close']) for date in dates]

    # 将字符串日期转换为 datetime 对象
    dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

    fig, ax = plt.subplots(figsize=(10, 5))  # 减小图表大小
    ax.plot(dates, prices, label='收盘价')
    
    # 设置 x 轴
    ax.set_xlabel('日期')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # 设置 y 轴
    ax.set_ylabel('价格 (美元)')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:.2f}'))  # 修改为美元

    # 设置标题和图例
    ax.set_title(f'{symbol} 股票最近30天收盘价走势')
    ax.legend()

    # 自动旋转并对齐日期标签
    fig.autofmt_xdate()

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100)  # 降低 DPI 以减小文件大小
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close(fig)
    return plot_url

@app.route('/')
def index():
    stock_symbol = 'AAPL'  # 苹果公司的股票代码
    stock_data = get_stock_data(stock_symbol)
    if stock_data:
        plot_url = plot_stock_data(stock_data, "苹果公司")
        return render_template('index.html', plot_url=plot_url, stock_symbol="苹果公司 (AAPL)")
    else:
        error_message = "无法获取股票数据。请检查 API 密钥和网络连接。"
        return render_template('index.html', error=error_message)

@app.route('/strategy', methods=['GET', 'POST'])
def strategy():
    if request.method == 'POST':
        # 获取策略参数
        stock_symbol = request.form.get('stock_symbol')
        buy_condition = request.form.get('buy_condition')
        sell_condition = request.form.get('sell_condition')
        
        # 这里应该添加策略运行和回测的逻辑
        # 现在我们只是简单地返回一个消息
        result = f"策略已运行：股票 {stock_symbol}，买入条件 {buy_condition}，卖出条件 {sell_condition}"
        
        return render_template('strategy.html', result=result)
    
    return render_template('strategy.html')

@app.route('/test')
def test():
    return "测试路由正常工作"

if __name__ == '__main__':
    app.run(debug=True)