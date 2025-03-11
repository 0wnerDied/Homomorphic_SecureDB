# 工具函数模块

## 概述

`utils.py` 是一个工具函数模块，提供了多种通用功能，包括性能计时、重试机制、缓存管理、数据压缩、哈希计算、文件操作和进度跟踪等。这些工具旨在提高代码的可靠性、性能和安全性。

## 装饰器

### `timing_decorator`

```python
def timing_decorator(func: Callable) -> Callable
```

**功能:**
- 测量函数执行时间并记录日志
- 包装原始函数，保留其签名和文档

**示例:**
```python
@timing_decorator
def expensive_operation():
    # 执行耗时操作
    pass
```

### `retry_decorator`

```python
def retry_decorator(max_retries: int = 3, delay: float = 1.0, 
                   backoff_factor: float = 2.0, exceptions: tuple = (Exception,)) -> Callable
```

**参数:**
- `max_retries`: 最大重试次数，默认为3
- `delay`: 初始延迟时间（秒），默认为1.0
- `backoff_factor`: 退避因子，每次重试后延迟时间会乘以这个因子，默认为2.0
- `exceptions`: 要捕获的异常类型，默认为所有异常

**功能:**
- 自动重试可能失败的操作
- 使用指数退避策略增加重试间隔
- 记录重试信息

**示例:**
```python
@retry_decorator(max_retries=5, exceptions=(ConnectionError, TimeoutError))
def network_operation():
    # 可能失败的网络操作
    pass
```

## 缓存管理

### `LRUCache` 类

```python
class LRUCache(Generic[K, V])
```

**功能:**
- 实现基于LRU（最近最少使用）策略的缓存
- 支持泛型键值类型
- 线程安全实现，支持并发访问
- 提供缓存命中率统计

**主要方法:**
- `__init__(self, capacity: int = 1000)`: 初始化缓存，设置容量
- `get(self, key: K) -> Optional[V]`: 获取缓存项，不存在返回None
- `put(self, key: K, value: V) -> None`: 添加或更新缓存项
- `remove(self, key: K) -> bool`: 移除缓存项，返回是否成功
- `clear(self) -> None`: 清空缓存
- `get_stats(self) -> Dict[str, Any]`: 获取缓存统计信息

**示例:**
```python
# 创建缓存实例
cache = LRUCache[str, dict](capacity=500)

# 添加缓存项
cache.put("user:123", {"name": "John", "age": 30})

# 获取缓存项
user = cache.get("user:123")

# 获取统计信息
stats = cache.get_stats()
print(f"命中率: {stats['hit_rate']:.2%}")
```

## 数据压缩

### `DataCompressor` 类

```python
class DataCompressor
```

**功能:**
- 使用zstandard算法进行高效数据压缩和解压缩
- 支持序列化对象的压缩存储和加载
- 提供字符串特定的压缩方法

**主要方法:**
- `__init__(self, level: int = 9)`: 初始化压缩器，设置压缩级别
- `compress(self, data: bytes) -> bytes`: 压缩二进制数据
- `decompress(self, compressed_data: bytes) -> bytes`: 解压缩数据
- `compress_and_save(self, data: Any, filename: str) -> None`: 序列化、压缩并保存数据
- `load_and_decompress(self, filename: str) -> Any`: 加载、解压缩并反序列化数据
- `compress_string(self, text: str) -> bytes`: 压缩字符串
- `decompress_to_string(self, compressed_data: bytes) -> str`: 解压缩为字符串

**示例:**
```python
# 创建压缩器
compressor = DataCompressor(level=12)  # 更高的压缩比

# 压缩字符串
compressed = compressor.compress_string("大量文本数据...")

# 解压缩
original = compressor.decompress_to_string(compressed)

# 保存复杂对象
data = {"results": [complex_object1, complex_object2]}
compressor.compress_and_save(data, "results.dat")

# 加载数据
loaded_data = compressor.load_and_decompress("results.dat")
```

