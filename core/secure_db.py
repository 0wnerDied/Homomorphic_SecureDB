"""
安全数据库核心模块 - 同态加密安全数据库系统
"""

import logging
import os
import getpass
import time
import json
from typing import Dict, Any, List, Optional, Tuple

# 导入项目模块
from core.config import (
    DB_CONNECTION_STRING,
    ENCRYPTION_CONFIG,
    LOG_CONFIG,
    KEY_MANAGEMENT,
    PERFORMANCE_CONFIG,
)
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
    """安全数据库系统主类"""

    def __init__(
        self,
        load_keys: bool = False,
        encrypt_only: bool = False,
        cache_size: int = None,
    ):
        """
        初始化安全数据库系统

        Args:
            load_keys: 是否从文件加载密钥
            encrypt_only: 是否仅用于加密 (不需要私钥) 
            cache_size: 缓存大小, 如果为None则使用配置文件中的值
        """
        # 确保密钥目录存在
        os.makedirs(KEY_MANAGEMENT["keys_dir"], exist_ok=True)

        # 初始化密钥管理器
        self.key_manager = KeyManager(KEY_MANAGEMENT["keys_dir"])

        # 初始化FHE管理器
        self.fhe_manager = FHEManager(
            ENCRYPTION_CONFIG["fhe"], self.key_manager, encrypt_only=encrypt_only
        )

        # 初始化数据库管理器, 使用LRU缓存
        cache_size = cache_size or PERFORMANCE_CONFIG["cache_size"]
        self.db_manager = DatabaseManager(DB_CONNECTION_STRING, cache_size=cache_size)
        logger.info(f"初始化数据库管理器, 缓存大小: {cache_size}")

        # 初始化AES管理器
        if load_keys:
            try:
                # 从文件加载AES密钥
                password = getpass.getpass("请输入密码以解密AES密钥: ")
                aes_key = self.key_manager.load_aes_key(
                    KEY_MANAGEMENT["aes_key_file"], password
                )
                self.aes_manager = AESManager(key=aes_key)
                logger.info("AES密钥加载成功")
            except Exception as e:
                logger.error(f"加载AES密钥失败: {e}")
                # 如果加载失败, 创建新的AES密钥
                logger.info("创建新的AES密钥")
                self.aes_manager = AESManager()
                self._save_aes_key()
        else:
            # 创建新的AES密钥
            self.aes_manager = AESManager()
            self._save_aes_key()

    def _save_aes_key(self):
        """保存AES密钥"""
        try:
            password = getpass.getpass("请输入密码以加密AES密钥: ")
            confirm = getpass.getpass("确认密码: ")

            if password != confirm:
                logger.error("密码不匹配")
                return

            self.key_manager.save_aes_key(
                self.aes_manager.get_key(), KEY_MANAGEMENT["aes_key_file"], password
            )
            logger.info("AES密钥保存成功")
        except Exception as e:
            logger.error(f"保存AES密钥失败: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        return self.db_manager.get_cache_stats()

    def clear_caches(self) -> None:
        """清除所有缓存"""
        self.db_manager.clear_all_caches()
        logger.info("所有缓存已清除")

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

            # 如果启用范围查询, 创建范围查询索引
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
            logger.info(f"添加记录, ID: {record_id}, 耗时: {elapsed:.3f}秒")

            return record_id
        except Exception as e:
            logger.error(f"添加记录失败: {e}")
            raise

    def add_records_batch(self, records: List[Tuple[int, str, bool]]) -> List[int]:
        """
        批量添加加密记录

        Args:
            records: 记录列表, 每个元素为(index_value, data, enable_range_query)元组

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

                # 如果启用范围查询, 创建范围查询索引
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
            logger.info(f"批量添加记录, 数量: {len(record_ids)}, 耗时: {elapsed:.3f}秒")

            return record_ids
        except Exception as e:
            logger.error(f"批量添加记录失败: {e}")
            raise

    def get_record(self, record_id: int) -> Optional[str]:
        """
        获取并解密记录

        Args:
            record_id: 记录ID

        Returns:
            解密后的数据, 如果记录不存在则返回None
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
            logger.info(f"获取并解密记录, ID: {record_id}, 耗时: {elapsed:.3f}秒")

            return decrypted_data.decode("utf-8")
        except Exception as e:
            logger.error(f"获取记录失败: {e}")
            raise

    def get_records_batch(self, record_ids: List[int]) -> Dict[int, Optional[str]]:
        """
        批量获取并解密记录

        Args:
            record_ids: 记录ID列表

        Returns:
            记录ID到解密数据的映射, 如果记录不存在则值为None
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
                f"批量获取并解密记录, 数量: {len(records)}, 耗时: {elapsed:.3f}秒"
            )

            return result
        except Exception as e:
            logger.error(f"批量获取记录失败: {e}")
            raise

    def search_by_index(self, index_value: int) -> List[Dict[str, Any]]:
        """
        按索引值搜索记录

        Args:
            index_value: 要搜索的索引值

        Returns:
            匹配记录的列表, 每个记录包含ID和解密后的数据
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
                f"按索引搜索记录, 索引值: {index_value}, 找到: {len(results)}条记录, 耗时: {elapsed:.3f}秒"
            )

            return results
        except Exception as e:
            logger.error(f"搜索记录失败: {e}")
            raise

    def search_by_range(
        self, min_value: int = None, max_value: int = None
    ) -> List[Dict[str, Any]]:
        """
        按索引范围搜索记录

        Args:
            min_value: 范围最小值, 如果为None则不检查下限
            max_value: 范围最大值, 如果为None则不检查上限

        Returns:
            匹配记录的列表, 每个记录包含ID和解密后的数据
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
                f"按范围搜索记录, 范围: {range_str}, 找到: {len(results)}条记录, 耗时: {elapsed:.3f}秒"
            )

            return results
        except Exception as e:
            logger.error(f"按范围搜索记录失败: {e}")
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
                logger.info(f"更新记录成功, ID: {record_id}, 耗时: {elapsed:.3f}秒")
            else:
                logger.info(f"更新记录失败, ID: {record_id}不存在")

            return success
        except Exception as e:
            logger.error(f"更新记录失败: {e}")
            raise

    def update_records_batch(self, updates: List[Tuple[int, str]]) -> int:
        """
        批量更新记录数据

        Args:
            updates: 更新列表, 每个元素为(record_id, new_data)元组

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
                f"批量更新记录, 成功数量: {updated_count}, 耗时: {elapsed:.3f}秒"
            )

            return updated_count
        except Exception as e:
            logger.error(f"批量更新记录失败: {e}")
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
            logger.error(f"删除记录失败: {e}")
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
            logger.error(f"批量删除记录失败: {e}")
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
            logger.error(f"清理未使用引用失败: {e}")
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
                    logger.error(f"解密记录数据失败, ID: {record.id}: {e}")
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
                f"导出数据成功, 记录数: {len(export_data)}, 文件: {output_file}, 耗时: {elapsed:.3f}秒"
            )

            return len(export_data)
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
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
                # 如果数据包含加密索引, 尝试直接使用
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
                        logger.error(f"导入加密数据失败: {e}")

                # 否则, 从明文数据创建新记录
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
                        # 如果解析失败, 跳过该记录
                        logger.warning(f"跳过格式无效的记录")

            # 批量添加记录
            if records:
                record_ids = self.add_records_batch(records)

                elapsed = time.time() - start_time
                logger.info(
                    f"导入数据成功, 记录数: {len(record_ids)}, 文件: {input_file}, 耗时: {elapsed:.3f}秒"
                )

                return len(record_ids)
            else:
                logger.warning("没有找到有效的记录可导入")
                return 0
        except Exception as e:
            logger.error(f"导入数据失败: {e}")
            raise
