"""
项目配置文件
"""

import os

# 数据库配置
DB_CONFIG = {
    "username": "username",
    "password": "password",
    "host": "localhost",
    "port": "114514",
    "database": "test",
}

DB_CONNECTION_STRING = f"postgresql://{DB_CONFIG['username']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# 加密配置
ENCRYPTION_CONFIG = {
    # FHE配置
    "fhe": {
        "scheme": "BFV",  # 同态加密方案
        "poly_modulus_degree": 2**13,  # 多项式模数度
        "plain_modulus": 65537,  # 明文模数
    },
    # AES配置
    "aes": {
        "key_size": 16,  # AES-128 (16字节)
        "mode": "CBC",  # 加密模式
        "padding": "PKCS7",  # 填充方式
    },
}

# 密钥管理配置
KEY_MANAGEMENT = {
    "keys_dir": os.path.expanduser("~/.SecureDBKeys"),  # 密钥存储目录
    "context_file": "context.con",
    "public_key_file": "public.key",
    "private_key_file": "secret.key",
    "relin_key_file": "relin.key",
    "aes_key_file": "aes.key",
}

# 日志配置
LOG_CONFIG = {"log_file": "secure_db.log", "level": "INFO"}
