# 数据库操作

## 概述

`DatabaseManager` 类封装了所有与加密记录相关的数据库操作。本模块结合 SQLAlchemy ORM 框架、多级缓存策略和同态加密技术，实现了安全且高效的数据存储和检索功能。

## 导入依赖

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
import xxhash
from typing import List, Optional, Tuple

from .models import EncryptedRecord, ReferenceTable, RangeQueryIndex, init_db
from core.utils import LRUCache, timing_decorator

logger = logging.getLogger(__name__)
```

模块依赖 SQLAlchemy 进行数据库操作，xxhash 进行高性能哈希计算，以及自定义的 LRU 缓存和性能计时装饰器。

## `DatabaseManager` 类

### 初始化

```python
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
        self.record_cache = LRUCache[int, EncryptedRecord](capacity=cache_size)  # 记录缓存
        self.index_query_cache = LRUCache[int, List[int]](capacity=cache_size)  # 索引查询缓存
        self.range_query_cache = LRUCache[str, List[int]](capacity=cache_size)  # 范围查询缓存

        logger.info(f"Database manager initialized successfully with cache size {cache_size}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
```

**功能:**
- 创建数据库引擎并初始化表结构
- 设置会话工厂
- 初始化多级缓存系统:
  - `reference_cache`: 字典缓存，存储哈希值到引用 ID 的映射
  - `record_cache`: LRU 缓存，存储记录 ID 到记录对象的映射
  - `index_query_cache`: LRU 缓存，存储索引查询结果
  - `range_query_cache`: LRU 缓存，存储范围查询结果

### 内部方法

#### `_get_or_create_reference`

```python
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
```

**功能:**
- 实现数据去重机制
- 使用 xxHash 算法计算加密数据的哈希值
- 先检查缓存，再检查数据库，避免重复存储相同的加密数据
- 如果数据不存在，创建新的引用表条目

#### `_invalidate_query_caches`

```python
def _invalidate_query_caches(self):
    """当记录被修改或删除时, 使查询缓存失效"""
```

**功能:**
- 当数据发生变化时清除查询缓存
- 确保查询结果的一致性

### 记录管理方法

#### `add_encrypted_record`

```python
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
        encrypted_data: 加密的数据 (包含IV) 
        range_query_bits: 用于范围查询的加密位表示 (可选) 

    Returns:
        新记录的ID
    """
```

**功能:**
- 添加单条加密记录到数据库
- 支持同时添加范围查询索引
- 使用引用表实现数据去重
- 自动更新缓存
- 使用 `timing_decorator` 记录执行时间

#### `add_encrypted_records_batch`

```python
@timing_decorator
def add_encrypted_records_batch(
    self, records: List[Tuple[bytes, bytes, Optional[List[bytes]]]]
) -> List[int]:
    """
    批量添加加密记录到数据库

    Args:
        records: 记录列表, 每个元素为(encrypted_index, encrypted_data, range_query_bits)元组
                range_query_bits可以为None

    Returns:
        新记录ID列表
    """
```

**功能:**
- 批量添加多条加密记录，提高性能
- 在单个事务中处理所有记录，确保原子性
- 支持同时添加范围查询索引
- 批量更新缓存

### 记录检索方法

#### `get_all_records`

```python
@timing_decorator
def get_all_records(self) -> List[EncryptedRecord]:
    """
    获取所有加密记录

    Returns:
        加密记录列表
    """
```

**功能:**
- 检索所有加密记录
- 更新记录缓存
- 记录执行时间

#### `get_record_by_id`

```python
def get_record_by_id(self, record_id: int) -> Optional[EncryptedRecord]:
    """
    通过ID获取加密记录

    Args:
        record_id: 记录ID

    Returns:
        加密记录对象, 如果不存在则返回None
    """
    # 首先检查缓存
    cached_record = self.record_cache.get(record_id)
    if cached_record is not None:
        logger.info(f"Cache hit: Retrieved record with ID {record_id} from cache")
        return cached_record

    # 缓存未命中, 从数据库获取
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
```

**功能:**
- 通过 ID 检索单条记录
- 优先从缓存获取，提高性能
- 缓存未命中时从数据库获取并更新缓存

#### `get_records_by_ids`

```python
def get_records_by_ids(self, record_ids: List[int]) -> List[EncryptedRecord]:
    """
    通过ID列表获取多个加密记录

    Args:
        record_ids: 记录ID列表

    Returns:
        加密记录对象列表
    """
```

**功能:**
- 批量获取多条记录
- 优先从缓存获取，只从数据库获取缓存未命中的记录
- 更新缓存

### 加密查询方法

#### `search_by_encrypted_index`

```python
@timing_decorator
def search_by_encrypted_index(
    self, fhe_manager, query_value: int
) -> List[EncryptedRecord]:
    """
    使用同态加密查询匹配的记录

    Args:
        fhe_manager: FHEManager实例, 用于比较加密索引
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
```

**功能:**
- 使用同态加密技术在加密状态下比较索引值
- 缓存查询结果，提高重复查询性能
- 记录执行时间和结果统计

#### `search_by_multiple_indices`

```python
@timing_decorator
def search_by_multiple_indices(
    self, fhe_manager, query_values: List[int]
) -> List[EncryptedRecord]:
    """
    使用同态加密查询匹配多个索引值的记录

    Args:
        fhe_manager: FHEManager实例, 用于比较加密索引
        query_values: 要查询的索引值列表

    Returns:
        匹配的记录列表
    """
    # 实现多索引查询的逻辑
    # ...
```

**功能:**
- 支持多个索引值的 OR 查询
- 优化查询性能，避免重复处理
- 缓存查询结果

#### `search_by_range`

```python
@timing_decorator
def search_by_range(
    self, fhe_manager, min_value: int = None, max_value: int = None
) -> List[EncryptedRecord]:
    """
    使用范围查询索引查询记录

    Args:
        fhe_manager: FHEManager实例, 用于比较加密索引
        min_value: 范围最小值, 如果为None则不检查下限
        max_value: 范围最大值, 如果为None则不检查上限

    Returns:
        匹配的记录列表
    """
```

**功能:**
- 支持在加密状态下进行范围查询
- 使用位表示法和同态加密比较实现范围检查
- 缓存查询结果

### 记录修改方法

#### `delete_record`

```python
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
```

**功能:**
- 删除单条记录及其关联的范围查询索引
- 从缓存中移除记录
- 使查询缓存失效，确保一致性

#### `delete_records_batch`

```python
def delete_records_batch(self, record_ids: List[int]) -> int:
    """
    批量删除加密记录

    Args:
        record_ids: 要删除的记录ID列表

    Returns:
        成功删除的记录数量
    """
```

**功能:**
- 批量删除多条记录，提高性能
- 在单个事务中处理所有删除操作
- 更新缓存状态

#### `update_record`

```python
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
```

**功能:**
- 更新单条记录的加密数据
- 使用引用表实现数据去重
- 更新缓存

#### `update_records_batch`

```python
def update_records_batch(self, updates: List[Tuple[int, bytes]]) -> int:
    """
    批量更新加密记录

    Args:
        updates: 更新列表, 每个元素为(record_id, encrypted_data)元组

    Returns:
        成功更新的记录数量
    """
```

**功能:**
- 批量更新多条记录，提高性能
- 在单个事务中处理所有更新操作
- 更新缓存状态

### 缓存管理方法

#### `clear_reference_cache`

```python
def clear_reference_cache(self):
    """清除引用表缓存"""
    self.reference_cache.clear()
    logger.info("Reference cache cleared")
```

**功能:**
- 清除引用表缓存

#### `clear_all_caches`

```python
def clear_all_caches(self):
    """清除所有缓存"""
    self.reference_cache.clear()
    self.record_cache.clear()
    self.index_query_cache.clear()
    self.range_query_cache.clear()
    logger.info("All caches cleared")
```

**功能:**
- 清除所有缓存，包括引用表缓存、记录缓存和查询缓存

#### `get_cache_stats`

```python
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
```

**功能:**
- 获取所有缓存的统计信息，包括命中率、大小等

### 维护方法

#### `cleanup_unused_references`

```python
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
```

**功能:**
- 清理未被任何记录引用的引用表条目
- 优化数据库存储空间
- 清除引用表缓存

## 性能优化策略

1. **多级缓存系统:**
   - 记录缓存: 减少数据库查询
   - 查询结果缓存: 避免重复执行昂贵的加密比较操作
   - 引用表缓存: 加速引用表查找

2. **批处理操作:**
   - 批量添加记录
   - 批量更新记录
   - 批量删除记录

3. **数据去重:**
   - 使用引用表避免存储重复的加密数据
   - 使用 xxHash 算法高效计算哈希值

4. **性能监控:**
   - 使用 `timing_decorator` 记录关键操作的执行时间
   - 记录缓存命中率和统计信息

## 安全考虑

1. **加密数据处理:**
   - 所有敏感数据以加密形式存储
   - 支持同态加密进行加密状态下的比较操作

2. **事务管理:**
   - 所有数据库操作使用事务包装
   - 发生错误时自动回滚，确保数据一致性

3. **异常处理:**
   - 捕获并记录所有数据库异常
   - 提供详细的错误日志

## 使用示例

```python
# 创建数据库管理器
db_manager = DatabaseManager("sqlite:///encrypted_db.sqlite", cache_size=2000)

# 添加加密记录
encrypted_index = fhe_manager.encrypt(42)
encrypted_data = aes_encrypt("sensitive data", key)
record_id = db_manager.add_encrypted_record(encrypted_index, encrypted_data)

# 查询记录
records = db_manager.search_by_encrypted_index(fhe_manager, 42)

# 范围查询
records = db_manager.search_by_range(fhe_manager, min_value=10, max_value=50)

# 更新记录
new_data = aes_encrypt("updated data", key)
db_manager.update_record(record_id, new_data)

# 删除记录
db_manager.delete_record(record_id)

# 获取缓存统计
stats = db_manager.get_cache_stats()
print(f"Record cache hit rate: {stats['record_cache']['hit_rate']:.2%}")
```