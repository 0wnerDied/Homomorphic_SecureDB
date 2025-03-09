"""
密钥管理模块 - 处理FHE和AES密钥的存储和加载
"""

import os
import pickle
import logging
import zstandard as zstd
from typing import Tuple
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

logger = logging.getLogger(__name__)


class KeyManager:
    """密钥管理器，处理密钥的安全存储和加载"""

    def __init__(self, keys_dir: str):
        """
        初始化密钥管理器

        Args:
            keys_dir: 密钥存储目录
        """
        self.keys_dir = keys_dir

        # 确保密钥目录存在
        if not os.path.exists(keys_dir):
            os.makedirs(keys_dir)
            logger.info(f"Created key directory: {keys_dir}")

        # 初始化压缩器
        self.compressor = zstd.ZstdCompressor(level=9)
        self.decompressor = zstd.ZstdDecompressor()

    def get_key_path(self, key_name: str) -> str:
        """
        获取密钥文件的完整路径

        Args:
            key_name: 密钥文件名

        Returns:
            密钥文件的完整路径
        """
        return os.path.join(self.keys_dir, key_name)

    def save_file(self, data: bytes, filename: str) -> None:
        """
        保存数据到文件

        Args:
            data: 要保存的数据
            filename: 文件名
        """
        try:
            file_path = self.get_key_path(filename)
            with open(file_path, "wb") as f:
                f.write(data)
            logger.info(f"Saved data to {file_path}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {e}")
            raise

    def load_file(self, filename: str) -> bytes:
        """
        从文件加载数据

        Args:
            filename: 文件名

        Returns:
            加载的数据
        """
        try:
            file_path = self.get_key_path(filename)
            with open(file_path, "rb") as f:
                data = f.read()
            logger.info(f"Loaded data from {file_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading data from {filename}: {e}")
            raise

    def encrypt_aes_key(self, aes_key: bytes, password: str) -> Tuple[bytes, bytes]:
        """
        使用密码加密AES密钥

        Args:
            aes_key: 要加密的AES密钥
            password: 用于加密的密码

        Returns:
            (encrypted_key, salt) 元组
        """
        try:
            # 生成盐
            salt = os.urandom(16)

            # 从密码派生密钥
            key = PBKDF2(
                password, salt, dkLen=32, count=100000, hmac_hash_module=SHA256
            )

            # 使用派生密钥加密AES密钥
            cipher = AES.new(key, AES.MODE_CBC)
            iv = cipher.iv
            encrypted_key = cipher.encrypt(pad(aes_key, AES.block_size))

            # 将IV附加到加密密钥
            result = iv + encrypted_key

            logger.info("AES key encrypted successfully")
            return (result, salt)

        except Exception as e:
            logger.error(f"Error encrypting AES key: {e}")
            raise

    def decrypt_aes_key(
        self, encrypted_data: bytes, salt: bytes, password: str
    ) -> bytes:
        """
        使用密码解密AES密钥

        Args:
            encrypted_data: 加密的数据（IV + 加密密钥）
            salt: 用于密码派生的盐
            password: 用于解密的密码

        Returns:
            解密的AES密钥
        """
        try:
            # 从密码派生密钥
            key = PBKDF2(
                password, salt, dkLen=32, count=100000, hmac_hash_module=SHA256
            )

            # 提取IV和加密密钥
            iv = encrypted_data[:16]
            encrypted_key = encrypted_data[16:]

            # 解密AES密钥
            cipher = AES.new(key, AES.MODE_CBC, iv=iv)
            decrypted_key = unpad(cipher.decrypt(encrypted_key), AES.block_size)

            logger.info("AES key decrypted successfully")
            return decrypted_key

        except Exception as e:
            logger.error(f"Error decrypting AES key: {e}")
            raise

    def save_aes_key(self, aes_key: bytes, key_file: str, password: str) -> None:
        """
        加密并保存AES密钥到文件

        Args:
            aes_key: 要保存的AES密钥
            key_file: 密钥文件名
            password: 用于加密的密码
        """
        try:
            # 加密AES密钥
            encrypted_key, salt = self.encrypt_aes_key(aes_key, password)

            # 准备保存的数据（salt + encrypted_key）
            data_to_save = {"salt": salt, "encrypted_key": encrypted_key}

            # 保存到文件
            key_path = self.get_key_path(key_file)
            with open(key_path, "wb") as f:
                pickle.dump(data_to_save, f)

            logger.info(f"Saved encrypted AES key to {key_path}")

        except Exception as e:
            logger.error(f"Error saving AES key: {e}")
            raise

    def load_aes_key(self, key_file: str, password: str) -> bytes:
        """
        从文件加载并解密AES密钥

        Args:
            key_file: 密钥文件名
            password: 用于解密的密码

        Returns:
            解密的AES密钥
        """
        try:
            # 加载加密的密钥数据
            key_path = self.get_key_path(key_file)
            with open(key_path, "rb") as f:
                data = pickle.load(f)

            salt = data["salt"]
            encrypted_key = data["encrypted_key"]

            # 解密AES密钥
            aes_key = self.decrypt_aes_key(encrypted_key, salt, password)

            logger.info(f"Loaded AES key from {key_path}")
            return aes_key

        except FileNotFoundError:
            logger.error(f"AES key file not found: {key_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading AES key: {e}")
            raise

    def compress_data(self, data: bytes) -> bytes:
        """
        压缩数据

        Args:
            data: 要压缩的数据

        Returns:
            压缩后的数据
        """
        try:
            return self.compressor.compress(data)
        except Exception as e:
            logger.error(f"Error compressing data: {e}")
            raise

    def decompress_data(self, compressed_data: bytes) -> bytes:
        """
        解压缩数据

        Args:
            compressed_data: 要解压的数据

        Returns:
            解压后的数据
        """
        try:
            return self.decompressor.decompress(compressed_data)
        except Exception as e:
            logger.error(f"Error decompressing data: {e}")
            raise
