"""
主程序 - 同态加密安全数据库系统启动入口
"""

import logging
import argparse
import sys
import json
import time

from core.secure_db import SecureDB


# 设置日志系统
def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("secure_db.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# 全局日志对象
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="基于同态加密的安全数据库系统")

    # 创建互斥操作组
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument("--genkeys", action="store_true", help="生成新密钥")
    operation_group.add_argument("--add", action="store_true", help="添加新记录")
    operation_group.add_argument("--get", type=int, help="通过ID获取记录")
    operation_group.add_argument("--search", type=int, help="通过索引值搜索记录")
    operation_group.add_argument("--update", type=int, help="通过ID更新记录")
    operation_group.add_argument("--delete", type=int, help="通过ID删除记录")
    operation_group.add_argument(
        "--cleanup", action="store_true", help="清理未使用的引用"
    )
    operation_group.add_argument(
        "--clear-cache", action="store_true", help="清除所有缓存"
    )
    operation_group.add_argument(
        "--cache-stats", action="store_true", help="显示缓存统计信息"
    )
    operation_group.add_argument(
        "--range-search", action="store_true", help="执行范围搜索"
    )
    operation_group.add_argument(
        "--export-data", action="store_true", help="导出数据到JSON文件"
    )
    operation_group.add_argument(
        "--import-data", action="store_true", help="从JSON文件导入数据"
    )
    operation_group.add_argument(
        "--export-records", action="store_true", help="导出特定记录"
    )
    operation_group.add_argument(
        "--import-records", action="store_true", help="导入特定记录"
    )

    # 索引操作
    operation_group.add_argument(
        "--update-by-index", type=int, help="通过索引值更新记录"
    )
    operation_group.add_argument(
        "--delete-by-index", type=int, help="通过索引值删除记录"
    )
    operation_group.add_argument(
        "--update-by-range", action="store_true", help="通过索引范围更新记录"
    )
    operation_group.add_argument(
        "--delete-by-range", action="store_true", help="通过索引范围删除记录"
    )

    # 核心操作参数组
    core_group = parser.add_argument_group("核心操作")
    core_group.add_argument(
        "--encrypt-only",
        action="store_true",
        help="仅加密模式 (只需要公钥) ",
    )

    # 数据参数组
    data_group = parser.add_argument_group("数据参数")
    data_group.add_argument("--index", type=int, help="添加操作的索引值")
    data_group.add_argument("--data", type=str, help="添加/更新操作的数据")
    data_group.add_argument(
        "--range", action="store_true", help="为添加操作启用范围查询"
    )
    data_group.add_argument("--min", type=int, help="范围操作的最小值")
    data_group.add_argument("--max", type=int, help="范围操作的最大值")

    # 批量操作参数组
    batch_group = parser.add_argument_group("批量操作")
    batch_group.add_argument("--batch", action="store_true", help="使用批量操作")
    batch_group.add_argument(
        "--ids",
        type=str,
        help="批量操作的记录ID列表, 以逗号分隔",
    )

    # 导入导出参数组
    io_group = parser.add_argument_group("导入导出")
    io_group.add_argument("--export", type=str, help="导出数据的文件路径")
    io_group.add_argument(
        "--import", dest="import_file", type=str, help="导入数据的文件路径"
    )
    io_group.add_argument(
        "--include-encrypted",
        action="store_true",
        help="在导出中包含加密数据",
    )

    # 缓存相关参数组
    cache_group = parser.add_argument_group("缓存管理")
    cache_group.add_argument(
        "--cache-size", type=int, help="设置自定义缓存大小 (覆盖配置文件) "
    )

    return parser.parse_args()


