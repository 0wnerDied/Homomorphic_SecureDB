"""
主程序 - 同态加密安全数据库系统启动入口
"""

import logging
import argparse
import sys
import json

from core.secure_db import SecureDB

logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="基于同态加密的安全数据库系统")

    parser.add_argument("--genkeys", action="store_true", help="生成新密钥")
    parser.add_argument(
        "--encrypt-only",
        action="store_true",
        help="仅加密模式（只需要公钥）",
    )
    parser.add_argument("--add", action="store_true", help="添加新记录")
    parser.add_argument("--get", type=int, help="通过ID获取记录")
    parser.add_argument("--search", type=int, help="通过索引值搜索记录")
    parser.add_argument("--update", type=int, help="通过ID更新记录")
    parser.add_argument("--delete", type=int, help="通过ID删除记录")
    parser.add_argument("--cleanup", action="store_true", help="清理未使用的引用")
    parser.add_argument("--index", type=int, help="添加操作的索引值")
    parser.add_argument("--data", type=str, help="添加/更新操作的数据")

    parser.add_argument("--range", action="store_true", help="为添加操作启用范围查询")
    parser.add_argument("--min", type=int, help="范围搜索的最小值")
    parser.add_argument("--max", type=int, help="范围搜索的最大值")
    parser.add_argument("--batch", action="store_true", help="使用批量操作")
    parser.add_argument(
        "--ids",
        type=str,
        help="批量操作的记录ID列表，以逗号分隔",
    )
    parser.add_argument("--export", type=str, help="导出数据到JSON文件")
    parser.add_argument(
        "--import", dest="import_file", type=str, help="从JSON文件导入数据"
    )
    parser.add_argument(
        "--include-encrypted",
        action="store_true",
        help="在导出中包含加密数据",
    )

    # 缓存相关参数
    parser.add_argument(
        "--cache-size", type=int, help="设置自定义缓存大小（覆盖配置文件）"
    )
    parser.add_argument("--clear-cache", action="store_true", help="清除所有缓存")
    parser.add_argument("--cache-stats", action="store_true", help="显示缓存统计信息")

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    try:
        if args.genkeys:
            # 生成新密钥
            secure_db = SecureDB(
                load_keys=False, encrypt_only=False, cache_size=args.cache_size
            )
            print("新密钥生成成功")
            return

        # 初始化安全数据库系统
        secure_db = SecureDB(
            load_keys=True, encrypt_only=args.encrypt_only, cache_size=args.cache_size
        )

        # 处理缓存相关命令
        if args.clear_cache:
            secure_db.clear_caches()
            print("所有缓存已成功清除")
            return

        if args.cache_stats:
            stats = secure_db.get_cache_stats()
            print("缓存统计信息:")
            print(json.dumps(stats, indent=2))
            return

        if args.add:
            # 添加记录
            if args.index is None or args.data is None:
                print("错误: 添加操作需要 --index 和 --data 参数")
                return

            record_id = secure_db.add_record(args.index, args.data, args.range)
            print(f"已添加记录，ID: {record_id}")

        elif args.get is not None:
            # 获取记录
            if args.batch and args.ids:
                # 批量获取
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                results = secure_db.get_records_batch(record_ids)
                for record_id, data in results.items():
                    if data:
                        print(f"记录 {record_id}: {data}")
                    else:
                        print(f"记录 {record_id} 不存在")
            else:
                # 单条获取
                data = secure_db.get_record(args.get)
                if data:
                    print(f"记录 {args.get}: {data}")
                else:
                    print(f"记录 {args.get} 不存在")

        elif args.search is not None:
            # 搜索记录
            results = secure_db.search_by_index(args.search)
            if results:
                print(f"找到 {len(results)} 条匹配记录:")
                for result in results:
                    print(f"记录 {result['id']}: {result['data']}")
            else:
                print("未找到匹配记录")

        elif args.min is not None or args.max is not None:
            # 范围搜索
            results = secure_db.search_by_range(args.min, args.max)
            if results:
                print(f"在指定范围内找到 {len(results)} 条记录:")
                for result in results:
                    print(f"记录 {result['id']}: {result['data']}")
            else:
                print("在指定范围内未找到记录")

        elif args.update is not None:
            # 更新记录
            if args.data is None:
                print("错误: 更新操作需要 --data 参数")
                return

            if args.batch and args.ids:
                # 批量更新
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                updates = [(record_id, args.data) for record_id in record_ids]
                updated_count = secure_db.update_records_batch(updates)
                print(f"已更新 {updated_count} 条记录")
            else:
                # 单条更新
                success = secure_db.update_record(args.update, args.data)
                if success:
                    print(f"记录 {args.update} 更新成功")
                else:
                    print(f"记录 {args.update} 不存在")

        elif args.delete is not None:
            # 删除记录
            if args.batch and args.ids:
                # 批量删除
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                deleted_count = secure_db.delete_records_batch(record_ids)
                print(f"已删除 {deleted_count} 条记录")
            else:
                # 单条删除
                success = secure_db.delete_record(args.delete)
                if success:
                    print(f"记录 {args.delete} 删除成功")
                else:
                    print(f"记录 {args.delete} 不存在")

        elif args.cleanup:
            # 清理未使用的引用
            count = secure_db.cleanup_references()
            print(f"已清理 {count} 个未使用的引用")

        elif args.export:
            # 导出数据
            count = secure_db.export_data(args.export, args.include_encrypted)
            print(f"已导出 {count} 条记录到 {args.export}")

        elif args.import_file:
            # 导入数据
            count = secure_db.import_data(args.import_file, args.range)
            print(f"已从 {args.import_file} 导入 {count} 条记录")

        else:
            print("未指定操作。使用 --help 获取使用信息。")

    except Exception as e:
        print(f"错误: {e}")
        logger.exception("未处理的异常")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
