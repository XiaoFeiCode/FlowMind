# -*- coding: utf-8 -*-
"""
数据库连接模块

从环境变量读取数据库连接配置，兼容本地开发和 Docker 部署。
"""
import os
import re
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _resolve_env(value: str) -> str:
    """解析字符串中的 ${VAR:default} 占位符"""
    def repl(m):
        var = m.group(1)
        default = m.group(2) if m.group(2) else ""
        return os.environ.get(var, default)
    return re.sub(r"\$\{(\w+)(?::([^}]*))?\}", repl, value)


def _get_db_url() -> str:
    """从环境变量或 endpoints.yml 构建数据库连接 URL。"""
    # 1. 环境变量直接指定
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # 2. 各组件环境变量（优先）
    db_host = os.environ.get("MYSQL_HOST", "localhost")
    db_port = os.environ.get("MYSQL_PORT", "3306")
    db_user = os.environ.get("MYSQL_USER", "root")
    db_password = os.environ.get("MYSQL_PASSWORD", "123456")
    db_name = os.environ.get("MYSQL_DATABASE", "ecommerce")

    # 3. 尝试从 endpoints.yml 读取 URL（兼容 ${VAR} 占位符）
    endpoints_path = Path(__file__).parent.parent / "endpoints.yml"
    if endpoints_path.exists():
        try:
            import yaml
            with open(endpoints_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            db_config = config.get("database", {})
            if isinstance(db_config, dict) and "url" in db_config:
                raw_url = db_config["url"]
                return _resolve_env(raw_url)  # ← 关键修复：解析 ${VAR} 占位符
        except Exception:
            pass

    return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


db_url = _get_db_url()

# 创建数据库引擎（延迟连接，不会在导入时报错）
engine = create_engine(db_url, pool_pre_ping=True, connect_args={"charset": "utf8mb4"})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


if __name__ == "__main__":

    def export_db_table_class(run=False):
        """将数据库表映射为Python类"""
        if not run:
            return
        output_path = "db_table_class.py"
        cmd = ["python", "-m", "sqlacodegen", db_url]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)

    export_db_table_class(True)
