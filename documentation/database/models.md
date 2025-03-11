# 数据库模型

## 概述

`models.py` 定义了安全数据库系统的核心数据模型，使用 SQLAlchemy ORM 框架实现。该模块设计了三个主要模型，用于存储加密数据、引用表和范围查询索引，支持同态加密和高效的数据检索操作。

## 基础设置

```python
from sqlalchemy import Column, Integer, LargeBinary, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()
```

模块使用 SQLAlchemy 的声明式基类 `Base` 作为所有模型的基类，提供了 ORM 功能。

## 数据模型

### `EncryptedRecord` 模型

```python
class EncryptedRecord(Base):
    """加密记录模型"""

    __tablename__ = "encrypted_records"

    id = Column(Integer, primary_key=True)
    encrypted_index = Column(LargeBinary, nullable=False, index=True)  # BFV加密的索引
    encrypted_data = Column(LargeBinary, nullable=False)  # AES加密的数据 (包含IV) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # 关系
    range_indices = relationship(
        "RangeQueryIndex", back_populates="record", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<EncryptedRecord(id={self.id})>"
```

**功能:**
- 存储加密的用户数据记录
- 使用 BFV 同态加密方案加密索引值，支持加密状态下的相等性比较
- 使用 AES 加密存储实际数据内容，包含初始化向量 (IV)
- 自动跟踪记录创建和更新时间
- 与 `RangeQueryIndex` 模型建立一对多关系，支持级联删除

**字段:**
- `id`: 整数，主键，自动递增
- `encrypted_index`: 二进制大对象，BFV 加密的索引值，创建了索引以加速查询
- `encrypted_data`: 二进制大对象，AES 加密的数据内容
- `created_at`: 日期时间，记录创建时间，自动设置为当前 UTC 时间
- `updated_at`: 日期时间，记录更新时间，自动更新

### `ReferenceTable` 模型

```python
class ReferenceTable(Base):
    """引用表模型 - 用于存储重复的加密数据"""

    __tablename__ = "reference_table"

    id = Column(Integer, primary_key=True)
    hash_value = Column(String(64), unique=True, nullable=False, index=True)
    encrypted_data = Column(LargeBinary, nullable=False)

    def __repr__(self):
        return f"<ReferenceTable(id={self.id})>"
```

**功能:**
- 实现数据去重机制，避免存储相同的加密数据多次
- 使用哈希值作为查找键，提高查询效率
- 减少数据库存储空间需求

**字段:**
- `id`: 整数，主键，自动递增
- `hash_value`: 字符串(64)，加密数据的哈希值，唯一索引
- `encrypted_data`: 二进制大对象，AES 加密的数据内容

### `RangeQueryIndex` 模型

```python
class RangeQueryIndex(Base):
    """范围查询索引模型 - 用于存储加密索引的位表示"""

    __tablename__ = "range_query_indices"

    id = Column(Integer, primary_key=True)
    record_id = Column(
        Integer, ForeignKey("encrypted_records.id"), nullable=False, index=True
    )
    bit_position = Column(Integer, nullable=False)  # 位位置
    encrypted_bit = Column(LargeBinary, nullable=False)  # 加密的位值

    # 关系
    record = relationship("EncryptedRecord", back_populates="range_indices")

    def __repr__(self):
        return f"<RangeQueryIndex(record_id={self.record_id}, bit_position={self.bit_position})>"
```

**功能:**
- 支持加密状态下的范围查询操作
- 使用位表示法存储索引值的二进制表示
- 每个位位置单独加密，允许在加密状态下进行比较操作

**字段:**
- `id`: 整数，主键，自动递增
- `record_id`: 整数，外键，关联到 `EncryptedRecord` 表的 `id` 字段
- `bit_position`: 整数，表示索引值二进制表示中的位位置
- `encrypted_bit`: 二进制大对象，BFV 加密的位值（0 或 1）

**关系:**
- `record`: 与 `EncryptedRecord` 模型的多对一关系

## 数据库初始化

```python
def init_db(engine):
    """
    初始化数据库表

    Args:
        engine: SQLAlchemy引擎
    """
    Base.metadata.create_all(engine)
```

**功能:**
- 根据定义的模型创建数据库表
- 如果表已存在，则不会重新创建

## 数据流程

1. **记录创建流程:**
   - 使用 BFV 同态加密方案加密索引值
   - 使用 AES 加密数据内容
   - 计算加密数据的哈希值，检查是否已存在于引用表中
   - 如果启用范围查询，将索引值转换为二进制表示，并为每个位创建 `RangeQueryIndex` 记录
   - 存储加密的索引和数据（或引用）到 `EncryptedRecord` 表

2. **查询流程:**
   - **精确查询:** 在加密状态下比较 `encrypted_index` 字段
   - **范围查询:** 使用 `RangeQueryIndex` 表中的位表示进行比较

3. **数据更新流程:**
   - 更新加密数据或引用
   - 自动更新 `updated_at` 时间戳

## 设计考虑

1. **安全性:**
   - 索引和数据均以加密形式存储
   - 使用同态加密支持加密状态下的计算
   - 不存储任何明文敏感信息

2. **性能优化:**
   - 为频繁查询的字段创建索引
   - 使用引用表减少重复数据存储
   - 自动跟踪时间戳便于审计和缓存失效

3. **可扩展性:**
   - 模型设计支持未来添加更多功能
   - 关系定义支持复杂查询和数据完整性

## 使用示例

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import init_db, EncryptedRecord

# 创建数据库引擎
engine = create_engine('sqlite:///secure_db.sqlite')

# 初始化数据库
init_db(engine)

# 创建会话
Session = sessionmaker(bind=engine)
session = Session()

# 创建加密记录
encrypted_record = EncryptedRecord(
    encrypted_index=bfv_encrypted_index,
    encrypted_data=aes_encrypted_data
)
session.add(encrypted_record)
session.commit()

# 查询记录
records = session.query(EncryptedRecord).all()
for record in records:
    print(record.id, record.created_at)
```

## 技术细节

1. **BFV 加密:**
   - 用于索引值和范围查询位值的加密
   - 支持加密状态下的相等性比较和有限的算术运算

2. **AES 加密:**
   - 用于数据内容的加密
   - 提供高效的加密和解密操作
   - 每条记录使用唯一的初始化向量 (IV)

3. **范围查询实现:**
   - 将整数索引值转换为二进制表示
   - 对每个位单独加密，存储在 `RangeQueryIndex` 表中
   - 范围查询通过比较位表示进行，支持 >, <, >=, <= 操作

4. **数据去重机制:**
   - 计算加密数据的哈希值
   - 在 `ReferenceTable` 中查找哈希值
   - 如果存在，使用引用而不是重复存储数据

## 性能考虑

- `encrypted_index` 和 `hash_value` 字段创建了索引，提高查询性能
- `record_id` 字段创建了索引，加速关联查询
- 使用级联删除确保数据完整性并简化删除操作
- 数据去重机制减少存储需求，特别是对于重复数据
