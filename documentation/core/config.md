# 配置文件

## 概述

`config.py` 是项目的核心配置文件，提供了数据库连接、加密、密钥管理、日志记录、性能优化、安全审计和系统限制等方面的配置参数。该文件通过环境变量和默认值的组合方式提供灵活的配置选项。

## 配置项详解

### 数据库配置 (`DB_CONFIG`)

包含PostgreSQL数据库连接所需的所有参数：

- `host`: 数据库服务器地址，默认为 `localhost`
- `port`: 数据库端口，默认为 `5432`
- `username`: 数据库用户名，默认为 `privacy_db_test`
- `password`: 数据库密码，默认为 `privacy_test_pwd`
- `database`: 数据库名称，默认为 `aviation_privacy_test`
- `admin_user`: PostgreSQL管理员用户，默认为 `0wnerd1ed`
- `admin_password`: 管理员密码，默认为空

所有数据库连接参数均可通过环境变量覆盖：
- `SECURE_DB_USERNAME`
- `SECURE_DB_PASSWORD`
- `SECURE_DB_HOST`
- `SECURE_DB_PORT`
- `SECURE_DB_NAME`

### 数据库连接字符串 (`DB_CONNECTION_STRING`)

根据数据库配置自动生成的PostgreSQL连接字符串，格式为：
```
postgresql://username:password@host:port/database
```

### 加密配置 (`ENCRYPTION_CONFIG`)

包含两种加密方案的配置：

#### 全同态加密 (FHE)
- `scheme`: 同态加密方案，使用 `BFV`
- `poly_modulus_degree`: 多项式模数度，设置为 2^13
- `plain_modulus`: 明文模数，设置为 1032193
- `coeff_modulus_bits`: 系数模数位数，配置为 [60, 40, 40, 60]
- `scale`: 缩放因子，设置为 2^40

#### AES加密
- `key_size`: AES密钥大小，32字节 (AES-256)
- `mode`: 加密模式，使用 `GCM` 提供认证加密
- `nonce_size`: GCM模式的IV/Nonce大小，12字节
- `tag_size`: GCM认证标签大小，16字节

### 密钥管理配置 (`KEY_MANAGEMENT`)

管理加密密钥的存储和轮换：

- `keys_dir`: 密钥存储目录，默认为 `~/.SecureDBKeys`，可通过 `SECURE_DB_KEYS_DIR` 环境变量覆盖
- `context_file`: FHE上下文文件名，`context.con`
- `public_key_file`: 公钥文件名，`public.key`
- `private_key_file`: 私钥文件名，`secret.key`
- `relin_key_file`: 重线性化密钥文件名，`relin.key`
- `galois_key_file`: Galois密钥文件名，`galois.key`
- `aes_key_file`: AES密钥文件名，`aes.key`
- `backup_dir`: 密钥备份目录，默认为 `~/.SecureDBKeys/backups`
- `key_rotation_days`: 密钥轮换周期，90天
- `pbkdf2_iterations`: PBKDF2密钥派生函数迭代次数，1,000,000次

### 日志配置 (`LOG_CONFIG`)

系统日志记录配置：

- `log_file`: 日志文件路径，默认为 `secure_db.log`，可通过 `SECURE_DB_LOG_FILE` 环境变量覆盖
- `level`: 日志级别，默认为 `INFO`，可通过 `SECURE_DB_LOG_LEVEL` 环境变量覆盖
- `max_size`: 单个日志文件最大大小，10MB
- `backup_count`: 保留的日志文件数量，5个
- `log_format`: 日志格式，包含时间戳、模块名、日志级别和消息

### 性能优化配置 (`PERFORMANCE_CONFIG`)

系统性能相关参数：

- `cache_size`: 缓存项数量，默认为 1000，可通过 `SECURE_DB_CACHE_SIZE` 环境变量覆盖
- `batch_size`: 批处理大小，默认为 100，可通过 `SECURE_DB_BATCH_SIZE` 环境变量覆盖
- `compression_level`: zstd压缩级别，默认为 9，可通过 `SECURE_DB_COMPRESSION_LEVEL` 环境变量覆盖
- `parallel_threads`: 并行处理线程数，默认为 4，可通过 `SECURE_DB_THREADS` 环境变量覆盖
- `query_timeout`: 查询超时时间，默认为 30秒，可通过 `SECURE_DB_QUERY_TIMEOUT` 环境变量覆盖

### 安全审计配置 (`AUDIT_CONFIG`)

安全审计和日志记录：

- `enabled`: 是否启用审计功能，默认为 `True`
- `audit_log_file`: 审计日志文件路径，默认为 `audit.log`，可通过 `SECURE_DB_AUDIT_LOG` 环境变量覆盖
- `log_queries`: 是否记录查询操作，默认为 `True`
- `log_data_access`: 是否记录数据访问操作，默认为 `True`
- `log_key_operations`: 是否记录密钥操作，默认为 `True`

### 系统限制配置 (`LIMITS_CONFIG`)

系统资源使用限制：

- `max_records_per_query`: 单次查询最大记录数，1000条
- `max_batch_operations`: 最大批处理操作数，500个
- `max_data_size`: 最大数据大小，10MB

## 使用说明

1. 可通过环境变量覆盖大部分配置项
2. 敏感信息（如数据库密码）建议通过环境变量设置，而非硬编码
3. 密钥存储目录默认在用户主目录下，可根据安全需求调整
4. 性能参数可根据硬件资源和负载情况进行调优

## 注意事项

- 生产环境中应确保修改默认的测试数据库凭证
- 密钥轮换机制应定期执行以提高安全性
- 审计日志应定期备份和检查
- 系统限制参数应根据实际使用场景进行调整