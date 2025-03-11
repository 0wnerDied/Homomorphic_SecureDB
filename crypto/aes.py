"""
AES加密模块
"""

import logging
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from typing import Union, Optional

logger = logging.getLogger(__name__)


class AESManager:
    """AES加密管理器, 处理AES-GCM加密操作"""

    def __init__(self, key: Optional[bytes] = None, key_size: int = 32):
        """
        初始化AES加密管理器

        Args:
            key: 可选的AES密钥, 如果未提供则生成新密钥
            key_size: 密钥大小 (字节) , 默认为32 (256位) 
        """
        self.key = key if key is not None else get_random_bytes(key_size)
        logger.info(f"AES manager initialized with {'provided' if key else 'new'} key")

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """
        加密数据

        Args:
            data: 要加密的数据, 可以是字符串或字节

        Returns:
            加密后的字节数据 (包含IV和认证标签) 
        """
        try:
            # 将字符串转换为字节
            if isinstance(data, str):
                data_bytes = data.encode("utf-8")
            else:
                data_bytes = data

            # 生成随机IV
            iv = get_random_bytes(12)  # GCM模式使用12字节IV

            # 创建AES-GCM密码对象
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=iv)

            # 加密数据
            ciphertext, tag = cipher.encrypt_and_digest(data_bytes)

            # 组合IV、认证标签和密文
            # 格式: IV (12字节) + 标签 (16字节) + 密文
            return iv + tag + ciphertext
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        解密数据

        Args:
            encrypted_data: 加密后的字节数据 (包含IV和认证标签) 

        Returns:
            解密后的字节数据
        """
        try:
            # 提取IV、认证标签和密文
            iv = encrypted_data[:12]
            tag = encrypted_data[12:28]
            ciphertext = encrypted_data[28:]

            # 创建AES-GCM密码对象
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=iv)

            # 解密数据
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)

            return plaintext
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise

    def get_key(self) -> bytes:
        """
        获取AES密钥

        Returns:
            AES密钥字节
        """
        return self.key

    def encrypt_batch(self, data_list: list[Union[str, bytes]]) -> list[bytes]:
        """
        批量加密数据

        Args:
            data_list: 要加密的数据列表

        Returns:
            加密后的字节数据列表
        """
        result = []
        for data in data_list:
            encrypted = self.encrypt(data)
            result.append(encrypted)
        return result

    def decrypt_batch(self, encrypted_data_list: list[bytes]) -> list[bytes]:
        """
        批量解密数据

        Args:
            encrypted_data_list: 加密后的字节数据列表

        Returns:
            解密后的字节数据列表
        """
        result = []
        for encrypted_data in encrypted_data_list:
            decrypted = self.decrypt(encrypted_data)
            result.append(decrypted)
        return result
