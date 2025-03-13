"""
性能测试脚本 - 测试系统在不同负载下的性能
"""

import os
import sys
import json
import time
import random
import logging
import statistics
from test_config import PROJECT_ROOT, TEST_DATA_CONFIG

# 添加项目根目录到Python路径
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目模块
try:
    from core.secure_db import SecureDB
    from generate_test_data import generate_privacy_test_data
except ImportError as e:
    logger = logging.getLogger("性能测试")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确, 并且已安装所有依赖")
    sys.exit(1)

logger = logging.getLogger("性能测试")


class PerformanceTester:
    """性能测试类"""

    def __init__(self):
        """初始化性能测试器"""
        self.secure_db = SecureDB(
            load_keys=True, cache_size=TEST_DATA_CONFIG["cache_size"]
        )
        self.record_ids = []
        self.customer_ids = []

    def setup_test_data(self, count=20):
        """设置测试数据"""
        logger.info(f"创建 {count} 条测试记录...")

        for _ in range(count):
            customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
            self.customer_ids.append(customer_id)
            data = generate_privacy_test_data(customer_id)
            record_id = self.secure_db.add_record(
                customer_id, data, enable_range_query=True
            )
            self.record_ids.append(record_id)

        logger.info(f"成功创建 {len(self.record_ids)} 条测试记录")

    def cleanup_test_data(self):
        """清理测试数据"""
        if self.record_ids:
            logger.info(f"清理 {len(self.record_ids)} 条测试记录...")
            self.secure_db.delete_records_batch(self.record_ids)
            self.record_ids = []
            self.customer_ids = []
            logger.info("测试记录清理完成")

    def test_add_performance(self, count=50, batch_size=10):
        """测试添加记录的性能"""
        logger.info(f"测试添加记录性能 - {count} 条记录, 批量大小 {batch_size}")

        times = []
        for i in range(0, count, batch_size):
            batch = []
            batch_count = min(batch_size, count - i)

            for _ in range(batch_count):
                customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
                data = generate_privacy_test_data(customer_id)
                batch.append((customer_id, data, True))

            start_time = time.time()
            batch_ids = self.secure_db.add_records_batch(batch)
            elapsed = time.time() - start_time

            times.append(elapsed / batch_count)  # 每条记录的平均时间
            self.record_ids.extend(batch_ids)

        avg_time = statistics.mean(times)
        logger.info(f"添加记录平均耗时: {avg_time:.6f} 秒/条")

        return {
            "operation": "添加记录",
            "total_records": count,
            "batch_size": batch_size,
            "average_time_per_record": avg_time,
            "times": times,
        }

    def test_get_performance(self, iterations=100):
        """测试获取记录的性能"""
        if not self.record_ids:
            logger.error("没有测试记录, 无法测试获取性能")
            return None

        logger.info(f"测试获取记录性能 - {iterations} 次随机获取")

        times = []
        for _ in range(iterations):
            record_id = random.choice(self.record_ids)

            start_time = time.time()
            self.secure_db.get_record(record_id)
            elapsed = time.time() - start_time

            times.append(elapsed)

        avg_time = statistics.mean(times)
        logger.info(f"获取记录平均耗时: {avg_time:.6f} 秒/条")

        return {
            "operation": "获取记录",
            "iterations": iterations,
            "average_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "times": times,
        }

    def test_search_performance(self, iterations=20):
        """测试索引搜索的性能"""
        if not self.customer_ids:
            logger.error("没有测试客户ID, 无法测试搜索性能")
            return None

        logger.info(f"测试索引搜索性能 - {iterations} 次随机搜索")

        times = []
        for _ in range(iterations):
            customer_id = random.choice(self.customer_ids)

            start_time = time.time()
            results = self.secure_db.search_by_index(customer_id)
            elapsed = time.time() - start_time

            times.append(elapsed)
            logger.debug(
                f"搜索客户ID {customer_id} 找到 {len(results)} 条记录, 耗时: {elapsed:.6f} 秒"
            )

        avg_time = statistics.mean(times)
        logger.info(f"索引搜索平均耗时: {avg_time:.6f} 秒/次")

        return {
            "operation": "索引搜索",
            "iterations": iterations,
            "average_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "times": times,
        }

    def test_range_search_performance(self, iterations=10, range_width=100):
        """
        测试范围搜索的性能

        Args:
            iterations: 测试迭代次数
            range_width: 范围宽度 (上限与下限的差值)
        """
        if not self.customer_ids:
            logger.error("没有测试客户ID, 无法测试范围搜索性能")
            return None

        logger.info(
            f"测试范围搜索性能 - {iterations} 次范围搜索, 范围宽度 {range_width}"
        )

        # 对客户ID排序, 方便构建有效范围
        sorted_ids = sorted(self.customer_ids)

        times = []
        results_counts = []

        for _ in range(iterations):
            # 随机选择一个已存在的客户ID作为范围中点
            center_id = random.choice(sorted_ids)

            # 构建范围
            min_value = max(
                center_id - range_width // 2, TEST_DATA_CONFIG["index_range"][0]
            )
            max_value = min(
                center_id + range_width // 2, TEST_DATA_CONFIG["index_range"][1]
            )

            start_time = time.time()
            results = self.secure_db.search_by_range(min_value, max_value)
            elapsed = time.time() - start_time

            times.append(elapsed)
            results_counts.append(len(results))

            logger.debug(
                f"范围搜索 {min_value}-{max_value} 找到 {len(results)} 条记录, 耗时: {elapsed:.6f} 秒"
            )

        avg_time = statistics.mean(times)
        avg_results = statistics.mean(results_counts)
        logger.info(
            f"范围搜索平均耗时: {avg_time:.6f} 秒/次, 平均找到 {avg_results:.1f} 条记录"
        )

        return {
            "operation": "范围搜索",
            "iterations": iterations,
            "range_width": range_width,
            "average_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "average_results_count": avg_results,
            "times": times,
        }

    def test_update_performance(self, iterations=20):
        """测试更新记录的性能"""
        if not self.record_ids:
            logger.error("没有测试记录, 无法测试更新性能")
            return None

        logger.info(f"测试更新记录性能 - {iterations} 次随机更新")

        times = []
        for _ in range(iterations):
            record_id = random.choice(self.record_ids)
            idx = self.record_ids.index(record_id)
            customer_id = self.customer_ids[idx]

            updated_data = generate_privacy_test_data(customer_id)

            start_time = time.time()
            self.secure_db.update_record(record_id, updated_data)
            elapsed = time.time() - start_time

            times.append(elapsed)

        avg_time = statistics.mean(times)
        logger.info(f"更新记录平均耗时: {avg_time:.6f} 秒/条")

        return {
            "operation": "更新记录",
            "iterations": iterations,
            "average_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "times": times,
        }

    def test_delete_performance(self, count=20, batch_size=5):
        """测试删除记录的性能"""
        if not self.record_ids:
            logger.error("没有测试记录, 无法测试删除性能")
            return None

        # 只使用部分记录进行删除测试, 保留其他记录用于后续测试
        test_record_ids = self.record_ids[:count]
        self.record_ids = self.record_ids[count:]

        logger.info(
            f"测试删除记录性能 - {len(test_record_ids)} 条记录, 批量大小 {batch_size}"
        )

        times = []
        for i in range(0, len(test_record_ids), batch_size):
            batch = test_record_ids[i : i + batch_size]
            batch_count = len(batch)

            start_time = time.time()
            self.secure_db.delete_records_batch(batch)
            elapsed = time.time() - start_time

            times.append(elapsed / batch_count)  # 每条记录的平均时间

        avg_time = statistics.mean(times)
        logger.info(f"删除记录平均耗时: {avg_time:.6f} 秒/条")

        return {
            "operation": "删除记录",
            "total_records": len(test_record_ids),
            "batch_size": batch_size,
            "average_time_per_record": avg_time,
            "times": times,
        }

    def run_all_performance_tests(self):
        """运行所有性能测试"""
        logger.info("开始运行全面性能测试...")

        results = {}

        # 设置初始测试数据
        self.setup_test_data(count=30)

        # 测试获取记录性能
        results["get"] = self.test_get_performance(iterations=50)

        # 测试搜索性能
        results["search"] = self.test_search_performance(iterations=20)

        # 测试范围搜索性能
        results["range_search"] = self.test_range_search_performance(
            iterations=10, range_width=100
        )

        # 测试更新记录性能
        results["update"] = self.test_update_performance(iterations=20)

        # 测试删除记录性能
        results["delete"] = self.test_delete_performance(count=10, batch_size=2)

        # 测试添加记录性能
        results["add"] = self.test_add_performance(count=30, batch_size=5)

        # 清理测试数据
        self.cleanup_test_data()

        # 保存性能测试结果
        results_file = os.path.join(PROJECT_ROOT, "test", "performance_results.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"性能测试结果已保存: {results_file}")

        return results


def run_performance_tests():
    """运行性能测试"""
    try:
        tester = PerformanceTester()
        tester.run_all_performance_tests()
        return True
    except Exception as e:
        logger.error(f"性能测试出现异常: {e}")
        return False


if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)
