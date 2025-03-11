"""
项目配置文件
"""

import os

# 数据库配置
"""DB_CONFIG = {
    "username": "username",
    "password": "password",
    "host": "localhost",
    "port": "114514",
    "database": "test",
}"""
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "username": "privacy_db_test",
    "password": "privacy_test_pwd",
    "database": "aviation_privacy_test",
    "admin_user": "0wnerd1ed",  # 使用标准的PostgreSQL管理员用户
    "admin_password": "",
}
# 支持环境变量覆盖数据库配置
DB_CONFIG.update(
    {
        "username": os.environ.get("SECURE_DB_USERNAME", DB_CONFIG["username"]),
        "password": os.environ.get("SECURE_DB_PASSWORD", DB_CONFIG["password"]),
        "host": os.environ.get("SECURE_DB_HOST", DB_CONFIG["host"]),
        "port": os.environ.get("SECURE_DB_PORT", DB_CONFIG["port"]),
        "database": os.environ.get("SECURE_DB_NAME", DB_CONFIG["database"]),
    }
)

DB_CONNECTION_STRING = f"postgresql://{DB_CONFIG['username']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# 加密配置
ENCRYPTION_CONFIG = {
    # FHE配置
    "fhe": {
        "scheme": "BFV",  # 同态加密方案
        "poly_modulus_degree": 2**13,  # 多项式模数度
        "plain_modulus": 1032193,  # 明文模数 (优化后的值)
        "coeff_modulus_bits": [60, 40, 40, 60],  # 系数模数位数
        "scale": 2**40,  # 缩放因子
    },
    # AES配置
    "aes": {
        "key_size": 32,  # AES-256 (32字节)
        "mode": "GCM",  # 加密模式 (改为GCM提供认证加密)
        "nonce_size": 12,  # GCM模式的IV/Nonce大小
        "tag_size": 16,  # GCM认证标签大小
    },
}

# 密钥管理配置
KEY_MANAGEMENT = {
    "keys_dir": os.environ.get(
        "SECURE_DB_KEYS_DIR", os.path.expanduser("~/.SecureDBKeys")
    ),  # 密钥存储目录
    "context_file": "context.con",
    "public_key_file": "public.key",
    "private_key_file": "secret.key",
    "relin_key_file": "relin.key",
    "galois_key_file": "galois.key",  # 添加Galois密钥支持
    "aes_key_file": "aes.key",
    "backup_dir": os.path.join(
        os.path.expanduser("~/.SecureDBKeys"), "backups"
    ),  # 备份目录
    "key_rotation_days": 90,  # 密钥轮换周期 (天)
    "pbkdf2_iterations": 1000000,  # PBKDF2迭代次数
}

# 日志配置
LOG_CONFIG = {
    "log_file": os.environ.get("SECURE_DB_LOG_FILE", "secure_db.log"),
    "level": os.environ.get("SECURE_DB_LOG_LEVEL", "INFO"),
    "max_size": 10 * 1024 * 1024,  # 最大日志文件大小 (10MB)
    "backup_count": 5,  # 保留的日志文件数量
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "cache_size": int(os.environ.get("SECURE_DB_CACHE_SIZE", "1000")),  # 缓存项数量
    "batch_size": int(os.environ.get("SECURE_DB_BATCH_SIZE", "100")),  # 批处理大小
    "compression_level": int(
        os.environ.get("SECURE_DB_COMPRESSION_LEVEL", "9")
    ),  # zstd压缩级别
    "parallel_threads": int(os.environ.get("SECURE_DB_THREADS", "4")),  # 并行处理线程数
    "query_timeout": int(
        os.environ.get("SECURE_DB_QUERY_TIMEOUT", "30")
    ),  # 查询超时时间(秒)
}

# 安全审计配置
AUDIT_CONFIG = {
    "enabled": True,
    "audit_log_file": os.environ.get("SECURE_DB_AUDIT_LOG", "audit.log"),
    "log_queries": True,
    "log_data_access": True,
    "log_key_operations": True,
}

# 系统限制配置
LIMITS_CONFIG = {
    "max_records_per_query": 1000,  # 单次查询最大记录数
    "max_batch_operations": 500,  # 最大批处理操作数
    "max_data_size": 10 * 1024 * 1024,  # 最大数据大小 (10MB)
}
