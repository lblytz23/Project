import requests

# 登录URL
login_url = 'https://www.mingtuiw.com/membership-login'

# 用户名和密码
username = 'lblytz23@live.cn'
password = '551866'

# 创建一个会话对象
session = requests.Session()

# 设置请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# 登录数据
login_data = {
    'username': username,
    'password': password,
    'remember': 'on'  # 如果有记住登录选项
}

# 发送POST请求进行登录
response = session.post(login_url, data=login_data, headers=headers)

# 打印响应内容以进行调试
print(response.text)

# 检查是否登录成功
if "欢迎" in response.text or response.ok:
    print("登录成功")
else:
    print("登录失败")
