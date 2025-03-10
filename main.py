"""
主程序 - 同态加密数据库演示
"""

import logging
import argparse
import os
import sys
import getpass
import time
import json
from typing import Dict, Any, List, Optional, Tuple

# 导入项目模块
from config import DB_CONNECTION_STRING, ENCRYPTION_CONFIG, LOG_CONFIG, KEY_MANAGEMENT
from crypto.fhe import FHEManager
from crypto.aes import AESManager
from crypto.key_manager import KeyManager
from database.operations import DatabaseManager

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_CONFIG["log_file"]), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class SecureDB:
    """安全数据库演示类"""

    def __init__(self, load_keys: bool = False, encrypt_only: bool = False):
        """
        初始化演示

        Args:
            load_keys: 是否从文件加载密钥
            encrypt_only: 是否仅用于加密（不需要私钥）
        """
        # 确保密钥目录存在
        os.makedirs(KEY_MANAGEMENT["keys_dir"], exist_ok=True)

        # 初始化密钥管理器
        self.key_manager = KeyManager(KEY_MANAGEMENT["keys_dir"])

        # 初始化FHE管理器
        self.fhe_manager = FHEManager(
            ENCRYPTION_CONFIG["fhe"], self.key_manager, encrypt_only=encrypt_only
        )

        # 初始化数据库管理器
        self.db_manager = DatabaseManager(DB_CONNECTION_STRING)

        # 初始化AES管理器
        if load_keys:
            try:
                # 从文件加载AES密钥
                password = getpass.getpass("Enter password to decrypt AES key: ")
                aes_key = self.key_manager.load_aes_key(
                    KEY_MANAGEMENT["aes_key_file"], password
                )
                self.aes_manager = AESManager(key=aes_key)
                logger.info("AES key loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load AES key: {e}")
                # 如果加载失败，创建新的AES密钥
                logger.info("Creating new AES key")
                self.aes_manager = AESManager()
                self._save_aes_key()
        else:
            # 创建新的AES密钥
            self.aes_manager = AESManager()
            self._save_aes_key()

    def _save_aes_key(self):
        """保存AES密钥"""
        try:
            password = getpass.getpass("Enter password to encrypt AES key: ")
            confirm = getpass.getpass("Confirm password: ")

            if password != confirm:
                logger.error("Passwords do not match")
                return

            self.key_manager.save_aes_key(
                self.aes_manager.get_key(), KEY_MANAGEMENT["aes_key_file"], password
            )
            logger.info("AES key saved successfully")
        except Exception as e:
            logger.error(f"Failed to save AES key: {e}")

    def add_record(
        self, index_value: int, data: str, enable_range_query: bool = False
    ) -> int:
        """
        添加加密记录

        Args:
            index_value: 索引值
            data: 要加密的数据
            enable_range_query: 是否启用范围查询支持

        Returns:
            新记录的ID
        """
        try:
            start_time = time.time()

            # 加密索引
            encrypted_index = self.fhe_manager.encrypt_int(index_value)

            # 如果启用范围查询，创建范围查询索引
            range_query_bits = None
            if enable_range_query:
                range_query_bits = self.fhe_manager.encrypt_for_range_query(index_value)

            # 加密数据
            encrypted_data = self.aes_manager.encrypt(data)

            # 添加到数据库
            record_id = self.db_manager.add_encrypted_record(
                encrypted_index, encrypted_data, range_query_bits
            )

            elapsed = time.time() - start_time
            logger.info(f"Added record with ID {record_id} in {elapsed:.3f} seconds")

            return record_id
        except Exception as e:
            logger.error(f"Error adding record: {e}")
            raise

    def add_records_batch(self, records: List[Tuple[int, str, bool]]) -> List[int]:
        """
        批量添加加密记录

        Args:
            records: 记录列表，每个元素为(index_value, data, enable_range_query)元组

        Returns:
            新记录ID列表
        """
        try:
            start_time = time.time()

            # 准备批量加密数据
            encrypted_records = []

            for index_value, data, enable_range_query in records:
                # 加密索引
                encrypted_index = self.fhe_manager.encrypt_int(index_value)

                # 如果启用范围查询，创建范围查询索引
                range_query_bits = None
                if enable_range_query:
                    range_query_bits = self.fhe_manager.encrypt_for_range_query(
                        index_value
                    )

                # 加密数据
                encrypted_data = self.aes_manager.encrypt(data)

                # 添加到批处理列表
                encrypted_records.append(
                    (encrypted_index, encrypted_data, range_query_bits)
                )

            # 批量添加到数据库
            record_ids = self.db_manager.add_encrypted_records_batch(encrypted_records)

            elapsed = time.time() - start_time
            logger.info(
                f"Added {len(record_ids)} records in batch in {elapsed:.3f} seconds"
            )

            return record_ids
        except Exception as e:
            logger.error(f"Error adding records in batch: {e}")
            raise

    def get_record(self, record_id: int) -> Optional[str]:
        """
        获取并解密记录

        Args:
            record_id: 记录ID

        Returns:
            解密后的数据，如果记录不存在则返回None
        """
        try:
            start_time = time.time()

            # 获取记录
            record = self.db_manager.get_record_by_id(record_id)
            if not record:
                return None

            # 解密数据
            decrypted_data = self.aes_manager.decrypt(record.encrypted_data)

            elapsed = time.time() - start_time
            logger.info(
                f"Retrieved and decrypted record {record_id} in {elapsed:.3f} seconds"
            )

            return decrypted_data.decode("utf-8")
        except Exception as e:
            logger.error(f"Error retrieving record: {e}")
            raise

    def get_records_batch(self, record_ids: List[int]) -> Dict[int, Optional[str]]:
        """
        批量获取并解密记录

        Args:
            record_ids: 记录ID列表

        Returns:
            记录ID到解密数据的映射，如果记录不存在则值为None
        """
        try:
            start_time = time.time()

            # 获取记录
            records = self.db_manager.get_records_by_ids(record_ids)

            # 创建ID到记录的映射
            record_map = {record.id: record for record in records}

            # 解密数据
            result = {}
            for record_id in record_ids:
                if record_id in record_map:
                    decrypted_data = self.aes_manager.decrypt(
                        record_map[record_id].encrypted_data
                    )
                    result[record_id] = decrypted_data.decode("utf-8")
                else:
                    result[record_id] = None

            elapsed = time.time() - start_time
            logger.info(
                f"Retrieved and decrypted {len(records)} records in batch in {elapsed:.3f} seconds"
            )

            return result
        except Exception as e:
            logger.error(f"Error retrieving records in batch: {e}")
            raise

    def search_by_index(self, index_value: int) -> List[Dict[str, Any]]:
        """
        按索引值搜索记录

        Args:
            index_value: 要搜索的索引值

        Returns:
            匹配记录的列表，每个记录包含ID和解密后的数据
        """
        try:
            start_time = time.time()

            # 搜索记录
            records = self.db_manager.search_by_encrypted_index(
                self.fhe_manager, index_value
            )

            # 解密数据
            results = []
            for record in records:
                decrypted_data = self.aes_manager.decrypt(record.encrypted_data)
                results.append(
                    {"id": record.id, "data": decrypted_data.decode("utf-8")}
                )

            elapsed = time.time() - start_time
            logger.info(
                f"Searched for index {index_value} and found {len(results)} records in {elapsed:.3f} seconds"
            )

            return results
        except Exception as e:
            logger.error(f"Error searching records: {e}")
            raise

    def search_by_range(
        self, min_value: int = None, max_value: int = None
    ) -> List[Dict[str, Any]]:
        """
        按索引范围搜索记录

        Args:
            min_value: 范围最小值，如果为None则不检查下限
            max_value: 范围最大值，如果为None则不检查上限

        Returns:
            匹配记录的列表，每个记录包含ID和解密后的数据
        """
        try:
            start_time = time.time()

            # 搜索记录
            records = self.db_manager.search_by_range(
                self.fhe_manager, min_value, max_value
            )

            # 解密数据
            results = []
            for record in records:
                decrypted_data = self.aes_manager.decrypt(record.encrypted_data)
                results.append(
                    {"id": record.id, "data": decrypted_data.decode("utf-8")}
                )

            elapsed = time.time() - start_time
            range_str = f"[{min_value if min_value is not None else '*'}, {max_value if max_value is not None else '*'}]"
            logger.info(
                f"Searched for range {range_str} and found {len(results)} records in {elapsed:.3f} seconds"
            )

            return results
        except Exception as e:
            logger.error(f"Error searching records by range: {e}")
            raise

    def update_record(self, record_id: int, new_data: str) -> bool:
        """
        更新记录数据

        Args:
            record_id: 记录ID
            new_data: 新数据

        Returns:
            是否成功更新
        """
        try:
            start_time = time.time()

            # 加密新数据
            encrypted_data = self.aes_manager.encrypt(new_data)

            # 更新记录
            success = self.db_manager.update_record(record_id, encrypted_data)

            elapsed = time.time() - start_time
            if success:
                logger.info(f"Updated record {record_id} in {elapsed:.3f} seconds")
            else:
                logger.info(f"Record {record_id} not found for update")

            return success
        except Exception as e:
            logger.error(f"Error updating record: {e}")
            raise

    def update_records_batch(self, updates: List[Tuple[int, str]]) -> int:
        """
        批量更新记录数据

        Args:
            updates: 更新列表，每个元素为(record_id, new_data)元组

        Returns:
            成功更新的记录数量
        """
        try:
            start_time = time.time()

            # 准备批量更新数据
            encrypted_updates = []

            for record_id, new_data in updates:
                # 加密新数据
                encrypted_data = self.aes_manager.encrypt(new_data)
                encrypted_updates.append((record_id, encrypted_data))

            # 批量更新记录
            updated_count = self.db_manager.update_records_batch(encrypted_updates)

            elapsed = time.time() - start_time
            logger.info(
                f"Updated {updated_count} records in batch in {elapsed:.3f} seconds"
            )

            return updated_count
        except Exception as e:
            logger.error(f"Error updating records in batch: {e}")
            raise

    def delete_record(self, record_id: int) -> bool:
        """
        删除记录

        Args:
            record_id: 记录ID

        Returns:
            是否成功删除
        """
        try:
            return self.db_manager.delete_record(record_id)
        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            raise

    def delete_records_batch(self, record_ids: List[int]) -> int:
        """
        批量删除记录

        Args:
            record_ids: 记录ID列表

        Returns:
            成功删除的记录数量
        """
        try:
            return self.db_manager.delete_records_batch(record_ids)
        except Exception as e:
            logger.error(f"Error deleting records in batch: {e}")
            raise

    def cleanup_references(self) -> int:
        """
        清理未使用的引用

        Returns:
            删除的引用数量
        """
        try:
            return self.db_manager.cleanup_unused_references()
        except Exception as e:
            logger.error(f"Error cleaning up references: {e}")
            raise

    def export_data(self, output_file: str, include_encrypted: bool = False) -> int:
        """
        导出数据到JSON文件

        Args:
            output_file: 输出文件路径
            include_encrypted: 是否包含加密数据

        Returns:
            导出的记录数量
        """
        try:
            start_time = time.time()

            # 获取所有记录
            records = self.db_manager.get_all_records()

            # 准备导出数据
            export_data = []

            for record in records:
                record_data = {
                    "id": record.id,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": (
                        record.updated_at.isoformat()
                        if hasattr(record, "updated_at")
                        else None
                    ),
                }

                # 解密数据
                try:
                    decrypted_data = self.aes_manager.decrypt(record.encrypted_data)
                    record_data["data"] = decrypted_data.decode("utf-8")
                except Exception as e:
                    logger.error(f"Error decrypting data for record {record.id}: {e}")
                    record_data["data"] = None

                # 如果包含加密数据
                if include_encrypted:
                    record_data["encrypted_index"] = record.encrypted_index.hex()
                    record_data["encrypted_data"] = record.encrypted_data.hex()

                export_data.append(record_data)

            # 写入文件
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            elapsed = time.time() - start_time
            logger.info(
                f"Exported {len(export_data)} records to {output_file} in {elapsed:.3f} seconds"
            )

            return len(export_data)
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise

    def import_data(self, input_file: str, enable_range_query: bool = False) -> int:
        """
        从JSON文件导入数据

        Args:
            input_file: 输入文件路径
            enable_range_query: 是否为导入的记录启用范围查询

        Returns:
            导入的记录数量
        """
        try:
            start_time = time.time()

            # 读取文件
            with open(input_file, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            # 准备批量导入
            records = []

            for item in import_data:
                # 如果数据包含加密索引，尝试直接使用
                if "encrypted_index" in item and "encrypted_data" in item:
                    try:
                        encrypted_index = bytes.fromhex(item["encrypted_index"])
                        encrypted_data = bytes.fromhex(item["encrypted_data"])

                        # 添加到数据库
                        self.db_manager.add_encrypted_record(
                            encrypted_index, encrypted_data
                        )
                        continue
                    except Exception as e:
                        logger.error(f"Error importing encrypted data: {e}")

                # 否则，从明文数据创建新记录
                if "data" in item and isinstance(item["data"], str):
                    try:
                        # 尝试解析JSON数据
                        data_obj = json.loads(item["data"])

                        # 如果数据对象包含索引字段
                        if "index" in data_obj:
                            index_value = int(data_obj["index"])
                            records.append(
                                (index_value, item["data"], enable_range_query)
                            )
                    except (json.JSONDecodeError, ValueError, KeyError):
                        # 如果解析失败，跳过该记录
                        logger.warning(f"Skipping record with invalid data format")

            # 批量添加记录
            if records:
                record_ids = self.add_records_batch(records)

                elapsed = time.time() - start_time
                logger.info(
                    f"Imported {len(record_ids)} records from {input_file} in {elapsed:.3f} seconds"
                )

                return len(record_ids)
            else:
                logger.warning("No valid records found for import")
                return 0
        except Exception as e:
            logger.error(f"Error importing data: {e}")
            raise


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Secure Database with FHE Indexing")

    parser.add_argument("--genkeys", action="store_true", help="Generate new keys")
    parser.add_argument(
        "--encrypt-only",
        action="store_true",
        help="Encrypt-only mode (public key only)",
    )
    parser.add_argument("--add", action="store_true", help="Add a new record")
    parser.add_argument("--get", type=int, help="Get record by ID")
    parser.add_argument("--search", type=int, help="Search records by index value")
    parser.add_argument("--update", type=int, help="Update record by ID")
    parser.add_argument("--delete", type=int, help="Delete record by ID")
    parser.add_argument(
        "--cleanup", action="store_true", help="Cleanup unused references"
    )
    parser.add_argument("--index", type=int, help="Index value for add operation")
    parser.add_argument("--data", type=str, help="Data for add/update operation")

    parser.add_argument(
        "--range", action="store_true", help="Enable range query for add operation"
    )
    parser.add_argument("--min", type=int, help="Minimum value for range search")
    parser.add_argument("--max", type=int, help="Maximum value for range search")
    parser.add_argument("--batch", action="store_true", help="Use batch operations")
    parser.add_argument(
        "--ids",
        type=str,
        help="Comma-separated list of record IDs for batch operations",
    )
    parser.add_argument("--export", type=str, help="Export data to JSON file")
    parser.add_argument(
        "--import", dest="import_file", type=str, help="Import data from JSON file"
    )
    parser.add_argument(
        "--include-encrypted",
        action="store_true",
        help="Include encrypted data in export",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    try:
        if args.genkeys:
            # 生成新密钥
            demo = SecureDB(load_keys=False, encrypt_only=False)
            print("New keys generated successfully")
            return

        # 初始化演示
        demo = SecureDB(load_keys=True, encrypt_only=args.encrypt_only)

        if args.add:
            # 添加记录
            if args.index is None or args.data is None:
                print("Error: --index and --data are required for add operation")
                return

            record_id = demo.add_record(args.index, args.data, args.range)
            print(f"Added record with ID: {record_id}")

        elif args.get is not None:
            # 获取记录
            if args.batch and args.ids:
                # 批量获取
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                results = demo.get_records_batch(record_ids)
                for record_id, data in results.items():
                    if data:
                        print(f"Record {record_id}: {data}")
                    else:
                        print(f"Record {record_id} not found")
            else:
                # 单条获取
                data = demo.get_record(args.get)
                if data:
                    print(f"Record {args.get}: {data}")
                else:
                    print(f"Record {args.get} not found")

        elif args.search is not None:
            # 搜索记录
            results = demo.search_by_index(args.search)
            if results:
                print(f"Found {len(results)} matching records:")
                for result in results:
                    print(f"Record {result['id']}: {result['data']}")
            else:
                print("No matching records found")

        elif args.min is not None or args.max is not None:
            # 范围搜索
            results = demo.search_by_range(args.min, args.max)
            if results:
                print(f"Found {len(results)} records in range:")
                for result in results:
                    print(f"Record {result['id']}: {result['data']}")
            else:
                print("No records found in the specified range")

        elif args.update is not None:
            # 更新记录
            if args.data is None:
                print("Error: --data is required for update operation")
                return

            if args.batch and args.ids:
                # 批量更新
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                updates = [(record_id, args.data) for record_id in record_ids]
                updated_count = demo.update_records_batch(updates)
                print(f"Updated {updated_count} records")
            else:
                # 单条更新
                success = demo.update_record(args.update, args.data)
                if success:
                    print(f"Record {args.update} updated successfully")
                else:
                    print(f"Record {args.update} not found")

        elif args.delete is not None:
            # 删除记录
            if args.batch and args.ids:
                # 批量删除
                record_ids = [int(id_str) for id_str in args.ids.split(",")]
                deleted_count = demo.delete_records_batch(record_ids)
                print(f"Deleted {deleted_count} records")
            else:
                # 单条删除
                success = demo.delete_record(args.delete)
                if success:
                    print(f"Record {args.delete} deleted successfully")
                else:
                    print(f"Record {args.delete} not found")

        elif args.cleanup:
            # 清理未使用的引用
            count = demo.cleanup_references()
            print(f"Cleaned up {count} unused references")

        elif args.export:
            # 导出数据
            count = demo.export_data(args.export, args.include_encrypted)
            print(f"Exported {count} records to {args.export}")

        elif args.import_file:
            # 导入数据
            count = demo.import_data(args.import_file, args.range)
            print(f"Imported {count} records from {args.import_file}")

        else:
            print("No operation specified. Use --help for usage information.")

    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Unhandled exception")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
