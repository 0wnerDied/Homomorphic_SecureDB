"""
数据库操作模块
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
import xxhash
from typing import List, Optional

from .models import EncryptedRecord, ReferenceTable, init_db

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器，处理数据库操作"""

    def __init__(self, connection_string: str):
        """
        初始化数据库管理器

        Args:
            connection_string: 数据库连接字符串
        """
        try:
            self.engine = create_engine(connection_string)
            init_db(self.engine)  # 初始化数据库表
            self.Session = sessionmaker(bind=self.engine)
            self.reference_cache = {}  # 引用表缓存
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _get_or_create_reference(self, session, encrypted_data: bytes) -> int:
        """
        获取或创建引用表条目

        Args:
            session: 数据库会话
            encrypted_data: 加密数据

        Returns:
            引用ID
        """
        # 计算哈希值
        hash_value = xxhash.xxh64(encrypted_data).hexdigest()

        # 检查缓存
        if hash_value in self.reference_cache:
            return self.reference_cache[hash_value]

        # 检查数据库
        ref = (
            session.query(ReferenceTable)
            .filter(ReferenceTable.hash_value == hash_value)
            .first()
        )

        if ref is None:
            # 创建新引用
            ref = ReferenceTable(hash_value=hash_value, encrypted_data=encrypted_data)
            session.add(ref)
            session.flush()  # 获取ID但不提交

        # 更新缓存
        self.reference_cache[hash_value] = ref.id

        return ref.id

    def add_encrypted_record(
        self, encrypted_index: bytes, encrypted_data: bytes
    ) -> int:
        """
        添加加密记录到数据库

        Args:
            encrypted_index: 加密的索引
            encrypted_data: 加密的数据（包含IV）

        Returns:
            新记录的ID
        """
        session = self.Session()
        try:
            # 获取或创建引用
            ref_id = self._get_or_create_reference(session, encrypted_data)

            # 创建记录
            record = EncryptedRecord(
                encrypted_index=encrypted_index, encrypted_data=encrypted_data
            )
            session.add(record)
            session.commit()
            logger.info(f"Added encrypted record with ID {record.id}")
            return record.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding encrypted record: {e}")
            raise
        finally:
            session.close()

    def get_all_records(self) -> List[EncryptedRecord]:
        """
        获取所有加密记录

        Returns:
            加密记录列表
        """
        session = self.Session()
        try:
            records = session.query(EncryptedRecord).all()
            logger.info(f"Retrieved {len(records)} encrypted records")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving records: {e}")
            raise
        finally:
            session.close()

    def get_record_by_id(self, record_id: int) -> Optional[EncryptedRecord]:
        """
        通过ID获取加密记录

        Args:
            record_id: 记录ID

        Returns:
            加密记录对象，如果不存在则返回None
        """
        session = self.Session()
        try:
            record = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id == record_id)
                .first()
            )
            if record:
                logger.info(f"Retrieved record with ID {record_id}")
            else:
                logger.info(f"Record with ID {record_id} not found")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving record {record_id}: {e}")
            raise
        finally:
            session.close()

    def search_by_encrypted_index(
        self, fhe_manager, query_value: int
    ) -> List[EncryptedRecord]:
        """
        使用同态加密查询匹配的记录

        Args:
            fhe_manager: FHEManager实例，用于比较加密索引
            query_value: 要查询的索引值

        Returns:
            匹配的记录列表
        """
        session = self.Session()
        try:
            all_records = session.query(EncryptedRecord).all()
            matching_records = []

            logger.info(f"Searching for records with index {query_value}")
            for record in all_records:
                # 使用同态加密比较索引
                if fhe_manager.compare_encrypted(record.encrypted_index, query_value):
                    matching_records.append(record)

            logger.info(f"Found {len(matching_records)} matching records")
            return matching_records
        except SQLAlchemyError as e:
            logger.error(f"Error searching records: {e}")
            raise
        finally:
            session.close()

    def search_by_multiple_indices(
        self, fhe_manager, query_values: List[int]
    ) -> List[EncryptedRecord]:
        """
        使用同态加密查询匹配多个索引值的记录

        Args:
            fhe_manager: FHEManager实例，用于比较加密索引
            query_values: 要查询的索引值列表

        Returns:
            匹配的记录列表
        """
        session = self.Session()
        try:
            all_records = session.query(EncryptedRecord).all()
            matching_records = []

            logger.info(f"Searching for records with indices {query_values}")
            for record in all_records:
                # 对每个查询值进行检查
                for query_value in query_values:
                    if fhe_manager.compare_encrypted(
                        record.encrypted_index, query_value
                    ):
                        matching_records.append(record)
                        break  # 一旦找到匹配，就不再检查其他查询值

            logger.info(f"Found {len(matching_records)} matching records")
            return matching_records
        except SQLAlchemyError as e:
            logger.error(f"Error searching records: {e}")
            raise
        finally:
            session.close()

    def delete_record(self, record_id: int) -> bool:
        """
        删除加密记录

        Args:
            record_id: 要删除的记录ID

        Returns:
            是否成功删除
        """
        session = self.Session()
        try:
            record = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id == record_id)
                .first()
            )
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Deleted record with ID {record_id}")
                return True
            else:
                logger.info(f"Record with ID {record_id} not found for deletion")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error deleting record {record_id}: {e}")
            raise
        finally:
            session.close()

    def update_record(self, record_id: int, encrypted_data: bytes) -> bool:
        """
        更新加密记录的数据

        Args:
            record_id: 要更新的记录ID
            encrypted_data: 新的加密数据

        Returns:
            是否成功更新
        """
        session = self.Session()
        try:
            record = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id == record_id)
                .first()
            )
            if record:
                # 获取或创建引用
                ref_id = self._get_or_create_reference(session, encrypted_data)

                # 更新记录
                record.encrypted_data = encrypted_data
                session.commit()
                logger.info(f"Updated record with ID {record_id}")
                return True
            else:
                logger.info(f"Record with ID {record_id} not found for update")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating record {record_id}: {e}")
            raise
        finally:
            session.close()

    def clear_reference_cache(self):
        """清除引用表缓存"""
        self.reference_cache.clear()
        logger.info("Reference cache cleared")

    def cleanup_unused_references(self) -> int:
        """
        清理未使用的引用表条目

        Returns:
            删除的条目数量
        """
        session = self.Session()
        try:
            # 获取所有使用中的加密数据哈希值
            used_data = session.query(EncryptedRecord.encrypted_data).all()
            used_hashes = set(xxhash.xxh64(data[0]).hexdigest() for data in used_data)

            # 查找未使用的引用表条目
            unused_refs = (
                session.query(ReferenceTable)
                .filter(~ReferenceTable.hash_value.in_(used_hashes))
                .all()
            )

            # 删除未使用的条目
            count = len(unused_refs)
            for ref in unused_refs:
                session.delete(ref)

            session.commit()
            logger.info(f"Deleted {count} unused reference entries")

            # 清除缓存
            self.clear_reference_cache()

            return count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error cleaning up unused references: {e}")
            raise
        finally:
            session.close()
