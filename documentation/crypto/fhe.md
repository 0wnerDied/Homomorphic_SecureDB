# 同态加密模块

## 概述

`FHEManager`类实现了基于SEAL-Python库的同态加密功能，采用BFV (Brakerski/Fan-Vercauteren) 方案。同态加密允许在加密数据上直接执行计算操作，而无需先解密，从而在保护数据隐私的同时支持数据分析和查询。

## 特性

- **整数加密**：支持单个整数和批量整数的加密与解密
- **字符串加密**：支持字符串的加密与解密
- **完全同态比较**：支持加密状态下的等值比较、大小比较和范围查询，无需解密中间结果
- **范围查询支持**：通过位加密结合同态操作实现高效的范围查询
- **缓存机制**：内置缓存系统提高重复操作的性能
- **密钥管理**：支持密钥的生成、保存和加载
- **加密模式**：支持仅加密模式，适用于不需要解密功能的场景

## 初始化

```python
def __init__(
    self,
    config: Dict[str, Any],
    key_manager: KeyManager,
    encrypt_only: bool = False,
):
    """
    初始化同态加密管理器

    Args:
        config: 配置字典, 包含scheme, poly_modulus_degree, plain_modulus等参数
        key_manager: 密钥管理器实例
        encrypt_only: 是否仅用于加密 (不需要私钥) 
    """
```

## 主要方法

### 整数加密与解密

```python
def encrypt_int(self, value: int) -> bytes:
    """
    加密整数值

    Args:
        value: 要加密的整数

    Returns:
        加密后的压缩字节数据
    """
```

```python
def decrypt_int(self, compressed_bytes: bytes) -> int:
    """
    解密整数值

    Args:
        compressed_bytes: 压缩的加密字节数据

    Returns:
        解密后的整数
    """
```

### 字符串加密与解密

```python
def encrypt_string(self, text: str) -> List[bytes]:
    """
    加密字符串

    Args:
        text: 要加密的字符串

    Returns:
        加密字符的字节列表
    """
```

```python
def decrypt_string(self, encrypted_chars: List[bytes]) -> str:
    """
    解密字符串

    Args:
        encrypted_chars: 加密字符的字节列表

    Returns:
        解密后的字符串
    """
```

### 批量操作

```python
def batch_encrypt_int(self, values: List[int]) -> List[bytes]:
    """
    批量加密整数值

    Args:
        values: 要加密的整数列表

    Returns:
        加密后的字节列表
    """
```

```python
def batch_decrypt_int(self, encrypted_values: List[bytes]) -> List[int]:
    """
    批量解密整数值

    Args:
        encrypted_values: 加密的字节列表

    Returns:
        解密后的整数列表
    """
```

### 完全同态比较操作

```python
def compare_encrypted(self, encrypted_bytes: bytes, query_value: int) -> bool:
    """
    比较加密索引与查询值是否相等

    Args:
        encrypted_bytes: 加密的索引字节数据
        query_value: 要比较的查询值

    Returns:
        如果相等返回True, 否则返回False
    """
```

### 范围查询支持

```python
def encrypt_for_range_query(self, value: int, bits: int = 32) -> List[bytes]:
    """
    为范围查询加密整数值

    Args:
        value: 要加密的整数
        bits: 位数, 默认32位

    Returns:
        加密后的位表示列表
    """
```

```python
def compare_less_than(
    self, encrypted_bits: List[bytes], query_value: int, bits: int = 32
) -> bool:
    """
    比较加密值是否小于查询值

    Args:
        encrypted_bits: 加密的位表示列表
        query_value: 要比较的查询值
        bits: 位数, 默认32位

    Returns:
        如果加密值小于查询值返回True, 否则返回False
    """
```

```python
def compare_greater_than(
    self, encrypted_bits: List[bytes], query_value: int, bits: int = 32
) -> bool:
    """
    比较加密值是否大于查询值

    Args:
        encrypted_bits: 加密的位表示列表
        query_value: 要比较的查询值
        bits: 位数, 默认32位

    Returns:
        如果加密值大于查询值返回True, 否则返回False
    """
```