def validate_args(args):
    """验证命令行参数的有效性和互斥性"""
    # 检查添加操作所需参数
    if args.add and (args.index is None or args.data is None):
        logger.error("添加操作需要 --index 和 --data 参数")
        return False

    # 检查更新操作所需参数
    if args.update is not None and args.data is None:
        logger.error("更新操作需要 --data 参数")
        return False

    # 检查通过索引更新操作所需参数
    if args.update_by_index is not None and args.data is None:
        logger.error("通过索引更新操作需要 --data 参数")
        return False

    # 检查通过范围更新操作所需参数
    if args.update_by_range and args.data is None:
        logger.error("通过范围更新操作需要 --data 参数")
        return False

    # 检查范围操作所需参数
    if (args.range_search or args.update_by_range or args.delete_by_range) and (
        args.min is None and args.max is None
    ):
        logger.error("范围操作需要至少一个范围参数 (--min 或 --max)")
        return False

    # 检查范围查询参数
    if args.min is not None and args.max is None:
        logger.warning("未指定最大值，将使用系统最大整数")
    elif args.min is None and args.max is not None:
        logger.warning("未指定最小值，将使用0")

    # 检查批量操作参数
    if (
        args.batch
        and (args.ids is None)
        and (args.get is not None or args.update is not None or args.delete is not None)
    ):
        logger.error("批量操作需要 --ids 参数")
        return False

    # 检查导出特定记录参数
    if args.export_records and (args.ids is None or args.export is None):
        logger.error("导出特定记录需要 --ids 和 --export 参数")
        return False

    # 检查导入特定记录参数
    if args.import_records and args.import_file is None:
        logger.error("导入特定记录需要 --import 参数")
        return False

    # 检查导出数据参数
    if args.export_data and args.export is None:
        logger.error("导出数据需要 --export 参数")
        return False

    # 检查导入数据参数
    if args.import_data and args.import_file is None:
        logger.error("导入数据需要 --import 参数")
        return False

    return True


def handle_key_operations(args):
    """处理密钥相关操作"""
    if args.genkeys:
        try:
            secure_db = SecureDB(
                load_keys=False, encrypt_only=False, cache_size=args.cache_size
            )
            logger.info("新密钥生成成功")
            print("新密钥生成成功")
            return True
        except Exception as e:
            logger.exception("生成密钥时发生错误")
            print(f"生成密钥失败: {e}")
            return False
    return None


def handle_cache_operations(secure_db, args):
    """处理缓存相关操作"""
    if args.clear_cache:
        try:
            secure_db.clear_caches()
            logger.info("所有缓存已清除")
            print("所有缓存已成功清除")
            return True
        except Exception as e:
            logger.exception("清除缓存时发生错误")
            print(f"清除缓存失败: {e}")
            return False

    if args.cache_stats:
        try:
            stats = secure_db.get_cache_stats()
            print("缓存统计信息:")
            print(json.dumps(stats, indent=2))
            logger.info("已显示缓存统计信息")
            return True
        except Exception as e:
            logger.exception("获取缓存统计信息时发生错误")
            print(f"获取缓存统计信息失败: {e}")
            return False

    return None


