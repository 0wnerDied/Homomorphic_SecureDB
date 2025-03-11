# AES 加密模块

## 概述

`AESManager`类提供了基于AES-GCM (Galois/Counter Mode) 的加密和解密功能。AES-GCM是一种高效的认证加密模式，同时提供数据机密性和完整性保护。

## 特性

- **AES-GCM加密**：提供认证加密，确保数据完整性和机密性
- **灵活的输入格式**：支持字符串或字节类型的输入数据
- **批量处理**：支持批量加密和解密操作
- **安全的随机IV**：每次加密使用随机初始化向量，增强安全性
- **内置认证**：使用GCM模式的认证标签验证数据完整性

## 初始化

```python
def __init__(self, key: Optional[bytes] = None, key_size: int = 32):
    """
    初始化AES加密管理器

    Args:
        key: 可选的AES密钥, 如果未提供则生成新密钥
        key_size: 密钥大小(字节), 默认为32 (256位) 
    """
```

## 主要方法

### 加密数据

```python
def encrypt(self, data: Union[str, bytes]) -> bytes:
    """
    加密数据

    Args:
        data: 要加密的数据, 可以是字符串或字节

    Returns:
        加密后的字节数据 (包含IV和认证标签) 
    """
```

加密后的数据格式为：`IV (12字节) + 标签 (16字节) + 密文`

### 解密数据

```python
def decrypt(self, encrypted_data: bytes) -> bytes:
    """
    解密数据

    Args:
        encrypted_data: 加密后的字节数据 (包含IV和认证标签) 

    Returns:
        解密后的字节数据
    """
```

### 获取密钥

```python
def get_key(self) -> bytes:
    """
    获取AES密钥

    Returns:
        AES密钥字节
    """
```

### 批量加密

```python
def encrypt_batch(self, data_list: list[Union[str, bytes]]) -> list[bytes]:
    """
    批量加密数据

    Args:
        data_list: 要加密的数据列表

    Returns:
        加密后的字节数据列表
    """
```

### 批量解密

```python
def decrypt_batch(self, encrypted_data_list: list[bytes]) -> list[bytes]:
    """
    批量解密数据

    Args:
        encrypted_data_list: 加密后的字节数据列表

    Returns:
        解密后的字节数据列表
    """
```

## 使用示例

```python
# 初始化AES管理器（自动生成密钥）
aes_manager = AESManager()

# 使用指定密钥初始化
import os
custom_key = os.urandom(32)  # 生成256位密钥
aes_manager = AESManager(key=custom_key)

# 加密字符串数据
sensitive_data = "这是一条敏感信息"
encrypted = aes_manager.encrypt(sensitive_data)

# 解密数据
decrypted_bytes = aes_manager.decrypt(encrypted)
decrypted_text = decrypted_bytes.decode("utf-8")
print(decrypted_text)  # 输出: 这是一条敏感信息

# 批量加密
data_list = ["数据1", "数据2", "数据3"]
encrypted_list = aes_manager.encrypt_batch(data_list)

# 批量解密
decrypted_list = aes_manager.decrypt_batch(encrypted_list)
decrypted_texts = [d.decode("utf-8") for d in decrypted_list]
```

## 技术细节

1. **加密模式**：使用AES-GCM (Galois/Counter Mode)，这是一种AEAD (Authenticated Encryption with Associated Data) 模式
2. **密钥长度**：默认使用256位 (32字节) 密钥，提供最高级别的AES安全性
3. **IV长度**：使用12字节 (96位) 的初始化向量，符合GCM模式的最佳实践
4. **认证标签**：使用16字节的认证标签，用于验证数据完整性

## 安全注意事项

1. **密钥管理**：密钥是加密系统的核心，应妥善保管，避免泄露
2. **密钥备份**：确保密钥有安全的备份机制，否则加密数据将无法恢复
3. **错误处理**：解密失败通常表示数据被篡改或使用了错误的密钥
4. **随机性**：该实现使用`Crypto.Random.get_random_bytes`确保IV的随机性
