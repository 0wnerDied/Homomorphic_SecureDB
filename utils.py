"""
工具函数模块
"""

import logging
import time
from typing import Callable, Any, Dict
import xxhash
import zstandard as zstd
import pickle
import os

logger = logging.getLogger(__name__)


def timing_decorator(func: Callable) -> Callable:
    """
    计时装饰器，用于测量函数执行时间

    Args:
        func: 要计时的函数

    Returns:
        包装后的函数
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"{func.__name__} completed in {elapsed:.3f} seconds")
        return result

    return wrapper


class LRUCache:
    """LRU缓存实现"""

    def __init__(self, capacity: int = 1000):
        """
        初始化LRU缓存

        Args:
            capacity: 缓存容量
        """
        self.capacity = capacity
        self.cache = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        """
        获取缓存项

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回None
        """
        if key in self.cache:
            # 移动到最近使用
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value

        self.misses += 1
        return None

    def put(self, key: str, value: Any) -> None:
        """
        添加缓存项

        Args:
            key: 缓存键
            value: 缓存值
        """
        if key in self.cache:
            # 移除旧值
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            # 移除最久未使用的项
            self.cache.pop(next(iter(self.cache)))

        # 添加新值
        self.cache[key] = value

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        Returns:
            包含命中率、命中次数和未命中次数的字典
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


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


def hash_data(data: bytes) -> str:
    """
    计算数据的哈希值

    Args:
        data: 要哈希的数据

    Returns:
        哈希值的十六进制字符串
    """
    return xxhash.xxh64(data).hexdigest()


def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建

    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")