def handle_record_operations(secure_db, args):
    """处理记录相关操作"""
    try:
        if args.add:
            # 添加记录
            record_id = secure_db.add_record(args.index, args.data, args.range)
            logger.info(f"已添加记录, ID: {record_id}")
            print(f"已添加记录, ID: {record_id}")
            return True

        elif args.get is not None:
            # 获取记录
            if args.batch and args.ids:
                # 批量获取
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                logger.info(f"批量获取记录, IDs: {record_ids}")
                results = secure_db.get_records_batch(record_ids)
                for record_id, data in results.items():
                    if data:
                        print(f"记录 {record_id}: {data}")
                    else:
                        print(f"记录 {record_id} 不存在")
                return True
            else:
                # 单条获取
                logger.info(f"获取记录, ID: {args.get}")
                data = secure_db.get_record(args.get)
                if data:
                    print(f"记录 {args.get}: {data}")
                else:
                    print(f"记录 {args.get} 不存在")
                return True

        elif args.search is not None:
            # 搜索记录
            logger.info(f"按索引搜索记录, 索引值: {args.search}")
            results = secure_db.search_by_index(args.search)
            if results:
                print(f"找到 {len(results)} 条匹配记录:")
                for result in results:
                    print(f"记录 {result['id']}: {result['data']}")
            else:
                print("未找到匹配记录")
            return True

        elif args.range_search:
            # 范围搜索
            min_val = args.min if args.min is not None else 0
            max_val = args.max if args.max is not None else sys.maxsize
            logger.info(f"范围搜索记录, 范围: [{min_val}, {max_val}]")
            results = secure_db.search_by_range(min_val, max_val)
            if results:
                print(f"在指定范围内找到 {len(results)} 条记录:")
                for result in results:
                    print(f"记录 {result['id']}: {result['data']}")
            else:
                print("在指定范围内未找到记录")
            return True

        elif args.update is not None:
            # 更新记录
            if args.batch and args.ids:
                # 批量更新
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                updates = [(record_id, args.data) for record_id in record_ids]
                logger.info(f"批量更新记录, IDs: {record_ids}")
                updated_count = secure_db.update_records_batch(updates)
                print(f"已更新 {updated_count} 条记录")
                return True
            else:
                # 单条更新
                logger.info(f"更新记录, ID: {args.update}")
                success = secure_db.update_record(args.update, args.data)
                if success:
                    print(f"记录 {args.update} 更新成功")
                else:
                    print(f"记录 {args.update} 不存在")
                return True

        elif args.delete is not None:
            # 删除记录
            if args.batch and args.ids:
                # 批量删除
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                logger.info(f"批量删除记录, IDs: {record_ids}")
                deleted_count = secure_db.delete_records_batch(record_ids)
                print(f"已删除 {deleted_count} 条记录")
                return True
            else:
                # 单条删除
                logger.info(f"删除记录, ID: {args.delete}")
                success = secure_db.delete_record(args.delete)
                if success:
                    print(f"记录 {args.delete} 删除成功")
                else:
                    print(f"记录 {args.delete} 不存在")
                return True

        elif args.cleanup:
            # 清理未使用的引用
            logger.info("清理未使用的引用")
            count = secure_db.cleanup_references()
            print(f"已清理 {count} 个未使用的引用")
            return True

    except Exception as e:
        logger.exception("处理记录操作时发生错误")
        print(f"操作失败: {e}")
        return False

    return None


def handle_index_operations(secure_db, args):
    """处理索引相关操作"""
    try:
        if args.update_by_index is not None:
            # 通过索引更新记录
            logger.info(f"通过索引更新记录, 索引值: {args.update_by_index}")
            updated_count = secure_db.update_by_index(args.update_by_index, args.data)
            if updated_count > 0:
                print(
                    f"已通过索引值 {args.update_by_index} 更新 {updated_count} 条记录"
                )
            else:
                print(f"未找到索引值为 {args.update_by_index} 的记录")
            return True

        elif args.delete_by_index is not None:
            # 通过索引删除记录
            logger.info(f"通过索引删除记录, 索引值: {args.delete_by_index}")
            deleted_count = secure_db.delete_by_index(args.delete_by_index)
            if deleted_count > 0:
                print(
                    f"已通过索引值 {args.delete_by_index} 删除 {deleted_count} 条记录"
                )
            else:
                print(f"未找到索引值为 {args.delete_by_index} 的记录")
            return True

        elif args.update_by_range:
            # 通过范围更新记录
            min_val = args.min if args.min is not None else 0
            max_val = args.max if args.max is not None else sys.maxsize
            range_str = f"[{min_val}, {max_val}]"
            logger.info(f"通过范围更新记录, 范围: {range_str}")
            updated_count = secure_db.update_by_range(args.data, min_val, max_val)
            if updated_count > 0:
                print(f"已在范围 {range_str} 内更新 {updated_count} 条记录")
            else:
                print(f"在范围 {range_str} 内未找到记录")
            return True

        elif args.delete_by_range:
            # 通过范围删除记录
            min_val = args.min if args.min is not None else 0
            max_val = args.max if args.max is not None else sys.maxsize
            range_str = f"[{min_val}, {max_val}]"
            logger.info(f"通过范围删除记录, 范围: {range_str}")
            deleted_count = secure_db.delete_by_range(min_val, max_val)
            if deleted_count > 0:
                print(f"已在范围 {range_str} 内删除 {deleted_count} 条记录")
            else:
                print(f"在范围 {range_str} 内未找到记录")
            return True

    except Exception as e:
        logger.exception("处理索引操作时发生错误")
        print(f"操作失败: {e}")
        return False

    return None


