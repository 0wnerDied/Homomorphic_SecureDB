"""
测试环境设置脚本 - 创建测试数据库和用户
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database, drop_database
from test_config import (
    TEST_DB_CONFIG,
    PROJECT_ROOT,
    ADMIN_DB_CONNECTION_STRING,
    TEST_DB_CONNECTION_STRING,
)

logger = logging.getLogger("测试环境设置")


def run_admin_sql_command(command):
    """使用管理员权限运行SQL命令"""
    engine = create_engine(ADMIN_DB_CONNECTION_STRING)

    try:
        with engine.begin() as connection:
            connection.execute(text(command))
        return True
    except Exception as e:
        logger.error(f"SQL命令执行失败: {e}")
        return False


def create_test_database():
    """创建测试数据库和用户"""
    logger.info("开始创建测试数据库和用户...")

    # 使用预定义的管理员连接字符串
    engine = create_engine(ADMIN_DB_CONNECTION_STRING)

    try:
        # 检查并删除已存在的用户
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    f"SELECT 1 FROM pg_roles WHERE rolname = '{TEST_DB_CONFIG['user']}'"
                )
            )
            if result.fetchone():
                logger.info(
                    f"测试用户 {TEST_DB_CONFIG['user']} 已存在, 将删除并重新创建"
                )
                # 确保删除用户前删除其拥有的数据库
                db_url = f"postgresql://{TEST_DB_CONFIG['admin_user']}:{TEST_DB_CONFIG['admin_password']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
                if database_exists(db_url):
                    drop_database(db_url)
                connection.execute(
                    text(f"DROP USER IF EXISTS {TEST_DB_CONFIG['user']}")
                )

            # 创建用户
            connection.execute(
                text(
                    f"CREATE USER {TEST_DB_CONFIG['user']} WITH PASSWORD '{TEST_DB_CONFIG['password']}'"
                )
            )
            logger.info(f"创建测试用户 {TEST_DB_CONFIG['user']} 成功")

            # 创建数据库
            db_url = f"postgresql://{TEST_DB_CONFIG['admin_user']}:{TEST_DB_CONFIG['admin_password']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
            if database_exists(db_url):
                drop_database(db_url)
            create_database(db_url)
            logger.info(f"创建测试数据库 {TEST_DB_CONFIG['database']} 成功")

            # 授予权限
            connection.execute(
                text(
                    f"GRANT ALL PRIVILEGES ON DATABASE {TEST_DB_CONFIG['database']} TO {TEST_DB_CONFIG['user']}"
                )
            )
            logger.info(f"授予权限成功")

        logger.info("测试数据库和用户创建成功")
        return True

    except Exception as e:
        logger.error(f"创建测试数据库和用户失败: {e}")
        return False


def create_test_config():
    """创建测试配置文件"""
    logger.info("创建测试配置文件...")

    test_config_content = f"""
# 测试环境配置 - 民航客户隐私数据安全数据库系统
DB_CONNECTION_STRING = "{TEST_DB_CONNECTION_STRING}"

# 加密配置
ENCRYPTION_CONFIG = {{
    "fhe": {{
        "key_size": 2048,
        "precision": 40
    }}
}}

# 日志配置
LOG_CONFIG = {{
    "level": "INFO",
    "log_file": "{os.path.join(PROJECT_ROOT, 'test', 'test.log')}"
}}

# 密钥管理
KEY_MANAGEMENT = {{
    "keys_dir": "{os.path.join(PROJECT_ROOT, 'test', 'keys')}",
    "aes_key_file": "test_aes.key",
    "fhe_public_key": "test_fhe_public.key",
    "fhe_private_key": "test_fhe_private.key"
}}

# 性能配置
PERFORMANCE_CONFIG = {{
    "cache_size": 50,
    "batch_size": 10,
    "timeout": 30
}}
"""

    # 确保test目录存在
    os.makedirs(os.path.join(PROJECT_ROOT, "test"), exist_ok=True)

    # 写入测试配置文件
    test_config_path = os.path.join(PROJECT_ROOT, "test", "test_config_override.py")
    with open(test_config_path, "w") as f:
        f.write(test_config_content)

    logger.info(f"测试配置文件已创建: {test_config_path}")
    return True


def setup_test_environment():
    """设置完整测试环境"""
    logger.info("开始设置测试环境...")

    # 创建测试数据库和用户
    if not create_test_database():
        logger.error("创建测试数据库和用户失败")
        return False

    # 创建测试配置文件
    if not create_test_config():
        logger.error("创建测试配置文件失败")
        return False

    # 创建测试密钥目录
    keys_dir = os.path.join(PROJECT_ROOT, "test", "keys")
    os.makedirs(keys_dir, exist_ok=True)
    logger.info(f"创建测试密钥目录: {keys_dir}")

    logger.info("测试环境设置完成")
    return True


if __name__ == "__main__":
    success = setup_test_environment()
    sys.exit(0 if success else 1)
