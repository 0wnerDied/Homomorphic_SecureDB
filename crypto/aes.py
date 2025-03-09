"""
AES加密模块
"""

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import logging
import xxhash
from typing import Union

logger = logging.getLogger(__name__)


class AESManager:
    """AES加密管理器，处理数据加密操作"""

    def __init__(self, key: bytes = None, key_size: int = 16):
        """
        初始化AES加密管理器

        Args:
            key: AES密钥，如果为None则随机生成
            key_size: 密钥大小，默认16字节(128位)
        """
        self.key = key if key else get_random_bytes(key_size)
        self.key_size = key_size

        # 缓存
        self._encrypt_cache = {}
        self._decrypt_cache = {}
        self.cache_hits = 0

        logger.info(f"AES manager initialized with {key_size*8}-bit key")

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """
        加密数据（CBC模式，PKCS7填充）

        Args:
            data: 要加密的数据，可以是字符串或字节

        Returns:
            加密后的数据（IV + 密文）
        """
        # 如果输入是字符串，转换为字节
        if isinstance(data, str):
            data = data.encode("utf-8")

        # 计算缓存键
        cache_key = xxhash.xxh64(data).hexdigest()
        if cache_key in self._encrypt_cache:
            self.cache_hits += 1
            return self._encrypt_cache[cache_key]

        try:
            # 创建AES密码对象，使用CBC模式
            iv = get_random_bytes(AES.block_size)  # 16字节IV
            cipher = AES.new(self.key, AES.MODE_CBC, iv=iv)

            # 使用PKCS7填充并加密数据
            padded_data = pad(data, AES.block_size)
            ciphertext = cipher.encrypt(padded_data)

            # 将IV附加到密文前面
            encrypted_data = iv + ciphertext

            # 更新缓存
            self._encrypt_cache[cache_key] = encrypted_data

            return encrypted_data

        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        解密数据（CBC模式，PKCS7填充）

        Args:
            encrypted_data: 加密的数据（IV + 密文）

        Returns:
            解密后的明文字节
        """
        # 计算缓存键
        cache_key = xxhash.xxh64(encrypted_data).hexdigest()
        if cache_key in self._decrypt_cache:
            self.cache_hits += 1
            return self._decrypt_cache[cache_key]

        try:
            # 提取IV和密文
            iv = encrypted_data[: AES.block_size]  # 前16字节是IV
            ciphertext = encrypted_data[AES.block_size :]  # 剩余部分是密文

            # 创建AES密码对象
            cipher = AES.new(self.key, AES.MODE_CBC, iv=iv)

            # 解密并去除填充
            padded_plaintext = cipher.decrypt(ciphertext)
            plaintext = unpad(padded_plaintext, AES.block_size)

            # 更新缓存
            self._decrypt_cache[cache_key] = plaintext

            return plaintext

        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise

    def get_key(self) -> bytes:
        """
        获取当前使用的密钥

        Returns:
            AES密钥
        """
        return self.key

    def set_key(self, key: bytes) -> None:
        """
        设置新的AES密钥

        Args:
            key: 新的AES密钥
        """
        if len(key) != self.key_size:
            raise ValueError(f"Key size must be {self.key_size} bytes")

        self.key = key
        self._encrypt_cache.clear()
        self._decrypt_cache.clear()
        self.cache_hits = 0

        logger.info("AES key updated")
