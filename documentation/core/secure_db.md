# 安全数据库核心模块

## 概述

`secure_db.py` 是同态加密安全数据库系统的核心模块，提供了一个统一的接口来处理加密数据的存储、检索和操作。该模块整合了FHE（全同态加密）和AES加密技术，实现了对敏感数据的安全存储和查询，同时支持对加密数据进行计算操作。

## 类: `SecureDB`

### 初始化

```python
def __init__(self, load_keys: bool = False, encrypt_only: bool = False, cache_size: int = None)
```

**参数:**
- `load_keys`: 布尔值，指定是否从文件加载现有密钥
- `encrypt_only`: 布尔值，指定是否仅用于加密操作（不需要私钥）
- `cache_size`: 整数，指定缓存大小，如果为None则使用配置文件中的值

**功能:**
- 初始化密钥管理器、FHE管理器、数据库管理器和AES管理器
- 如果`load_keys=True`，尝试从文件加载AES密钥
- 如果加载失败或`load_keys=False`，创建新的AES密钥

### 核心方法

#### 密钥管理

```python
def _save_aes_key(self)
```

**功能:**
- 提示用户输入密码并确认
- 使用密钥管理器加密并保存AES密钥到文件

#### 缓存管理

```python
def get_cache_stats(self) -> Dict[str, Any]
```

**返回:**
- 包含缓存统计信息的字典

```python
def clear_caches(self) -> None
```

**功能:**
- 清除所有缓存

#### 记录操作

##### 添加记录

```python
def add_record(self, index_value: int, data: str, enable_range_query: bool = False) -> int
```

**参数:**
- `index_value`: 整数，索引值
- `data`: 字符串，要加密的数据
- `enable_range_query`: 布尔值，是否启用范围查询支持

**返回:**
- 新记录的ID

**功能:**
- 使用FHE加密索引值
- 如果启用范围查询，创建范围查询索引
- 使用AES加密数据
- 将加密后的数据添加到数据库

##### 批量添加记录

```python
def add_records_batch(self, records: List[Tuple[int, str, bool]]) -> List[int]
```

**参数:**
- `records`: 列表，每个元素为(index_value, data, enable_range_query)元组

**返回:**
- 新记录ID列表

**功能:**
- 批量加密和添加多条记录
- 提高批量操作效率

##### 获取记录

```python
def get_record(self, record_id: int) -> Optional[str]
```

**参数:**
- `record_id`: 整数，记录ID

**返回:**
- 解密后的数据，如果记录不存在则返回None

**功能:**
- 从数据库获取加密记录
- 使用AES解密数据

##### 批量获取记录

```python
def get_records_batch(self, record_ids: List[int]) -> Dict[int, Optional[str]]
```

**参数:**
- `record_ids`: 整数列表，记录ID列表

**返回:**
- 记录ID到解密数据的映射，如果记录不存在则值为None

**功能:**
- 批量获取和解密多条记录

#### 搜索功能

##### 按索引搜索

```python
def search_by_index(self, index_value: int) -> List[Dict[str, Any]]
```

**参数:**
- `index_value`: 整数，要搜索的索引值

**返回:**
- 匹配记录的列表，每个记录包含ID和解密后的数据

**功能:**
- 使用FHE技术在加密状态下进行索引匹配
- 解密匹配记录的数据

##### 范围搜索

```python
def search_by_range(self, min_value: int = None, max_value: int = None) -> List[Dict[str, Any]]
```

**参数:**
- `min_value`: 整数，范围最小值，如果为None则不检查下限
- `max_value`: 整数，范围最大值，如果为None则不检查上限

**返回:**
- 匹配记录的列表，每个记录包含ID和解密后的数据

**功能:**
- 使用FHE技术在加密状态下进行范围查询
- 解密匹配记录的数据

#### 更新操作

##### 更新记录

```python
def update_record(self, record_id: int, new_data: str) -> bool
```

**参数:**
- `record_id`: 整数，记录ID
- `new_data`: 字符串，新数据

**返回:**
- 布尔值，是否成功更新

**功能:**
- 加密新数据
- 更新数据库中的记录

##### 批量更新记录

```python
def update_records_batch(self, updates: List[Tuple[int, str]]) -> int
```

**参数:**
- `updates`: 列表，每个元素为(record_id, new_data)元组

**返回:**
- 整数，成功更新的记录数量

**功能:**
- 批量加密和更新多条记录

#### 删除操作

##### 删除记录

```python
def delete_record(self, record_id: int) -> bool
```

**参数:**
- `record_id`: 整数，记录ID

**返回:**
- 布尔值，是否成功删除

**功能:**
- 从数据库中删除指定记录

##### 批量删除记录

```python
def delete_records_batch(self, record_ids: List[int]) -> int
```

**参数:**
- `record_ids`: 整数列表，记录ID列表

**返回:**
- 整数，成功删除的记录数量

**功能:**
- 批量删除多条记录

#### 维护操作

```python
def cleanup_references(self) -> int
```

**返回:**
- 整数，删除的引用数量

**功能:**
- 清理数据库中未使用的引用

#### 导入/导出功能

##### 导出数据

```python
def export_data(self, output_file: str, include_encrypted: bool = False) -> int
```

**参数:**
- `output_file`: 字符串，输出文件路径
- `include_encrypted`: 布尔值，是否包含加密数据

**返回:**
- 整数，导出的记录数量

**功能:**
- 获取所有记录并解密数据
- 将数据导出到JSON文件
- 可选择是否包含加密形式的数据

##### 导入数据

```python
def import_data(self, input_file: str, enable_range_query: bool = False) -> int
```

**参数:**
- `input_file`: 字符串，输入文件路径
- `enable_range_query`: 布尔值，是否为导入的记录启用范围查询

**返回:**
- 整数，导入的记录数量

**功能:**
- 从JSON文件读取数据
- 如果数据包含加密索引和数据，直接使用
- 否则，从明文数据创建新记录

## 使用示例

```python
# 初始化安全数据库系统（创建新密钥）
secure_db = SecureDB()

# 添加加密记录
record_id = secure_db.add_record(index_value=42, data='{"name":"John Doe","age":30}', enable_range_query=True)

# 按索引搜索记录
results = secure_db.search_by_index(42)
for result in results:
    print(f"ID: {result['id']}, Data: {result['data']}")

# 范围查询
range_results = secure_db.search_by_range(min_value=30, max_value=50)
print(f"找到 {len(range_results)} 条记录在范围 [30, 50] 内")

# 导出数据
exported_count = secure_db.export_data("backup.json")
print(f"导出了 {exported_count} 条记录")
```

## 性能考虑

- 同态加密操作计算密集，可能会影响性能
- 批处理方法（`add_records_batch`、`get_records_batch`等）可以显著提高效率
- 缓存机制有助于减少重复计算和数据库访问
- 范围查询比精确索引查询更消耗资源

## 安全注意事项

- 密码应具有足够的强度以保护AES密钥
- 密钥文件应妥善保管，避免未授权访问
- 加密参数（如多项式模数度、明文模数等）直接影响安全性和性能
- 在生产环境中应定期轮换密钥