"""
测试数据导入导出功能
"""

import os
import sys
import logging
import random
import json
from test_config import PROJECT_ROOT, TEST_DATA_CONFIG

# 添加项目根目录到Python路径
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目模块
try:
    from core.secure_db import SecureDB
    from generate_test_data import generate_privacy_test_data
except ImportError as e:
    logger = logging.getLogger("数据导入导出测试")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确, 并且已安装所有依赖")
    sys.exit(1)

logger = logging.getLogger("数据导入导出测试")


def test_export_specific_records():
    """测试特定记录的导出功能"""
    logger.info("开始测试特定记录的导出功能...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 生成测试记录
        test_records = []
        record_ids = []

        logger.info("生成测试记录...")
        for _ in range(10):
            customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
            data = generate_privacy_test_data(customer_id)
            record_id = secure_db.add_record(customer_id, data, enable_range_query=True)
            record_ids.append(record_id)
            test_records.append(data)

        # 导出特定记录
        export_file = TEST_DATA_CONFIG["export_file_specific"]
        logger.info(f"导出特定记录到文件: {export_file}")

        export_count = secure_db.export_records(record_ids, export_file)
        if export_count == len(record_ids):
            logger.info(f"成功导出 {export_count} 条特定记录")
        else:
            logger.error(
                f"导出特定记录失败, 预期 {len(record_ids)} 条, 实际导出 {export_count} 条"
            )
            success = False

        if success:
            logger.info("特定记录导出测试通过")
        else:
            logger.error("特定记录导出测试失败")

        return success, record_ids, test_records, export_file

    except Exception as e:
        logger.error(f"特定记录导出测试出现异常: {e}")
        return False, [], [], ""


def test_import_specific_records(record_ids, test_records, export_file):
    """测试特定记录的导入功能"""
    logger.info("开始测试特定记录的导入功能...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 删除原记录
        logger.info("删除原始记录...")
        secure_db.delete_records_batch(record_ids)

        # 导入特定记录
        logger.info(f"从文件导入特定记录: {export_file}")
        import_result = secure_db.import_records(export_file)

        if import_result and len(import_result) == len(record_ids):
            logger.info(f"成功导入 {len(import_result)} 条特定记录")

            # 清除缓存，确保从数据库获取最新数据
            secure_db.clear_caches()

            # 验证导入的数据
            logger.info("验证导入的特定记录...")

            # 验证每条记录
            all_verified = True
            for i, record_id in enumerate(import_result):
                try:
                    # 使用get_record获取记录，避免使用缓存中的对象
                    result = secure_db.get_record(record_id)

                    if result == test_records[i]:
                        logger.debug(f"特定记录 {record_id} 验证成功")
                    else:
                        logger.error(f"特定记录 {record_id} 验证失败，数据不匹配")
                        all_verified = False
                except Exception as e:
                    logger.error(f"验证记录 {record_id} 时出错: {e}")
                    all_verified = False

            if not all_verified:
                success = False

            # 删除导入的记录
            secure_db.delete_records_batch(import_result)
        else:
            logger.error(
                f"导入特定记录失败，预期 {len(record_ids)} 条，实际导入 {len(import_result) if import_result else 0} 条"
            )
            success = False

        if success:
            logger.info("特定记录导入测试通过")
        else:
            logger.error("特定记录导入测试失败")

        return success

    except Exception as e:
        logger.error(f"特定记录导入测试出现异常: {e}")
        return False


def test_export_all_records():
    """测试所有记录的导出功能"""
    logger.info("开始测试所有记录的导出功能...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 生成测试记录
        test_records = []
        record_ids = []

        logger.info("生成测试记录...")
        for _ in range(10):
            customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
            data = generate_privacy_test_data(customer_id)
            record_id = secure_db.add_record(customer_id, data, enable_range_query=True)
            record_ids.append(record_id)
            test_records.append(data)

        # 导出所有数据
        export_file = TEST_DATA_CONFIG["export_file_all"]
        logger.info(f"导出所有记录到文件: {export_file}")

        export_count = secure_db.export_data(export_file, include_encrypted=False)
        if export_count >= len(record_ids):
            logger.info(f"成功导出 {export_count} 条记录")
        else:
            logger.error(
                f"导出所有记录失败, 至少应有 {len(record_ids)} 条, 实际导出 {export_count} 条"
            )
            success = False

        if success:
            logger.info("所有记录导出测试通过")
        else:
            logger.error("所有记录导出测试失败")

        return success, record_ids, test_records, export_file

    except Exception as e:
        logger.error(f"所有记录导出测试出现异常: {e}")
        return False, [], [], ""


def test_import_all_records(original_record_ids, test_records, export_file):
    """测试所有记录的导入功能"""
    logger.info("开始测试所有记录的导入功能...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 删除原记录
        logger.info("删除原始记录...")
        secure_db.delete_records_batch(original_record_ids)

        # 导入所有数据
        logger.info(f"从文件导入所有记录: {export_file}")
        import_count = secure_db.import_data(export_file, enable_range_query=True)

        if import_count >= len(original_record_ids):
            logger.info(f"成功导入 {import_count} 条记录")

            # 验证导入的数据 - 由于导入所有记录时可能有其他记录, 所以我们只验证我们知道的记录
            logger.info("验证部分导入记录...")

            # 搜索导入的记录 - 从测试记录中提取客户ID
            all_found = True
            for i, test_record in enumerate(test_records):
                try:
                    # 从测试记录中解析出客户ID
                    record_data = json.loads(test_record)
                    customer_id = int(record_data.get("index"))

                    # 通过索引值搜索记录
                    results = secure_db.search_by_index(customer_id)
                    if not results:
                        logger.error(f"未找到客户ID为 {customer_id} 的记录")
                        all_found = False
                        continue

                    # 验证数据内容
                    found = False
                    for result in results:
                        if result["data"] == test_record:
                            logger.debug(
                                f"记录 {result['id']} (客户ID: {customer_id}) 验证成功"
                            )
                            found = True
                            break

                    if not found:
                        logger.error(f"客户ID为 {customer_id} 的记录数据不匹配")
                        all_found = False
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.error(f"解析测试记录失败: {e}")
                    all_found = False

            if not all_found:
                success = False
        else:
            logger.error(
                f"导入所有记录失败, 至少应有 {len(original_record_ids)} 条, 实际导入 {import_count} 条"
            )
            success = False

        if success:
            logger.info("所有记录导入测试通过")
        else:
            logger.error("所有记录导入测试失败")

        return success

    except Exception as e:
        logger.error(f"所有记录导入测试出现异常: {e}")
        return False


def test_export_import():
    """测试数据导出和导入功能"""
    logger.info("开始综合测试数据导出和导入功能...")

    # 测试特定记录的导出
    (
        specific_export_success,
        specific_record_ids,
        specific_test_records,
        specific_export_file,
    ) = test_export_specific_records()

    # 确保导出文件存在
    if specific_export_success and os.path.exists(specific_export_file):
        # 测试特定记录的导入
        specific_import_success = test_import_specific_records(
            specific_record_ids, specific_test_records, specific_export_file
        )
    else:
        logger.error("特定记录导出失败或导出文件不存在, 跳过导入测试")
        specific_import_success = False

    # 测试所有记录的导出
    all_export_success, all_record_ids, all_test_records, all_export_file = (
        test_export_all_records()
    )

    # 确保导出文件存在
    if all_export_success and os.path.exists(all_export_file):
        # 测试所有记录的导入
        all_import_success = test_import_all_records(
            all_record_ids, all_test_records, all_export_file
        )
    else:
        logger.error("所有记录导出失败或导出文件不存在, 跳过导入测试")
        all_import_success = False

    # 综合结果
    if (
        specific_export_success
        and specific_import_success
        and all_export_success
        and all_import_success
    ):
        logger.info("所有数据导入导出测试全部通过")
        return True
    else:
        logger.error("部分数据导入导出测试失败")
        return False


if __name__ == "__main__":
    success = test_export_import()
    sys.exit(0 if success else 1)
