# ============================================================
# FlowMind Dockerfile
# 基于 Python 3.10 slim 镜像，CPU 推理模式
# ============================================================

FROM python:3.10-slim

LABEL maintainer="xiaoFei"
LABEL description="FlowMind · 汇智智能客服系统"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装（利用 Docker 层缓存）
COPY requirements-flowmind.txt .

# 安装 torch CPU 版（减少镜像体积 ~2GB）
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements-flowmind.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制源代码
COPY setup.py .
COPY flowmind/ ./flowmind/

# 以可编辑模式安装（保留源码引用）
RUN pip install -e . --no-deps

# ============================================================
# 运行配置
# ============================================================
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 默认端口（可通过环境变量覆盖）
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# 挂载点
# /app/models   — 嵌入模型文件 (bge-base-zh-v1.5)
# /app/data     — Flow 定义、actions 等业务数据

EXPOSE 8000

# 启动命令
CMD flowmind run \
    --model /app/data \
    --endpoints /app/data/endpoints.yml \
    --host ${APP_HOST} \
    --port ${APP_PORT}
