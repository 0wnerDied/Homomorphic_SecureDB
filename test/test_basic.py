"""
基本功能测试脚本 - 测试系统的基本CRUD操作
"""

import sys
import random
import logging
from test_config import PROJECT_ROOT, TEST_DATA_CONFIG

# 添加项目根目录到Python路径
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目模块
try:
    from core.secure_db import SecureDB
    from generate_test_data import generate_privacy_test_data
except ImportError as e:
    logger = logging.getLogger("基本功能测试")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确, 并且已安装所有依赖")
    sys.exit(1)

logger = logging.getLogger("基本功能测试")


def test_crud_operations():
    """测试基本的CRUD操作"""
    logger.info("开始测试基本CRUD操作...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 生成测试客户ID和数据
        customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
        test_data = generate_privacy_test_data(customer_id)

        # 测试添加记录
        logger.info(f"测试添加记录, 客户ID: {customer_id}")
        record_id = secure_db.add_record(
            customer_id, test_data, enable_range_query=True
        )
        logger.info(f"记录添加成功, ID: {record_id}")

        # 测试获取记录
        logger.info(f"测试获取记录, ID: {record_id}")
        retrieved_data = secure_db.get_record(record_id)
        if retrieved_data == test_data:
            logger.info("记录获取成功, 数据匹配")
        else:
            logger.error("记录获取失败, 数据不匹配")
            success = False

        # 测试更新记录
        updated_data = generate_privacy_test_data(customer_id)
        logger.info(f"测试更新记录, ID: {record_id}")
        update_success = secure_db.update_record(record_id, updated_data)

        if update_success:
            # 验证更新 - 需要重新获取记录，而不是使用缓存
            # 先清除缓存，确保获取最新数据
            secure_db.clear_caches()

            # 重新获取记录
            retrieved_data = secure_db.get_record(record_id)
            if retrieved_data == updated_data:
                logger.info("记录更新成功, 数据匹配")
            else:
                logger.error("记录更新失败, 数据不匹配")
                success = False
        else:
            logger.error("记录更新操作失败")
            success = False

        # 测试按索引搜索
        logger.info(f"测试按索引搜索, 客户ID: {customer_id}")
        search_results = secure_db.search_by_index(customer_id)
        if search_results and any(
            result["id"] == record_id for result in search_results
        ):
            logger.info(f"索引搜索成功, 找到 {len(search_results)} 条记录")
        else:
            logger.error("索引搜索失败, 未找到预期记录")
            success = False

        # 测试删除记录
        logger.info(f"测试删除记录, ID: {record_id}")
        delete_success = secure_db.delete_record(record_id)

        if delete_success:
            # 验证删除 - 清除缓存确保获取最新状态
            secure_db.clear_caches()

            # 尝试获取已删除的记录
            deleted_data = secure_db.get_record(record_id)
            if deleted_data is None:
                logger.info("记录删除成功")
            else:
                logger.error("记录删除失败, 仍能获取到记录")
                success = False
        else:
            logger.error("记录删除操作失败")
            success = False

        return success

    except Exception as e:
        logger.error(f"CRUD测试出现异常: {e}")
        return False


if __name__ == "__main__":
    success = test_crud_operations()
    sys.exit(0 if success else 1)
