"""
数据库模型定义
"""

from sqlalchemy import Column, Integer, LargeBinary, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class EncryptedRecord(Base):
    """加密记录模型"""

    __tablename__ = "encrypted_records"

    id = Column(Integer, primary_key=True)
    encrypted_index = Column(LargeBinary, nullable=False, index=True)  # BFV加密的索引
    encrypted_data = Column(LargeBinary, nullable=False)  # AES加密的数据（包含IV）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

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


def init_db(engine):
    """
    初始化数据库表

    Args:
        engine: SQLAlchemy引擎
    """
    Base.metadata.create_all(engine)
