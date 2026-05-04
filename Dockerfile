# Hexa Blueprint™ API — Docker 镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY api_main.py .
COPY cli_app.py .
COPY schemas.py .
COPY engines/ ./engines/
COPY data/ ./data/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD uvicorn api_main:app --host 0.0.0.0 --port ${PORT:-8000}
