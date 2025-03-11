# 密钥管理模块

## 概述

`KeyManager`类提供了全面的密钥管理功能，负责处理FHE（全同态加密）和AES密钥的生成、存储、加载和备份。该模块实现了安全的密钥存储机制，支持密码保护和数据压缩，确保密钥在存储和传输过程中的安全性和效率。

## 特性

- **安全密钥存储**：支持AES加密保护敏感密钥
- **密码派生**：使用PBKDF2算法从用户密码安全派生加密密钥
- **数据压缩**：使用Zstandard高效压缩算法减少密钥存储空间
- **密钥轮换**：支持FHE密钥对的安全轮换，自动备份旧密钥
- **备份与恢复**：提供完整的密钥备份和恢复机制
- **灵活的文件管理**：统一的文件路径处理和异常管理

## 初始化

```python
def __init__(self, keys_dir: str):
    """
    初始化密钥管理器

    Args:
        keys_dir: 密钥存储目录
    """
```

## 基本文件操作

### 获取密钥路径

```python
def get_key_path(self, filename: str) -> str:
    """
    获取密钥文件的完整路径

    Args:
        filename: 密钥文件名

    Returns:
        密钥文件的完整路径
    """
```

### 保存文件

```python
def save_file(self, data: bytes, filename: str) -> None:
    """
    保存数据到文件

    Args:
        data: 要保存的数据
        filename: 文件名
    """
```

### 加载文件

```python
def load_file(self, filename: str) -> bytes:
    """
    从文件加载数据

    Args:
        filename: 文件名

    Returns:
        加载的数据
    """
```

## AES密钥管理

### 加密AES密钥

```python
def encrypt_aes_key(self, aes_key: bytes, password: str) -> Tuple[bytes, bytes]:
    """
    使用密码加密AES密钥

    Args:
        aes_key: 要加密的AES密钥
        password: 用于加密的密码

    Returns:
        (encrypted_key, salt) 元组
    """
```

### 解密AES密钥

```python
def decrypt_aes_key(self, encrypted_data: bytes, salt: bytes, password: str) -> bytes:
    """
    使用密码解密AES密钥

    Args:
        encrypted_data: 加密的数据 (IV + 加密密钥) 
        salt: 用于密码派生的盐
        password: 用于解密的密码

    Returns:
        解密的AES密钥
    """
```

### 保存AES密钥

```python
def save_aes_key(self, aes_key: bytes, key_file: str, password: str) -> None:
    """
    加密并保存AES密钥到文件

    Args:
        aes_key: 要保存的AES密钥
        key_file: 密钥文件名
        password: 用于加密的密码
    """
```

### 加载AES密钥

```python
def load_aes_key(self, key_file: str, password: str) -> bytes:
    """
    从文件加载并解密AES密钥

    Args:
        key_file: 密钥文件名
        password: 用于解密的密码

    Returns:
        解密的AES密钥
    """
```

## FHE密钥管理

### 保存FHE密钥对

```python
def save_fhe_keys(
    self,
    public_key: bytes,
    secret_key: bytes,
    public_key_file: str,
    secret_key_file: str,
    password: Optional[str] = None,
) -> None:
    """
    保存FHE密钥对

    Args:
        public_key: 公钥数据
        secret_key: 私钥数据
        public_key_file: 公钥文件名
        secret_key_file: 私钥文件名
        password: 如果提供, 将使用此密码加密私钥
    """
```

### 加载FHE公钥

```python
def load_fhe_public_key(self, public_key_file: str) -> bytes:
    """
    加载FHE公钥

    Args:
        public_key_file: 公钥文件名

    Returns:
        解压缩后的公钥数据
    """
```

### 加载FHE私钥

```python
def load_fhe_secret_key(self, secret_key_file: str, password: Optional[str] = None) -> bytes:
    """
    加载FHE私钥

    Args:
        secret_key_file: 私钥文件名
        password: 如果私钥已加密, 需提供密码

    Returns:
        解压缩后的私钥数据
    """
```

### 轮换FHE密钥对

```python
def rotate_fhe_keys(
    self,
    old_public_key_file: str,
    old_secret_key_file: str,
    new_public_key: bytes,
    new_secret_key: bytes,
    new_public_key_file: str,
    new_secret_key_file: str,
    password: Optional[str] = None,
) -> None:
    """
    轮换FHE密钥对 (保存新密钥并备份旧密钥) 

    Args:
        old_public_key_file: 旧公钥文件名
        old_secret_key_file: 旧私钥文件名
        new_public_key: 新公钥数据
        new_secret_key: 新私钥数据
        new_public_key_file: 新公钥文件名
        new_secret_key_file: 新私钥文件名
        password: 如果提供, 将使用此密码加密新私钥
    """
```

