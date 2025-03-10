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
from ..utils import LRUCache, timing_decorator

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器，处理数据库操作"""

    def __init__(self, connection_string: str, cache_size: int = 1000):
        """
        初始化数据库管理器

        Args:
            connection_string: 数据库连接字符串
            cache_size: 缓存大小
        """
        try:
            self.engine = create_engine(connection_string)
            init_db(self.engine)  # 初始化数据库表
            self.Session = sessionmaker(bind=self.engine)
            self.reference_cache = {}  # 引用表缓存

            # 初始化LRU缓存
            self.record_cache = LRUCache[int, EncryptedRecord](
                capacity=cache_size
            )  # 记录缓存
            self.index_query_cache = LRUCache[int, List[int]](
                capacity=cache_size
            )  # 索引查询缓存
            self.range_query_cache = LRUCache[str, List[int]](
                capacity=cache_size
            )  # 范围查询缓存

            logger.info(
                f"Database manager initialized successfully with cache size {cache_size}"
            )
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

    @timing_decorator
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

            # 更新缓存
            self.record_cache.put(record.id, record)

            logger.info(f"Added encrypted record with ID {record.id}")
            return record.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding encrypted record: {e}")
            raise
        finally:
            session.close()

    @timing_decorator
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
            new_records = []

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
                new_records.append((record.id, record))

            session.commit()

            # 更新缓存
            for record_id, record in new_records:
                self.record_cache.put(record_id, record)

            logger.info(f"Added {len(record_ids)} encrypted records in batch")
            return record_ids
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding encrypted records in batch: {e}")
            raise
        finally:
            session.close()

    @timing_decorator
    def get_all_records(self) -> List[EncryptedRecord]:
        """
        获取所有加密记录

        Returns:
            加密记录列表
        """
        session = self.Session()
        try:
            records = session.query(EncryptedRecord).all()

            # 更新缓存
            for record in records:
                self.record_cache.put(record.id, record)

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
        # 首先检查缓存
        cached_record = self.record_cache.get(record_id)
        if cached_record is not None:
            logger.info(f"Cache hit: Retrieved record with ID {record_id} from cache")
            return cached_record

        # 缓存未命中，从数据库获取
        session = self.Session()
        try:
            record = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id == record_id)
                .first()
            )

            # 更新缓存
            if record:
                self.record_cache.put(record_id, record)
                logger.info(f"Retrieved record with ID {record_id} (cache miss)")
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
        if not record_ids:
            return []

        # 首先从缓存获取
        records = []
        missing_ids = []

        for record_id in record_ids:
            cached_record = self.record_cache.get(record_id)
            if cached_record is not None:
                records.append(cached_record)
            else:
                missing_ids.append(record_id)

        # 如果所有记录都在缓存中，直接返回
        if not missing_ids:
            logger.info(f"Cache hit: Retrieved all {len(records)} records from cache")
            return records

        # 否则，从数据库获取缺失的记录
        session = self.Session()
        try:
            db_records = (
                session.query(EncryptedRecord)
                .filter(EncryptedRecord.id.in_(missing_ids))
                .all()
            )

            # 更新缓存并添加到结果列表
            for record in db_records:
                self.record_cache.put(record.id, record)
                records.append(record)

            logger.info(
                f"Retrieved {len(db_records)} records from database, {len(records) - len(db_records)} from cache"
            )
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving records by IDs: {e}")
            raise
        finally:
            session.close()

    @timing_decorator
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
        # 检查缓存
        cached_result = self.index_query_cache.get(query_value)
        if cached_result is not None:
            logger.info(f"Cache hit: Using cached result for index query {query_value}")
            return self.get_records_by_ids(cached_result)

        session = self.Session()
        try:
            all_records = session.query(EncryptedRecord).all()
            matching_records = []
            matching_ids = []

            logger.info(f"Searching for records with index {query_value}")
            for record in all_records:
                # 使用同态加密比较索引
                if fhe_manager.compare_encrypted(record.encrypted_index, query_value):
                    matching_records.append(record)
                    matching_ids.append(record.id)

                    # 更新记录缓存
                    self.record_cache.put(record.id, record)

            # 更新查询结果缓存
            self.index_query_cache.put(query_value, matching_ids)

            logger.info(f"Found {len(matching_records)} matching records")
            return matching_records
        except SQLAlchemyError as e:
            logger.error(f"Error searching records: {e}")
            raise
        finally:
            session.close()

    @timing_decorator
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
        # 尝试从缓存获取每个查询值的结果
        all_matching_ids = set()
        uncached_values = []

        for query_value in query_values:
            cached_result = self.index_query_cache.get(query_value)
            if cached_result is not None:
                all_matching_ids.update(cached_result)
            else:
                uncached_values.append(query_value)

        # 如果所有查询值都有缓存结果，直接返回
        if not uncached_values:
            logger.info(f"Cache hit: Using cached results for all index queries")
            return self.get_records_by_ids(list(all_matching_ids))

        session = self.Session()
        try:
            all_records = session.query(EncryptedRecord).all()
            matching_records = []

            # 为未缓存的查询值创建结果缓存
            value_to_ids = {value: [] for value in uncached_values}

            logger.info(f"Searching for records with indices {query_values}")
            for record in all_records:
                # 对每个未缓存的查询值进行检查
                for query_value in uncached_values:
                    if fhe_manager.compare_encrypted(
                        record.encrypted_index, query_value
                    ):
                        if record.id not in all_matching_ids:  # 避免重复
                            matching_records.append(record)
                            all_matching_ids.add(record.id)

                            # 更新记录缓存
                            self.record_cache.put(record.id, record)

                        # 更新查询值到ID的映射
                        value_to_ids[query_value].append(record.id)
                        break  # 一旦找到匹配，就不再检查其他查询值

            # 更新查询结果缓存
            for query_value, ids in value_to_ids.items():
                self.index_query_cache.put(query_value, ids)

            logger.info(f"Found {len(matching_records)} matching records")
            return matching_records
        except SQLAlchemyError as e:
            logger.error(f"Error searching records: {e}")
            raise
        finally:
            session.close()

    @timing_decorator
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
        # 创建范围查询的缓存键
        range_key = f"{min_value if min_value is not None else '*'}-{max_value if max_value is not None else '*'}"

        # 检查缓存
        cached_result = self.range_query_cache.get(range_key)
        if cached_result is not None:
            logger.info(f"Cache hit: Using cached result for range query [{range_key}]")
            return self.get_records_by_ids(cached_result)

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

            # 更新范围查询缓存
            self.range_query_cache.put(range_key, matching_record_ids)

            # 获取匹配的记录
            matching_records = self.get_records_by_ids(matching_record_ids)

            logger.info(f"Found {len(matching_records)} records in range [{range_key}]")
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

                # 从缓存中移除
                self.record_cache.remove(record_id)

                # 清除可能包含此记录的查询缓存
                self._invalidate_query_caches()

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

            # 从缓存中移除
            for record_id in record_ids:
                self.record_cache.remove(record_id)

            # 清除查询缓存
            self._invalidate_query_caches()

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

                # 更新缓存
                self.record_cache.put(record_id, record)

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

                    # 更新缓存
                    self.record_cache.put(record_id, record)

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

    def clear_all_caches(self):
        """清除所有缓存"""
        self.reference_cache.clear()
        self.record_cache.clear()
        self.index_query_cache.clear()
        self.range_query_cache.clear()
        logger.info("All caches cleared")

    def _invalidate_query_caches(self):
        """当记录被修改或删除时，使查询缓存失效"""
        self.index_query_cache.clear()
        self.range_query_cache.clear()
        logger.info("Query caches invalidated")

    def get_cache_stats(self):
        """
        获取缓存统计信息

        Returns:
            包含各个缓存统计信息的字典
        """
        return {
            "record_cache": self.record_cache.get_stats(),
            "index_query_cache": self.index_query_cache.get_stats(),
            "range_query_cache": self.range_query_cache.get_stats(),
            "reference_cache_size": len(self.reference_cache),
        }

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