def handle_import_export(secure_db, args):
    """处理导入导出操作"""
    try:
        if args.export_records:
            # 导出特定记录
            record_ids = [int(id_str) for id_str in args.ids.split(",")]
            logger.info(f"导出特定记录, IDs: {record_ids}, 文件: {args.export}")

            print(f"正在导出特定记录到 {args.export}...")
            start_time = time.time()
            count = secure_db.export_records(record_ids, args.export)
            elapsed = time.time() - start_time

            print(f"已导出 {count} 条特定记录到 {args.export} (耗时: {elapsed:.2f}秒)")
            return True

        elif args.import_records:
            # 导入特定记录
            logger.info(f"导入特定记录, 文件: {args.import_file}")

            print(f"正在从 {args.import_file} 导入特定记录...")
            start_time = time.time()
            record_ids = secure_db.import_records(args.import_file)
            elapsed = time.time() - start_time

            print(
                f"已从 {args.import_file} 导入 {len(record_ids)} 条特定记录 (耗时: {elapsed:.2f}秒)"
            )
            return True

        elif args.export_data:
            # 导出所有数据
            logger.info(
                f"导出所有数据, 文件: {args.export}, 包含加密数据: {args.include_encrypted}"
            )

            print(f"正在导出数据到 {args.export}...")
            start_time = time.time()
            count = secure_db.export_data(args.export, args.include_encrypted)
            elapsed = time.time() - start_time

            print(f"已导出 {count} 条记录到 {args.export} (耗时: {elapsed:.2f}秒)")
            return True

        elif args.import_data:
            # 导入数据
            logger.info(
                f"导入数据, 文件: {args.import_file}, 启用范围查询: {args.range}"
            )

            print(f"正在从 {args.import_file} 导入数据...")
            start_time = time.time()

            # 首先计算总记录数以显示进度
            try:
                with open(args.import_file, "r") as f:
                    data = json.load(f)
                    total_records = len(data.get("records", []))
                    print(f"文件包含 {total_records} 条记录")
            except:
                total_records = None
                print("无法预先确定记录数量")

            # 执行导入
            count = secure_db.import_data(args.import_file, args.range)
            elapsed = time.time() - start_time

            print(
                f"已从 {args.import_file} 导入 {count} 条记录 (耗时: {elapsed:.2f}秒)"
            )
            return True

    except Exception as e:
        logger.exception("处理导入导出操作时发生错误")
        print(f"导入/导出操作失败: {e}")
        return False

    return None


def main():
    """主函数"""
    # 设置日志系统
    setup_logging()

    # 解析命令行参数
    args = parse_args()

    # 验证参数
    if not validate_args(args):
        return 1

    # 处理密钥操作（不需要初始化完整的SecureDB）
    key_result = handle_key_operations(args)
    if key_result is not None:
        return 0 if key_result else 1

    try:
        # 初始化安全数据库系统
        logger.info(f"初始化安全数据库系统 (仅加密模式: {args.encrypt_only})")
        secure_db = SecureDB(
            load_keys=True, encrypt_only=args.encrypt_only, cache_size=args.cache_size
        )

        # 处理缓存操作
        cache_result = handle_cache_operations(secure_db, args)
        if cache_result is not None:
            return 0 if cache_result else 1

        # 处理索引操作
        index_result = handle_index_operations(secure_db, args)
        if index_result is not None:
            return 0 if index_result else 1

        # 处理记录操作
        record_result = handle_record_operations(secure_db, args)
        if record_result is not None:
            return 0 if record_result else 1

        # 处理导入导出操作
        import_export_result = handle_import_export(secure_db, args)
        if import_export_result is not None:
            return 0 if import_export_result else 1

        # 如果没有处理任何操作 - 不应该到达这里，因为我们使用了required=True的互斥组
        logger.warning("未执行任何操作，但参数解析通过。这可能是一个逻辑错误。")
        print("未执行任何操作。使用 --help 获取使用信息。")
        return 1

    except ValueError as e:
        logger.exception("参数错误")
        print(f"参数错误: {e}")
        return 1
    except FileNotFoundError as e:
        logger.exception("文件未找到")
        print(f"文件未找到: {e}")
        return 1
    except PermissionError as e:
        logger.exception("权限错误")
        print(f"权限错误: {e}")
        return 1
    except json.JSONDecodeError as e:
        logger.exception("JSON解析错误")
        print(f"JSON解析错误: {e}")
        return 1
    except Exception as e:
        logger.exception("未处理的异常")
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
