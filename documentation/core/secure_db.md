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

##### 通过索引更新记录

```python
def update_by_index(self, index_value: int, new_data: str) -> int
```

**参数:**
- `index_value`: 整数，索引值
- `new_data`: 字符串，新数据

**返回:**
- 整数，成功更新的记录数量

**功能:**
- 搜索所有匹配指定索引值的记录
- 使用AES加密新数据
- 更新所有匹配记录
- 返回成功更新的记录数量

##### 通过范围更新记录

```python
def update_by_range(self, new_data: str, min_value: int = None, max_value: int = None) -> int
```

**参数:**
- `new_data`: 字符串，新数据
- `min_value`: 整数，范围最小值，如果为None则不检查下限
- `max_value`: 整数，范围最大值，如果为None则不检查上限

**返回:**
- 整数，成功更新的记录数量

**功能:**
- 搜索所有在指定范围内的记录
- 使用AES加密新数据
- 批量更新所有匹配记录
- 返回成功更新的记录数量

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

##### 通过索引删除记录

```python
def delete_by_index(self, index_value: int) -> int
```

**参数:**
- `index_value`: 整数，索引值

**返回:**
- 整数，成功删除的记录数量

**功能:**
- 搜索所有匹配指定索引值的记录
- 批量删除所有匹配记录
- 返回成功删除的记录数量

##### 通过范围删除记录

```python
def delete_by_range(self, min_value: int = None, max_value: int = None) -> int
```

**参数:**
- `min_value`: 整数，范围最小值，如果为None则不检查下限
- `max_value`: 整数，范围最大值，如果为None则不检查上限

**返回:**
- 整数，成功删除的记录数量

**功能:**
- 搜索所有在指定范围内的记录
- 批量删除所有匹配记录
- 返回成功删除的记录数量

#### 维护操作

```python
def cleanup_references(self) -> int
```

**返回:**
- 整数，删除的引用数量

**功能:**
- 清理数据库中未使用的引用

#### 导入/导出功能

##### 导出所有数据

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

##### 导出特定记录

```python
def export_records(self, record_ids: List[int], output_file: str) -> int
```

**参数:**
- `record_ids`: 整数列表，要导出的记录ID列表
- `output_file`: 字符串，输出文件路径

**返回:**
- 整数，成功导出的记录数量

**功能:**
- 获取指定ID的记录并解密数据
- 将数据导出到JSON文件
- 适用于需要导出特定记录子集的场景

##### 导入所有数据

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

##### 导入特定记录

```python
def import_records(self, input_file: str) -> List[int]
```

**参数:**
- `input_file`: 字符串，输入文件路径

**返回:**
- 整数列表，导入记录的ID列表

**功能:**
- 从JSON文件读取特定记录数据
- 将记录导入到数据库系统
- 返回新创建记录的ID列表，便于后续跟踪和操作
- 适用于需要选择性导入特定记录的场景

## 使用示例

### 基本操作

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

### 基于范围的操作示例

```python
# 初始化安全数据库系统（加载现有密钥）
secure_db = SecureDB(load_keys=True)

# 添加一些测试记录
for i in range(1, 11):
    secure_db.add_record(
        index_value=i*10, 
        data=f'{{"id":{i},"name":"Item {i}","value":{i*100}}}', 
        enable_range_query=True
    )

# 通过范围更新记录
updated_count = secure_db.update_by_range(
    new_data='{"status":"on_sale","discount":0.2}',
    min_value=30,
    max_value=70
)
print(f"已更新 {updated_count} 条记录在范围 [30, 70] 内")

# 通过索引更新记录
updated_count = secure_db.update_by_index(
    index_value=100,
    new_data='{"status":"sold_out","available":false}'
)
print(f"已更新 {updated_count} 条索引值为 100 的记录")

# 通过范围删除记录
deleted_count = secure_db.delete_by_range(min_value=80)
print(f"已删除 {deleted_count} 条索引值大于等于 80 的记录")

# 通过索引删除记录
deleted_count = secure_db.delete_by_index(index_value=20)
print(f"已删除 {deleted_count} 条索引值为 20 的记录")
```

### 导出和导入特定记录

```python
# 初始化安全数据库系统（加载现有密钥）
secure_db = SecureDB(load_keys=True)

# 添加一些测试记录
record_ids = []
for i in range(10):
    record_id = secure_db.add_record(
        index_value=1000+i, 
        data=f'{{"customer_id":{1000+i},"name":"客户{i}","value":{i*100}}}', 
        enable_range_query=True
    )
    record_ids.append(record_id)

# 导出特定记录
export_file = "specific_records.json"
exported_count = secure_db.export_records(record_ids[:5], export_file)
print(f"导出了 {exported_count} 条特定记录到 {export_file}")

# 删除原始记录
secure_db.delete_records_batch(record_ids)

# 导入特定记录
imported_ids = secure_db.import_records(export_file)
print(f"导入了 {len(imported_ids)} 条记录，ID: {imported_ids}")

# 验证导入的记录
for record_id in imported_ids:
    data = secure_db.get_record(record_id)
    print(f"记录 {record_id}: {data}")
```

## 性能考虑

- 同态加密操作计算密集，可能会影响性能
- 批处理方法（`add_records_batch`、`get_records_batch`等）可以显著提高效率
- 缓存机制有助于减少重复计算和数据库访问
- 范围查询比精确索引查询更消耗资源
- 基于范围的更新和删除操作会先执行范围查询，然后再执行批量操作，因此可能比直接操作更耗时
- 导出和导入大量记录时，建议使用批处理方式进行处理，避免内存占用过高

## 安全注意事项

- 密码应具有足够的强度以保护AES密钥
- 密钥文件应妥善保管，避免未授权访问
- 加密参数（如多项式模数度、明文模数等）直接影响安全性和性能
- 在生产环境中应定期轮换密钥
- 导出的数据文件可能包含敏感信息，应妥善保护
- 导入数据时应验证数据来源的可靠性，避免导入恶意数据
- 基于范围的操作可能会暴露更多数据模式，应谨慎使用

## 数据备份与恢复

系统提供了完整的数据备份与恢复机制：

1. **全量备份**：使用 `export_data()` 方法导出所有记录
2. **选择性备份**：使用 `export_records()` 方法导出特定记录
3. **数据恢复**：使用 `import_data()` 或 `import_records()` 方法导入备份数据
4. **增量备份策略**：可以结合索引值和时间戳实现增量备份

建议定期执行备份操作，并将备份文件存储在安全的位置。在进行重大操作前，也应当创建备份以便在出现问题时能够恢复数据。

## 索引操作的使用场景

基于索引和范围的记录操作提供了更灵活的数据管理方式：

1. **批量数据更新**：当需要更新满足特定条件的所有记录时，可以使用 `update_by_range()` 或 `update_by_index()`
2. **数据清理**：使用 `delete_by_range()` 可以轻松删除过期或不再需要的数据
3. **分类管理**：使用索引值对数据进行分类，然后对特定类别的数据执行批量操作
4. **数据迁移**：在系统升级或数据结构变更时，可以使用这些方法对数据进行批量转换
5. **状态更新**：例如，将所有在特定价格范围内的商品标记为促销状态
