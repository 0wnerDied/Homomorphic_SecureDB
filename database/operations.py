"""
数据库操作模块
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
import xxhash
from typing import List, Optional, Tuple

from .models import EncryptedRecord, ReferenceTable, RangeQueryIndex, init_db

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
        self,
        encrypted_index: bytes,
        encrypted_data: bytes,
        range_query_bits: List[bytes] = None,
    ) -> int:
        """
        添加加密记录到数据库

        Args:
            encrypted_index: 加密的索引
            encrypted_data: 加密的数据（包含IV）
            range_query_bits: 用于范围查询的加密位表示（可选）

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
            session.flush()  # 获取ID但不提交

            # 如果提供了范围查询位，添加范围查询索引
            if range_query_bits:
                for bit_position, encrypted_bit in enumerate(range_query_bits):
                    range_index = RangeQueryIndex(
                        record_id=record.id,
                        bit_position=bit_position,
                        encrypted_bit=encrypted_bit,
                    )
                    session.add(range_index)

            session.commit()
            logger.info(f"Added encrypted record with ID {record.id}")
            return record.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding encrypted record: {e}")
            raise
        finally:
            session.close()

    def add_encrypted_records_batch(
        self, records: List[Tuple[bytes, bytes, Optional[List[bytes]]]]
    ) -> List[int]:
        """
        批量添加加密记录到数据库

        Args:
            records: 记录列表，每个元素为(encrypted_index, encrypted_data, range_query_bits)元组
                    range_query_bits可以为None

        Returns:
            新记录ID列表
        """
        session = self.Session()
        try:
            record_ids = []

            for encrypted_index, encrypted_data, range_query_bits in records:
                # 获取或创建引用
                ref_id = self._get_or_create_reference(session, encrypted_data)

                # 创建记录
                record = EncryptedRecord(
                    encrypted_index=encrypted_index, encrypted_data=encrypted_data
                )
                session.add(record)
                session.flush()  # 获取ID但不提交

                # 如果提供了范围查询位，添加范围查询索引
                if range_query_bits:
                    for bit_position, encrypted_bit in enumerate(range_query_bits):
                        range_index = RangeQueryIndex(
                            record_id=record.id,
                            bit_position=bit_position,
                            encrypted_bit=encrypted_bit,
                        )
                        session.add(range_index)

                record_ids.append(record.id)

            session.commit()
            logger.info(f"Added {len(record_ids)} encrypted records in batch")
            return record_ids
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding encrypted records in batch: {e}")
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

    def get_records_by_ids(self, record_ids: List[int]) -> List[EncryptedRecord]:
        """
        通过ID列表获取多个加密记录

        Args:
            record_ids: 记录ID列表

        Returns:
            加密记录对象列表
        """
        session = self.Session()
        try:
            records = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id.in_(record_ids))
                .all()
            )
            logger.info(f"Retrieved {len(records)} records by IDs")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving records by IDs: {e}")
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

    def search_by_range(
        self, fhe_manager, min_value: int = None, max_value: int = None
    ) -> List[EncryptedRecord]:
        """
        使用范围查询索引查询记录

        Args:
            fhe_manager: FHEManager实例，用于比较加密索引
            min_value: 范围最小值，如果为None则不检查下限
            max_value: 范围最大值，如果为None则不检查上限

        Returns:
            匹配的记录列表
        """
        session = self.Session()
        try:
            # 获取所有记录ID
            record_ids = session.query(EncryptedRecord.id).distinct().all()
            record_ids = [r[0] for r in record_ids]

            # 获取每个记录的范围查询位
            matching_record_ids = []

            for record_id in record_ids:
                # 获取记录的所有范围查询位
                range_indices = (
                    session.query(RangeQueryIndex)
                    .filter(RangeQueryIndex.record_id == record_id)
                    .order_by(RangeQueryIndex.bit_position)
                    .all()
                )

                if not range_indices:
                    continue  # 跳过没有范围查询索引的记录

                # 提取加密位
                encrypted_bits = [idx.encrypted_bit for idx in range_indices]

                # 检查范围
                in_range = fhe_manager.compare_range(
                    encrypted_bits, min_value, max_value
                )
                if in_range:
                    matching_record_ids.append(record_id)

            # 获取匹配的记录
            matching_records = self.get_records_by_ids(matching_record_ids)

            logger.info(
                f"Found {len(matching_records)} records in range [{min_value}, {max_value}]"
            )
            return matching_records
        except SQLAlchemyError as e:
            logger.error(f"Error searching records by range: {e}")
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
            # 首先删除关联的范围查询索引
            session.query(RangeQueryIndex).filter(
                RangeQueryIndex.record_id == record_id
            ).delete()

            # 然后删除记录
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

    def delete_records_batch(self, record_ids: List[int]) -> int:
        """
        批量删除加密记录

        Args:
            record_ids: 要删除的记录ID列表

        Returns:
            成功删除的记录数量
        """
        session = self.Session()
        try:
            # 首先删除关联的范围查询索引
            session.query(RangeQueryIndex).filter(
                RangeQueryIndex.record_id.in_(record_ids)
            ).delete(synchronize_session=False)

            # 然后删除记录
            deleted_count = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id.in_(record_ids))
                .delete(synchronize_session=False)
            )

            session.commit()
            logger.info(f"Deleted {deleted_count} records in batch")
            return deleted_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error deleting records in batch: {e}")
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

    def update_records_batch(self, updates: List[Tuple[int, bytes]]) -> int:
        """
        批量更新加密记录

        Args:
            updates: 更新列表，每个元素为(record_id, encrypted_data)元组

        Returns:
            成功更新的记录数量
        """
        session = self.Session()
        try:
            updated_count = 0

            for record_id, encrypted_data in updates:
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
                    updated_count += 1

            session.commit()
            logger.info(f"Updated {updated_count} records in batch")
            return updated_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating records in batch: {e}")
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
