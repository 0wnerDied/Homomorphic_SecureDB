"""
测试数据库初始化脚本 - 创建必要的表和索引
"""

import sys
import logging
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, LargeBinary, DateTime, func, ForeignKey
from test_config import TEST_DB_CONNECTION_STRING

logger = logging.getLogger("测试数据库初始化")

def init_test_database():
    """初始化测试数据库，创建必要的表和索引"""
    try:
        logger.info("开始初始化测试数据库...")
        
        # 创建数据库引擎
        engine = create_engine(f"postgresql://{TEST_DB_CONNECTION_STRING}")
        metadata = MetaData()
        
        # 定义表结构
        encrypted_records = Table(
            'encrypted_records', 
            metadata,
            Column('id', Integer, primary_key=True),
            Column('encrypted_index', LargeBinary, nullable=False),
            Column('encrypted_data', LargeBinary, nullable=False),
            Column('created_at', DateTime, server_default=func.now()),
            Column('updated_at', DateTime, onupdate=func.now())
        )
        
        range_query_indices = Table(
            'range_query_indices', 
            metadata,
            Column('id', Integer, primary_key=True),
            Column('record_id', Integer, ForeignKey('encrypted_records.id', ondelete='CASCADE'), nullable=False),
            Column('bit_position', Integer, nullable=False),
            Column('encrypted_bit', LargeBinary, nullable=False)
        )
        
        # 创建表
        logger.info("创建表...")
        metadata.create_all(engine)
        
        # 创建索引
        logger.info("创建索引...")
        with engine.connect() as connection:
            # 为range_query_indices表创建索引
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_range_query_record_id ON range_query_indices (record_id);"
            ))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_range_query_bit_position ON range_query_indices (bit_position);"
            ))
            
            # 提交事务
            connection.commit()
        
        logger.info("测试数据库初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"测试数据库初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = init_test_database()
    sys.exit(0 if success else 1)
