"""
测试环境清理脚本 - 清理测试数据库和用户
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, drop_database
from test_config import (
    TEST_DB_CONFIG,
    TEST_KEY_CONFIG,
    PROJECT_ROOT,
    ADMIN_DB_CONNECTION_STRING,
)

logger = logging.getLogger("测试环境清理")


def cleanup_test_database():
    """清理测试数据库和用户"""
    logger.info("开始清理测试数据库和用户...")

    # 使用预定义的管理员连接字符串
    engine = create_engine(ADMIN_DB_CONNECTION_STRING)

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


def cleanup_test_keys():
    """清理测试密钥文件"""
    logger.info("开始清理测试密钥文件...")

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
            return True
        except Exception as e:
            logger.error(f"清理测试密钥文件失败: {e}")
            return False
    return True


def get_user_confirmation(prompt):
    """
    获取用户确认

    Args:
        prompt: 提示信息

    Returns:
        bool: 用户是否确认
    """
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("请输入 y 或 n")


def cleanup_test_output_files():
    """清理测试生成的输出文件，需要用户确认"""
    logger.info("准备清理测试生成的输出文件...")

    # 需要确认清理的测试文件
    test_files = [
        os.path.join(PROJECT_ROOT, "test", "test_export.json"),
        os.path.join(PROJECT_ROOT, "test", "record_ids.json"),
        os.path.join(PROJECT_ROOT, "test", "test_config_override.py"),
        os.path.join(PROJECT_ROOT, "test", "performance_results.json"),
        os.path.join(PROJECT_ROOT, "test", "test_export_specific.json"),
        os.path.join(PROJECT_ROOT, "test", "test_export_all.json"),
        os.path.join(PROJECT_ROOT, "test", "test_report.txt"),
        os.path.join(PROJECT_ROOT, "test", "test.log"),
    ]

    # 检查哪些文件存在
    existing_files = [f for f in test_files if os.path.exists(f)]

    if not existing_files:
        logger.info("没有找到需要清理的测试输出文件")
        return True

    # 显示找到的文件
    print("\n发现以下测试输出文件:")
    for i, file_path in enumerate(existing_files, 1):
        print(f"{i}. {os.path.basename(file_path)}")

    # 询问用户是否清理
    if not get_user_confirmation("\n是否清理这些测试输出文件?"):
        logger.info("用户选择保留测试输出文件")
        return True

    # 清理文件
    success = True
    for file_path in existing_files:
        try:
            os.remove(file_path)
            logger.info(f"删除文件: {file_path}")
        except Exception as e:
            logger.error(f"删除文件 {file_path} 失败: {e}")
            success = False

    if success:
        logger.info("测试输出文件清理完成")
    else:
        logger.warning("部分测试输出文件清理失败")

    return success


def cleanup_test_environment():
    """清理完整测试环境"""
    logger.info("开始清理测试环境...")
    print("测试环境清理工具")
    print("=" * 50)

    # 无需确认，直接清理数据库和用户
    db_success = cleanup_test_database()

    # 无需确认，直接清理密钥文件
    keys_success = cleanup_test_keys()

    # 需要用户确认的测试输出文件清理
    files_success = cleanup_test_output_files()

    if db_success and keys_success and files_success:
        logger.info("测试环境清理完成")
        print("\n测试环境清理完成")
        return True
    else:
        logger.error("测试环境清理部分失败")
        print("\n测试环境清理部分失败，请查看日志获取详情")
        return False


if __name__ == "__main__":
    success = cleanup_test_environment()
    sys.exit(0 if success else 1)