## 哈希函数

### `hash_data`

```python
def hash_data(data: bytes) -> str
```

**功能:**
- 使用xxHash算法计算数据的哈希值
- 返回十六进制哈希字符串
- xxHash比MD5或SHA更快，适合大量数据处理

### `hash_file`

```python
def hash_file(filepath: str, chunk_size: int = 8192) -> str
```

**功能:**
- 计算文件的xxHash哈希值
- 分块读取，适合大文件
- 返回十六进制哈希字符串

**示例:**
```python
# 计算数据哈希
data_hash = hash_data(b"sensitive data")

# 计算文件哈希
file_hash = hash_file("large_file.dat")
```

## 文件操作

### `ensure_directory`

```python
def ensure_directory(directory: str) -> None
```

**功能:**
- 确保目录存在，如果不存在则创建

### `SafeFileHandler` 类

```python
class SafeFileHandler
```

**功能:**
- 提供安全的文件读写操作
- 支持原子写入，防止数据损坏
- 自动创建备份
- 专用的JSON文件处理方法

**主要方法:**
- `atomic_write(filepath: str, data: Union[str, bytes], mode: str = "w", backup: bool = True) -> None`: 原子方式写入文件
- `read_json(filepath: str, default: Any = None) -> Any`: 安全读取JSON文件
- `write_json(filepath: str, data: Any, pretty: bool = True, backup: bool = True) -> None`: 安全写入JSON文件

**示例:**
```python
# 原子写入文件
SafeFileHandler.atomic_write("config.txt", "new configuration data")

# 读取JSON
config = SafeFileHandler.read_json("settings.json", default={})

# 写入JSON
data = {"version": "1.0", "settings": {"enabled": True}}
SafeFileHandler.write_json("settings.json", data, pretty=True)
```

## 进度跟踪

### `ProgressTracker` 类

```python
class ProgressTracker
```

**功能:**
- 跟踪长时间运行操作的进度
- 估计剩余完成时间
- 计算处理速率
- 定期更新日志

**主要方法:**
- `__init__(self, total: int, description: str = "Processing", update_interval: float = 0.5)`: 初始化跟踪器
- `start(self) -> None`: 开始跟踪进度
- `update(self, increment: int = 1, force: bool = False) -> None`: 更新进度
- `finish(self) -> Tuple[float, float]`: 完成跟踪，返回总耗时和处理速率

**示例:**
```python
# 创建进度跟踪器
tracker = ProgressTracker(total=1000, description="Processing records")

# 开始处理
tracker.start()

# 处理项目
for item in items:
    process_item(item)
    tracker.update()

# 完成处理
total_time, items_per_sec = tracker.finish()
print(f"平均处理速度: {items_per_sec:.2f} 项/秒")
```

## 异常处理

模块设置了全局异常处理钩子，确保未捕获的异常被记录到日志中：

```python
def exception_handler(exc_type, exc_value, exc_traceback)
```

**功能:**
- 捕获并记录未处理的异常
- 保留键盘中断（Ctrl+C）的正常行为

## 使用建议

1. 对于可能失败的网络或I/O操作，使用`retry_decorator`增强可靠性
2. 对于频繁访问的数据，使用`LRUCache`减少计算或数据库查询
3. 对于大型数据存储，使用`DataCompressor`节省空间
4. 使用`SafeFileHandler`进行配置文件操作，防止意外损坏
5. 对于长时间运行的批处理操作，使用`ProgressTracker`监控进度
6. 使用`timing_decorator`识别性能瓶颈

## 性能考虑

- `xxhash`算法比传统哈希算法（如SHA-256）快10-20倍
- `zstandard`压缩提供比gzip更好的压缩比和速度
- LRU缓存使用`OrderedDict`实现，具有O(1)的查找和更新复杂度
- 文件原子写入使用临时文件和重命名操作，确保数据完整性
