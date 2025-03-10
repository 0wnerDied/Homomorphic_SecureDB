"""
工具函数模块
"""

import logging
import time
import os
import sys
import json
import pickle
import threading
from datetime import datetime
from functools import wraps
from typing import Callable, Any, Dict, TypeVar, Generic, Optional, Union, Tuple
from collections import OrderedDict

import xxhash
import zstandard as zstd

# 配置日志
logger = logging.getLogger(__name__)

# 泛型类型变量定义
K = TypeVar("K")  # 键类型
V = TypeVar("V")  # 值类型


def timing_decorator(func: Callable) -> Callable:
    """
    计时装饰器，用于测量函数执行时间

    Args:
        func: 要计时的函数

    Returns:
        包装后的函数
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"{func.__name__} completed in {elapsed:.3f} seconds")
        return result

    return wrapper


def retry_decorator(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    重试装饰器，用于自动重试可能失败的操作

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子，每次重试后延迟时间会乘以这个因子
        exceptions: 要捕获的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_retries, delay
            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    mtries -= 1
                    if mtries == 0:
                        raise

                    logger.warning(
                        f"Function {func.__name__} failed with {str(e)}. "
                        f"Retrying in {mdelay:.2f} seconds... ({max_retries - mtries}/{max_retries})"
                    )

                    time.sleep(mdelay)
                    mdelay *= backoff_factor
            return func(*args, **kwargs)

        return wrapper

    return decorator


class LRUCache(Generic[K, V]):
    """
    LRU缓存实现

    使用 OrderedDict 实现的 LRU (Least Recently Used) 缓存
    """

    def __init__(self, capacity: int = 1000):
        """
        初始化LRU缓存

        Args:
            capacity: 缓存容量
        """
        self.capacity = capacity
        self.cache: OrderedDict[K, V] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = threading.RLock()  # 添加线程锁以支持并发访问

    def get(self, key: K) -> Optional[V]:
        """
        获取缓存项

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回None
        """
        with self._lock:
            if key in self.cache:
                # 移动到最近使用
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value

            self.misses += 1
            return None

    def put(self, key: K, value: V) -> None:
        """
        添加缓存项

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            if key in self.cache:
                # 移除旧值
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # 移除最久未使用的项
                self.cache.popitem(last=False)

            # 添加新值
            self.cache[key] = value

    def remove(self, key: K) -> bool:
        """
        从缓存中移除项

        Args:
            key: 要移除的键

        Returns:
            如果键存在并被移除返回 True，否则返回 False
        """
        with self._lock:
            if key in self.cache:
                self.cache.pop(key)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            包含命中率、命中次数和未命中次数的字典
        """
        with self._lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0

            return {
                "size": len(self.cache),
                "capacity": self.capacity,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
            }

    def __len__(self) -> int:
        """返回缓存中的项数"""
        return len(self.cache)

    def __contains__(self, key: K) -> bool:
        """检查键是否在缓存中"""
        return key in self.cache


class DataCompressor:
    """数据压缩工具类"""

    def __init__(self, level: int = 9):
        """
        初始化压缩器

        Args:
            level: 压缩级别，1-22，默认9
        """
        self.compressor = zstd.ZstdCompressor(level=level)
        self.decompressor = zstd.ZstdDecompressor()

    def compress(self, data: bytes) -> bytes:
        """
        压缩数据

        Args:
            data: 要压缩的数据

        Returns:
            压缩后的数据
        """
        return self.compressor.compress(data)

    def decompress(self, compressed_data: bytes) -> bytes:
        """
        解压缩数据

        Args:
            compressed_data: 要解压的数据

        Returns:
            解压后的数据
        """
        return self.decompressor.decompress(compressed_data)

    def compress_and_save(self, data: Any, filename: str) -> None:
        """
        序列化、压缩并保存数据

        Args:
            data: 要保存的数据
            filename: 文件名
        """
        serialized = pickle.dumps(data)
        compressed = self.compress(serialized)

        with open(filename, "wb") as f:
            f.write(compressed)

    def load_and_decompress(self, filename: str) -> Any:
        """
        加载、解压缩并反序列化数据

        Args:
            filename: 文件名

        Returns:
            加载的数据
        """
        with open(filename, "rb") as f:
            compressed = f.read()

        serialized = self.decompress(compressed)
        return pickle.loads(serialized)

    def compress_string(self, text: str) -> bytes:
        """
        压缩字符串

        Args:
            text: 要压缩的字符串

        Returns:
            压缩后的字节数据
        """
        return self.compress(text.encode("utf-8"))

    def decompress_to_string(self, compressed_data: bytes) -> str:
        """
        解压缩为字符串

        Args:
            compressed_data: 压缩的数据

        Returns:
            解压缩后的字符串
        """
        return self.decompress(compressed_data).decode("utf-8")


def hash_data(data: bytes) -> str:
    """
    计算数据的哈希值

    Args:
        data: 要哈希的数据

    Returns:
        哈希值的十六进制字符串
    """
    return xxhash.xxh64(data).hexdigest()


def hash_file(filepath: str, chunk_size: int = 8192) -> str:
    """
    计算文件的哈希值

    Args:
        filepath: 文件路径
        chunk_size: 读取块大小

    Returns:
        文件的哈希值
    """
    hasher = xxhash.xxh64()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建

    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")


class SafeFileHandler:
    """安全文件处理类，提供原子写入和备份功能"""

    @staticmethod
    def atomic_write(
        filepath: str, data: Union[str, bytes], mode: str = "w", backup: bool = True
    ) -> None:
        """
        原子方式写入文件（先写入临时文件，再重命名）

        Args:
            filepath: 目标文件路径
            data: 要写入的数据
            mode: 写入模式 ('w' 为文本, 'wb' 为二进制)
            backup: 是否在覆盖前创建备份
        """
        # 确保目录存在
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # 如果文件存在且需要备份
        if os.path.exists(filepath) and backup:
            backup_path = f"{filepath}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
            os.rename(filepath, backup_path)
            logger.debug(f"Created backup: {backup_path}")

        # 创建临时文件
        temp_path = f"{filepath}.tmp"

        try:
            # 写入临时文件
            with open(temp_path, mode) as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())  # 确保数据写入磁盘

            # 原子重命名
            os.replace(temp_path, filepath)
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

    @staticmethod
    def read_json(filepath: str, default: Any = None) -> Any:
        """
        安全读取JSON文件

        Args:
            filepath: 文件路径
            default: 如果文件不存在或格式错误时返回的默认值

        Returns:
            解析后的JSON数据或默认值
        """
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            return default
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading JSON file {filepath}: {str(e)}")
            return default

    @staticmethod
    def write_json(
        filepath: str, data: Any, pretty: bool = True, backup: bool = True
    ) -> None:
        """
        安全写入JSON文件

        Args:
            filepath: 文件路径
            data: 要写入的数据
            pretty: 是否美化输出
            backup: 是否创建备份
        """
        indent = 2 if pretty else None
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)
        SafeFileHandler.atomic_write(filepath, json_str, "w", backup)


class ProgressTracker:
    """进度跟踪器，用于长时间运行的操作"""

    def __init__(
        self, total: int, description: str = "Processing", update_interval: float = 0.5
    ):
        """
        初始化进度跟踪器

        Args:
            total: 总项数
            description: 操作描述
            update_interval: 更新间隔（秒）
        """
        self.total = total
        self.description = description
        self.update_interval = update_interval
        self.current = 0
        self.start_time = None
        self.last_update = 0

    def start(self) -> None:
        """开始跟踪进度"""
        self.start_time = time.time()
        self.last_update = self.start_time
        logger.info(f"Started {self.description}: 0/{self.total} (0.0%)")

    def update(self, increment: int = 1, force: bool = False) -> None:
        """
        更新进度

        Args:
            increment: 增量
            force: 是否强制更新日志
        """
        self.current += increment
        current_time = time.time()

        # 如果达到更新间隔或强制更新
        if force or (current_time - self.last_update >= self.update_interval):
            elapsed = current_time - self.start_time
            percent = (self.current / self.total) * 100 if self.total > 0 else 0

            # 估计剩余时间
            if self.current > 0:
                items_per_sec = self.current / elapsed
                remaining_items = self.total - self.current
                eta = remaining_items / items_per_sec if items_per_sec > 0 else 0
                eta_str = f", ETA: {eta:.1f}s" if eta > 0 else ""
            else:
                eta_str = ""

            logger.info(
                f"{self.description}: {self.current}/{self.total} "
                f"({percent:.1f}%), {elapsed:.1f}s elapsed{eta_str}"
            )
            self.last_update = current_time

    def finish(self) -> Tuple[float, float]:
        """
        完成进度跟踪

        Returns:
            元组 (总耗时, 每秒处理项数)
        """
        if not self.start_time:
            return 0, 0

        end_time = time.time()
        total_time = end_time - self.start_time
        items_per_sec = self.current / total_time if total_time > 0 else 0

        logger.info(
            f"Completed {self.description}: {self.current}/{self.total} items "
            f"in {total_time:.2f}s ({items_per_sec:.2f} items/s)"
        )
        return total_time, items_per_sec


# 设置系统异常钩子，确保未捕获的异常被记录
def exception_handler(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 正常处理Ctrl+C
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# 设置异常处理钩子
sys.excepthook = exception_handler