```python
def compare_range(
    self,
    encrypted_bits: List[bytes],
    min_value: int = None,
    max_value: int = None,
    bits: int = 32,
) -> bool:
    """
    比较加密值是否在指定范围内

    Args:
        encrypted_bits: 加密的位表示列表
        min_value: 范围最小值, 如果为None则不检查下限
        max_value: 范围最大值, 如果为None则不检查上限
        bits: 位数, 默认32位

    Returns:
        如果加密值在范围内返回True, 否则返回False
    """
```

### 缓存管理

```python
def clear_cache(self):
    """清除缓存"""
```

## 密钥管理

```python
def _save_keys(self):
    """保存FHE上下文和密钥"""
```

```python
def _load_keys(self):
    """加载FHE上下文和密钥"""
```

## 使用示例

### 基本加密解密

```python
# 初始化配置
config = {
    "poly_modulus_degree": 8192,
    "plain_modulus": 1032193,
    "coeff_modulus_bits": [60, 40, 40, 60],
    "context_file": "params.bin",
    "public_key_file": "public.key",
    "private_key_file": "secret.key",
    "relin_key_file": "relin.key"
}

# 初始化密钥管理器和FHE管理器
key_manager = KeyManager(key_dir="./keys")
fhe = FHEManager(config, key_manager)

# 加密整数
encrypted_value = fhe.encrypt_int(42)

# 解密整数
decrypted_value = fhe.decrypt_int(encrypted_value)
print(f"解密值: {decrypted_value}")  # 输出: 解密值: 42

# 加密字符串
encrypted_string = fhe.encrypt_string("Hello")

# 解密字符串
decrypted_string = fhe.decrypt_string(encrypted_string)
print(f"解密字符串: {decrypted_string}")  # 输出: 解密字符串: Hello
```

### 完全同态比较操作

```python
# 加密整数
encrypted_value = fhe.encrypt_int(42)

# 比较加密值与明文值是否相等
is_equal = fhe.compare_encrypted(encrypted_value, 42)
print(f"值相等: {is_equal}")  # 输出: 值相等: True

# 为范围查询加密整数
encrypted_bits = fhe.encrypt_for_range_query(42)

# 范围比较
in_range = fhe.compare_range(encrypted_bits, min_value=30, max_value=50)
print(f"在范围内: {in_range}")  # 输出: 在范围内: True
```

### 批量操作

```python
# 批量加密整数
values = [10, 20, 30, 40, 50]
encrypted_values = fhe.batch_encrypt_int(values)

# 批量解密整数
decrypted_values = fhe.batch_decrypt_int(encrypted_values)
print(f"解密值: {decrypted_values}")  # 输出: 解密值: [10, 20, 30, 40, 50]
```

## 技术细节

1. **加密方案**：使用BFV (Brakerski/Fan-Vercauteren) 同态加密方案
2. **多项式模度**：默认使用8192的多项式模度，提供足够的安全性和性能
3. **批处理编码**：使用`BatchEncoder`替代已弃用的`IntegerEncoder`，提高效率
4. **完全同态比较**：使用平方差值法实现完全同态比较，无需解密中间结果
5. **范围查询实现**：通过位加密结合同态操作实现范围查询，保护中间结果
6. **缓存机制**：使用字典实现缓存，减少重复计算
7. **自定义系数模数**：支持自定义系数模数位数，为同态操作提供足够深度

## 安全注意事项

1. **参数选择**：多项式模度和系数模数的选择会影响安全性和性能，应根据实际需求调整
2. **密钥管理**：同态加密的私钥必须妥善保管，泄露将导致所有加密数据的安全性受损
3. **零信任实现**：比较操作采用完全同态实现，中间结果不会被解密，提高安全性
4. **加密模式**：在不需要解密功能的环境中，使用`encrypt_only=True`可以提高安全性
