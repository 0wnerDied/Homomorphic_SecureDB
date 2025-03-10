"""
测试环境清理脚本 - 清理测试数据库和用户
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, drop_database
from test_config import TEST_DB_CONFIG, TEST_KEY_CONFIG, PROJECT_ROOT

logger = logging.getLogger("测试环境清理")


def cleanup_test_database():
    """清理测试数据库和用户"""
    logger.info("开始清理测试数据库和用户...")

    # 创建管理员连接
    admin_connection_string = f"postgresql://{TEST_DB_CONFIG['admin_user']}:{TEST_DB_CONFIG['admin_password']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/postgres"
    engine = create_engine(admin_connection_string)

    try:
        # 检查并删除数据库
        db_url = f"postgresql://{TEST_DB_CONFIG['admin_user']}:{TEST_DB_CONFIG['admin_password']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        if database_exists(db_url):
            # 断开所有连接
            with engine.connect() as connection:
                connection.execute(
                    text(
                        f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{TEST_DB_CONFIG['database']}'
                AND pid <> pg_backend_pid();
                """
                    )
                )

            # 删除数据库
            drop_database(db_url)
            logger.info(f"删除测试数据库 {TEST_DB_CONFIG['database']} 成功")

        # 删除用户
        with engine.connect() as connection:
            connection.execute(text(f"DROP USER IF EXISTS {TEST_DB_CONFIG['user']}"))
            logger.info(f"删除测试用户 {TEST_DB_CONFIG['user']} 成功")

        logger.info("测试数据库和用户清理完成")
        return True

    except Exception as e:
        logger.error(f"清理测试数据库和用户失败: {e}")
        return False


def cleanup_test_files():
    """清理测试文件"""
    logger.info("开始清理测试文件...")

    # 清理测试密钥
    keys_dir = TEST_KEY_CONFIG["keys_dir"]
    if os.path.exists(keys_dir):
        try:
            for filename in os.listdir(keys_dir):
                file_path = os.path.join(keys_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"删除文件: {file_path}")

            os.rmdir(keys_dir)
            logger.info(f"删除目录: {keys_dir}")
        except Exception as e:
            logger.error(f"清理测试密钥文件失败: {e}")

    # 清理其他测试文件
    test_files = [
        os.path.join(PROJECT_ROOT, "test", "test_export.json"),
        os.path.join(PROJECT_ROOT, "test", "record_ids.json"),
        os.path.join(PROJECT_ROOT, "test", "test_config_override.py"),
        os.path.join(PROJECT_ROOT, "test", "performance_results.json"),
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件 {file_path} 失败: {e}")

    logger.info("测试文件清理完成")
    return True


def cleanup_test_environment():
    """清理完整测试环境"""
    logger.info("开始清理测试环境...")

    # 清理测试数据库和用户
    db_success = cleanup_test_database()

    # 清理测试文件
    files_success = cleanup_test_files()

    if db_success and files_success:
        logger.info("测试环境清理完成")
        return True
    else:
        logger.error("测试环境清理部分失败")
        return False


if __name__ == "__main__":
    success = cleanup_test_environment()
    sys.exit(0 if success else 1)
