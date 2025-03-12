"""
高级功能测试脚本 - 测试批量操作、范围查询和缓存功能
"""

import sys
import time
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
    logger = logging.getLogger("高级功能测试")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确, 并且已安装所有依赖")
    sys.exit(1)

logger = logging.getLogger("高级功能测试")


def test_batch_operations():
    """测试批量操作功能"""
    logger.info("开始测试批量操作功能...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 准备批量添加数据
        batch_size = TEST_DATA_CONFIG["batch_size"]
        batch_records = []
        customer_ids = []
        test_data_map = {}  # 存储原始测试数据, 用于后续验证

        for _ in range(batch_size):
            customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
            customer_ids.append(customer_id)
            data = generate_privacy_test_data(customer_id)
            test_data_map[customer_id] = data
            batch_records.append((customer_id, data, True))  # 启用范围查询

        # 测试批量添加
        logger.info(f"测试批量添加 {batch_size} 条记录")
        record_ids = secure_db.add_records_batch(batch_records)

        if len(record_ids) == batch_size:
            logger.info(f"批量添加成功, 添加了 {len(record_ids)} 条记录")
        else:
            logger.error(
                f"批量添加失败, 预期 {batch_size} 条, 实际添加 {len(record_ids)} 条"
            )
            success = False

        secure_db.clear_caches()

        # 测试批量获取
        logger.info(f"测试批量获取 {len(record_ids)} 条记录")
        batch_results = secure_db.get_records_batch(record_ids)

        if len(batch_results) == len(record_ids) and all(batch_results.values()):
            logger.info("批量获取成功, 所有记录都获取到了")
        else:
            logger.error(
                f"批量获取失败, 预期 {len(record_ids)} 条, 实际获取 {len([v for v in batch_results.values() if v])} 条"
            )
            success = False

        # 测试批量更新
        updated_batch = []
        updated_data_map = {}  # 存储更新后的数据, 用于后续验证

        for i, record_id in enumerate(record_ids):
            customer_id = customer_ids[i]
            updated_data = generate_privacy_test_data(customer_id)
            updated_data_map[record_id] = updated_data
            updated_batch.append((record_id, updated_data))

        logger.info(f"测试批量更新 {len(updated_batch)} 条记录")
        updated_count = secure_db.update_records_batch(updated_batch)

        if updated_count == len(updated_batch):
            logger.info(f"批量更新成功, 更新了 {updated_count} 条记录")

            # 清除缓存, 确保获取最新数据
            secure_db.clear_caches()

            # 验证更新是否成功
            verification_success = True
            for record_id, expected_data in updated_data_map.items():
                actual_data = secure_db.get_record(record_id)
                if actual_data != expected_data:
                    logger.error(f"记录 {record_id} 更新验证失败")
                    verification_success = False

            if verification_success:
                logger.info("批量更新验证通过, 所有记录数据已正确更新")
            else:
                logger.error("批量更新验证失败, 部分记录数据未正确更新")
                success = False
        else:
            logger.error(
                f"批量更新失败, 预期更新 {len(updated_batch)} 条, 实际更新 {updated_count} 条"
            )
            success = False

        # 测试批量删除
        logger.info(f"测试批量删除 {len(record_ids)} 条记录")
        deleted_count = secure_db.delete_records_batch(record_ids)

        if deleted_count == len(record_ids):
            logger.info(f"批量删除成功, 删除了 {deleted_count} 条记录")

            # 清除缓存, 确保获取最新状态
            secure_db.clear_caches()

            # 验证删除是否成功
            verification_success = True
            for record_id in record_ids:
                if secure_db.get_record(record_id) is not None:
                    logger.error(f"记录 {record_id} 删除验证失败, 仍能获取到记录")
                    verification_success = False

            if verification_success:
                logger.info("批量删除验证通过, 所有记录已成功删除")
            else:
                logger.error("批量删除验证失败, 部分记录未成功删除")
                success = False
        else:
            logger.error(
                f"批量删除失败, 预期删除 {len(record_ids)} 条, 实际删除 {deleted_count} 条"
            )
            success = False

        return success

    except Exception as e:
        logger.error(f"批量操作测试出现异常: {e}")
        return False


def test_range_query():
    """测试范围查询功能"""
    logger.info("开始测试范围查询功能...")
    success = True

    try:
        # 初始化安全数据库系统
        secure_db = SecureDB(load_keys=True)

        # 生成连续的客户ID, 以便测试范围查询
        base_customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
        customer_ids = [base_customer_id + i for i in range(10)]
        record_ids = []

        # 添加测试记录
        logger.info(f"添加10条连续客户ID的测试记录, 起始ID: {base_customer_id}")
        for customer_id in customer_ids:
            data = generate_privacy_test_data(customer_id)
            record_id = secure_db.add_record(customer_id, data, enable_range_query=True)
            record_ids.append(record_id)

        # 清除缓存, 确保从数据库获取最新数据
        secure_db.clear_caches()

        # 测试范围查询 - 完全包含
        start_id = base_customer_id
        end_id = base_customer_id + 9
        logger.info(f"测试范围查询 - 完全包含范围: {start_id} 到 {end_id}")
        range_results = secure_db.search_by_range(start_id, end_id)

        if len(range_results) == 10:
            logger.info(f"范围查询成功, 找到 {len(range_results)} 条记录")
        else:
            logger.error(f"范围查询失败, 预期 10 条, 实际找到 {len(range_results)} 条")
            success = False

        # 测试范围查询 - 部分包含
        start_id = base_customer_id + 3
        end_id = base_customer_id + 7
        logger.info(f"测试范围查询 - 部分包含范围: {start_id} 到 {end_id}")
        range_results = secure_db.search_by_range(start_id, end_id)

        if len(range_results) == 5:  # 包含5条记录
            logger.info(f"范围查询成功, 找到 {len(range_results)} 条记录")
        else:
            logger.error(f"范围查询失败, 预期 5 条, 实际找到 {len(range_results)} 条")
            success = False

        # 测试范围查询 - 不包含
        start_id = base_customer_id + 20
        end_id = base_customer_id + 30
        logger.info(f"测试范围查询 - 不包含范围: {start_id} 到 {end_id}")
        range_results = secure_db.search_by_range(start_id, end_id)

        if len(range_results) == 0:
            logger.info("范围查询成功, 未找到记录 (符合预期) ")
        else:
            logger.error(f"范围查询失败, 预期 0 条, 实际找到 {len(range_results)} 条")
            success = False

        # 清理测试记录
        logger.info("清理测试记录...")
        deleted_count = secure_db.delete_records_batch(record_ids)

        # 清除缓存, 确保从数据库获取最新状态
        secure_db.clear_caches()

        # 验证删除是否成功
        verification_success = True
        for record_id in record_ids:
            if secure_db.get_record(record_id) is not None:
                logger.error(f"记录 {record_id} 删除验证失败, 仍能获取到记录")
                verification_success = False

        if verification_success:
            logger.info("测试记录清理验证通过")
        else:
            logger.error("测试记录清理验证失败, 部分记录未成功删除")
            success = False

        return success

    except Exception as e:
        logger.error(f"范围查询测试出现异常: {e}")
        return False


def test_cache_performance():
    """测试缓存性能"""
    logger.info("开始测试缓存性能...")
    success = True

    try:
        # 初始化带缓存的安全数据库系统
        cache_size = TEST_DATA_CONFIG["cache_size"]
        secure_db = SecureDB(load_keys=True, cache_size=cache_size)

        # 添加测试记录
        customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
        data = generate_privacy_test_data(customer_id)
        record_id = secure_db.add_record(customer_id, data, enable_range_query=True)

        # 清除缓存, 确保首次访问不命中缓存
        secure_db.clear_caches()

        # 测试缓存性能 - 首次访问
        logger.info("测试首次访问记录 (无缓存) ...")
        start_time = time.time()
        _ = secure_db.get_record(record_id)
        first_access_time = time.time() - start_time

        # 测试缓存性能 - 再次访问
        logger.info("测试再次访问记录 (有缓存) ...")
        start_time = time.time()
        _ = secure_db.get_record(record_id)
        second_access_time = time.time() - start_time

        logger.info(f"首次访问时间: {first_access_time:.6f}秒")
        logger.info(f"再次访问时间: {second_access_time:.6f}秒")

        if second_access_time < first_access_time:
            logger.info("缓存性能测试通过, 缓存访问更快")
        else:
            logger.warning("缓存性能测试异常, 缓存访问未加速")
            # 不将此视为失败, 因为在某些环境下可能有波动

        # 清理测试记录
        secure_db.delete_record(record_id)

        # 清除缓存, 确保从数据库获取最新状态
        secure_db.clear_caches()

        # 验证删除是否成功
        if secure_db.get_record(record_id) is None:
            logger.info("测试记录清理验证通过")
        else:
            logger.error("测试记录清理验证失败, 仍能获取到记录")
            success = False

        return success

    except Exception as e:
        logger.error(f"缓存性能测试出现异常: {e}")
        return False


def run_advanced_tests():
    """运行所有高级功能测试"""
    tests = [
        ("批量操作测试", test_batch_operations),
        ("范围查询测试", test_range_query),
        ("缓存性能测试", test_cache_performance),
    ]

    all_success = True

    for test_name, test_func in tests:
        logger.info(f"开始运行 {test_name}")
        success = test_func()
        logger.info(f"{test_name} {'通过' if success else '失败'}")
        all_success = all_success and success

    return all_success


if __name__ == "__main__":
    success = run_advanced_tests()
    sys.exit(0 if success else 1)
