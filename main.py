"""
主程序 - 同态加密数据库演示
"""

import logging
import argparse
import os
import sys
import getpass
import time
from typing import Dict, Any, List, Optional

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

    def add_record(self, index_value: int, data: str) -> int:
        """
        添加加密记录

        Args:
            index_value: 索引值
            data: 要加密的数据

        Returns:
            新记录的ID
        """
        try:
            start_time = time.time()

            # 加密索引
            encrypted_index = self.fhe_manager.encrypt_int(index_value)

            # 加密数据
            encrypted_data = self.aes_manager.encrypt(data)

            # 添加到数据库
            record_id = self.db_manager.add_encrypted_record(
                encrypted_index, encrypted_data
            )

            elapsed = time.time() - start_time
            logger.info(f"Added record with ID {record_id} in {elapsed:.3f} seconds")

            return record_id
        except Exception as e:
            logger.error(f"Error adding record: {e}")
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
            if args.index is None or args.data is None:
                print("Error: Both --index and --data are required for add operation")
                return

            record_id = demo.add_record(args.index, args.data)
            print(f"Record added with ID: {record_id}")

        elif args.get is not None:
            data = demo.get_record(args.get)
            if data:
                print(f"Record {args.get}: {data}")
            else:
                print(f"Record {args.get} not found")

        elif args.search is not None:
            results = demo.search_by_index(args.search)
            print(f"Found {len(results)} records with index {args.search}:")
            for result in results:
                print(f"  ID: {result['id']}, Data: {result['data']}")

        elif args.update is not None:
            if args.data is None:
                print("Error: --data is required for update operation")
                return

            success = demo.update_record(args.update, args.data)
            if success:
                print(f"Record {args.update} updated successfully")
            else:
                print(f"Record {args.update} not found")

        elif args.delete is not None:
            success = demo.delete_record(args.delete)
            if success:
                print(f"Record {args.delete} deleted successfully")
            else:
                print(f"Record {args.delete} not found")

        elif args.cleanup:
            count = demo.cleanup_references()
            print(f"Cleaned up {count} unused references")

        else:
            print("No operation specified. Use --help for usage information.")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
