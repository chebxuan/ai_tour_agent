# Hexa Blueprint™ API - Docker 镜像
# 北京行程规划服务 FastAPI 版本

FROM python:3.11-slim

# 设置工作目录
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
COPY survey_architect.py .
COPY product_engine.py .
COPY cost_engine.py .
COPY *.csv .
COPY mashes/ ./mashes/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]
