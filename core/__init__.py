"""
SecureDB - 基于同态加密和AES的安全数据库系统

此项目提供了一个使用全同态加密(FHE)进行索引和AES进行数据加密的安全数据库实现。
主要功能包括: 
- 使用同态加密进行安全索引和查询
- AES加密保护数据内容
- 支持范围查询
- 批量操作支持
- 数据导入导出功能

主要模块: 
- crypto: 提供加密功能(AES, FHE)
- database: 数据库操作和模型
- utils: 工具函数和辅助类
"""

# 导入主程序
from .secure_db import SecureDB

# 导入工具类
from .utils import (
    LRUCache,
    DataCompressor,
    timing_decorator,
    retry_decorator,
    hash_data,
    hash_file,
    SafeFileHandler,
    ProgressTracker,
)

# 导入配置
from .config import (
    DB_CONNECTION_STRING,
    ENCRYPTION_CONFIG,
    KEY_MANAGEMENT,
    LOG_CONFIG,
    PERFORMANCE_CONFIG,
    AUDIT_CONFIG,
    LIMITS_CONFIG,
)

# 版本信息
__version__ = "0.1.0-beta"

# 导出主要类和函数
__all__ = [
    # 主程序
    "SecureDB",
    # 工具类
    "LRUCache",
    "DataCompressor",
    "timing_decorator",
    "retry_decorator",
    "hash_data",
    "hash_file",
    "SafeFileHandler",
    "ProgressTracker",
    # 配置常量
    "DB_CONNECTION_STRING",
    "ENCRYPTION_CONFIG",
    "KEY_MANAGEMENT",
    "LOG_CONFIG",
    "PERFORMANCE_CONFIG",
    "AUDIT_CONFIG",
    "LIMITS_CONFIG",
]
