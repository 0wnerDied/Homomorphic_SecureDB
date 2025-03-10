"""
数据库模型定义
"""

from sqlalchemy import Column, Integer, LargeBinary, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()


class EncryptedRecord(Base):
    """加密记录模型"""

    __tablename__ = "encrypted_records"

    id = Column(Integer, primary_key=True)
    encrypted_index = Column(LargeBinary, nullable=False, index=True)  # BFV加密的索引
    encrypted_data = Column(LargeBinary, nullable=False)  # AES加密的数据（包含IV）
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


class ReferenceTable(Base):
    """引用表模型 - 用于存储重复的加密数据"""

    __tablename__ = "reference_table"

    id = Column(Integer, primary_key=True)
    hash_value = Column(String(64), unique=True, nullable=False, index=True)
    encrypted_data = Column(LargeBinary, nullable=False)

    def __repr__(self):
        return f"<ReferenceTable(id={self.id})>"


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


def init_db(engine):
    """
    初始化数据库表

    Args:
        engine: SQLAlchemy引擎
    """
    Base.metadata.create_all(engine)
