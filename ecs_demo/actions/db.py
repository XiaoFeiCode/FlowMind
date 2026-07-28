# -*- coding: utf-8 -*-
"""
数据库连接模块

从 endpoints.yml 读取数据库连接配置，兼容本地开发和 Docker 部署。
"""
import os
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _get_db_url() -> str:
    """从环境变量或 endpoints.yml 构建数据库连接 URL。
    
    优先级: 环境变量 DATABASE_URL > endpoints.yml 配置 > 默认值
    """
    # 1. 环境变量直接指定（最简单）
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # 2. 各组件环境变量
    db_host = os.environ.get("MYSQL_HOST", "localhost")
    db_port = os.environ.get("MYSQL_PORT", "3306")
    db_user = os.environ.get("MYSQL_USER", "root")
    db_password = os.environ.get("MYSQL_PASSWORD", "123456")
    db_name = os.environ.get("MYSQL_DATABASE", "ecommerce")

    # 3. 尝试从 endpoints.yml 读取（如果文件存在）
    endpoints_path = Path(__file__).parent.parent / "endpoints.yml"
    if endpoints_path.exists():
        try:
            import yaml
            with open(endpoints_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            db_config = config.get("database", {})
            if isinstance(db_config, dict) and "url" in db_config:
                return db_config["url"]
        except Exception:
            pass  # 回退到环境变量
    
    return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


db_url = _get_db_url()

# 创建数据库引擎
engine = create_engine(db_url)
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
