# 使用官方 Python 镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装 Microsoft Edge 浏览器和必要的依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | apt-key add - \
    && echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list \
    && apt-get update \
    && apt-get install -y microsoft-edge-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 下载并安装 EdgeDriver
RUN EDGE_VERSION=$(microsoft-edge --version | cut -d' ' -f3) \
    && EDGE_DRIVER_VERSION=$(curl -s "https://msedgedriver.azureedge.net/LATEST_RELEASE_${EDGE_VERSION%%.*}") \
    && wget -q "https://msedgedriver.azureedge.net/${EDGE_DRIVER_VERSION}/edgedriver_linux64.zip" \
    && unzip edgedriver_linux64.zip \
    && mv msedgedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/msedgedriver \
    && rm edgedriver_linux64.zip

# 复制项目文件
COPY requirements.txt .
COPY scraper.py .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据目录
RUN mkdir /data

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置入口点
ENTRYPOINT ["python", "scraper.py"] 