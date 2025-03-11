"""
完整测试运行脚本 - 按顺序运行所有测试
"""

import os
import sys
import logging
import subprocess
import time
from datetime import datetime
from test_config import PROJECT_ROOT

logger = logging.getLogger("测试运行")


def run_script(script_name, description):
    """运行指定的测试脚本"""
    logger.info(f"开始运行 {description}...")

    script_path = os.path.join(PROJECT_ROOT, "test", script_name)
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        elapsed = time.time() - start_time
        success = result.returncode == 0

        if success:
            logger.info(f"{description} 运行成功, 耗时: {elapsed:.2f}秒")
        else:
            logger.error(f"{description} 运行失败, 耗时: {elapsed:.2f}秒")
            logger.error(f"错误输出: {result.stderr}")

        return success, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"{description} 运行异常: {e}, 耗时: {elapsed:.2f}秒")
        return False, elapsed


def run_all_tests():
    """按顺序运行所有测试"""
    logger.info("开始运行完整测试套件...")

    test_start_time = time.time()
    test_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 测试脚本及其描述
    test_scripts = [
        ("setup_test_env.py", "测试环境设置"),
        ("init_test_db.py", "测试数据库初始化"),
        ("generate_test_keys.py", "测试密钥生成"),
        ("generate_test_data.py", "测试数据生成"),
        ("test_basic.py", "基本功能测试"),
        ("test_advanced.py", "高级功能测试"),
        ("test_performance.py", "性能测试"),
        ("cleanup_test_env.py", "测试环境清理"),
    ]

    results = {}
    all_success = True

    for script, description in test_scripts:
        success, elapsed = run_script(script, description)
        results[description] = {"success": success, "elapsed": elapsed}
        all_success = all_success and success

        # 如果关键步骤失败, 则中止后续测试
        if not success and script in [
            "setup_test_env.py",
            "init_test_db.py",
            "generate_test_keys.py",
        ]:
            logger.error(f"{description} 失败, 中止后续测试")
            break

    # 计算总耗时
    total_elapsed = time.time() - test_start_time

    # 生成测试报告
    report = {
        "test_date": test_date,
        "total_elapsed": total_elapsed,
        "all_success": all_success,
        "results": results,
    }

    # 保存测试报告
    report_file = os.path.join(PROJECT_ROOT, "test", "test_report.txt")
    with open(report_file, "w") as f:
        f.write(f"SecureDB 测试报告\n")
        f.write(f"测试日期: {test_date}\n")
        f.write(f"总耗时: {total_elapsed:.2f}秒\n")
        f.write(f"测试结果: {'全部通过' if all_success else '部分失败'}\n\n")

        f.write("详细测试结果:\n")
        for description, result in results.items():
            status = "通过" if result["success"] else "失败"
            f.write(f"- {description}: {status}, 耗时: {result['elapsed']:.2f}秒\n")

    logger.info(f"测试报告已保存: {report_file}")

    if all_success:
        logger.info("所有测试全部通过!")
    else:
        logger.warning("部分测试失败, 请查看测试报告和日志获取详细信息")

    return all_success


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