## 数据压缩

### 压缩数据

```python
def compress_data(self, data: bytes) -> bytes:
    """
    压缩数据

    Args:
        data: 要压缩的数据

    Returns:
        压缩后的数据
    """
```

### 解压缩数据

```python
def decompress_data(self, compressed_data: bytes) -> bytes:
    """
    解压缩数据

    Args:
        compressed_data: 要解压的数据

    Returns:
        解压后的数据
    """
```

## 备份与恢复

### 生成备份

```python
def generate_backup(self, backup_dir: Optional[str] = None) -> str:
    """
    生成密钥备份

    Args:
        backup_dir: 备份目录, 如果为None则使用默认目录

    Returns:
        备份文件路径
    """
```

### 恢复备份

```python
def restore_backup(self, backup_file: str, password: Optional[str] = None) -> None:
    """
    从备份恢复密钥

    Args:
        backup_file: 备份文件路径
        password: 如果提供, 将验证密钥是否可以使用此密码解密
    """
```

## 使用示例

### 基本初始化

```python
# 初始化密钥管理器
key_manager = KeyManager(keys_dir="./keys")
```

### AES密钥管理

```python
# 创建AES密钥
from Crypto.Random import get_random_bytes
aes_key = get_random_bytes(32)  # 256位密钥

# 设置密码保护
password = "secure_password"

# 保存AES密钥
key_manager.save_aes_key(aes_key, "my_aes.key", password)

# 加载AES密钥
loaded_aes_key = key_manager.load_aes_key("my_aes.key", password)
```

### FHE密钥管理

```python
# 假设我们有FHE密钥对
public_key = b"..."  # 公钥数据
secret_key = b"..."  # 私钥数据

# 保存FHE密钥对 (私钥使用密码保护)
key_manager.save_fhe_keys(
    public_key,
    secret_key,
    "fhe_public.key",
    "fhe_secret.key",
    password="secure_password"
)

# 加载FHE公钥 (不需要密码)
loaded_public_key = key_manager.load_fhe_public_key("fhe_public.key")

# 加载FHE私钥 (需要密码)
loaded_secret_key = key_manager.load_fhe_secret_key("fhe_secret.key", password="secure_password")
```

### 密钥轮换

```python
# 假设我们有新的FHE密钥对
new_public_key = b"..."  # 新公钥数据
new_secret_key = b"..."  # 新私钥数据

# 轮换密钥 (备份旧密钥并保存新密钥)
key_manager.rotate_fhe_keys(
    "fhe_public.key",
    "fhe_secret.key",
    new_public_key,
    new_secret_key,
    "fhe_public.key",  # 使用相同的文件名
    "fhe_secret.key",  # 使用相同的文件名
    password="secure_password"
)
```

### 备份与恢复

```python
# 生成密钥备份
backup_file = key_manager.generate_backup()
print(f"Backup created: {backup_file}")

# 恢复备份 (可选验证密码)
key_manager.restore_backup(backup_file, password="secure_password")
```

### 数据压缩

```python
# 压缩大型数据
large_data = b"..." * 1000
compressed = key_manager.compress_data(large_data)

# 解压缩数据
original = key_manager.decompress_data(compressed)
```

## 技术细节

1. **密码派生**：使用PBKDF2算法从用户密码派生加密密钥，使用SHA-256哈希函数和10万次迭代，提供强大的抗暴力破解能力
2. **AES加密**：使用AES-CBC模式加密敏感密钥，提供高强度的保密性
3. **数据压缩**：采用Zstandard压缩算法，压缩级别为9（最高压缩率），显著减少存储空间
4. **备份格式**：使用tar.gz格式创建备份，确保完整性和兼容性
5. **密钥轮换**：自动为旧密钥创建带时间戳的备份，确保安全轮换

## 安全注意事项

1. **密码强度**：用于保护密钥的密码应当足够强，建议使用高熵值的长密码
2. **备份安全**：密钥备份文件应当存储在安全的位置，避免未授权访问
3. **密钥目录权限**：确保密钥目录具有适当的文件系统权限，限制访问
4. **密码管理**：安全存储用于解密密钥的密码，密码丢失将导致加密数据无法恢复
5. **轮换策略**：定期轮换密钥以提高系统安全性，特别是在可能存在密钥泄露的情况下
