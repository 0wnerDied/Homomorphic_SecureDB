"""
同态加密模块 - 使用SEAL-Python库实现BFV方案
"""

import seal
import os
import logging
import numpy as np
from typing import Dict, Any, List
from .key_manager import KeyManager

logger = logging.getLogger(__name__)


class FHEManager:
    """同态加密管理器，处理BFV加密操作"""

    def __init__(
        self,
        config: Dict[str, Any],
        key_manager: KeyManager,
        encrypt_only: bool = False,
    ):
        """
        初始化同态加密管理器

        Args:
            config: 配置字典，包含scheme, poly_modulus_degree, plain_modulus等参数
            key_manager: 密钥管理器实例
            encrypt_only: 是否仅用于加密（不需要私钥）
        """
        self.config = config
        self.key_manager = key_manager
        self.encrypt_only = encrypt_only

        # 密钥文件路径
        self.context_file = key_manager.get_key_path(
            config.get("context_file", "params.bin")
        )
        self.public_key_file = key_manager.get_key_path(
            config.get("public_key_file", "public.key")
        )
        self.private_key_file = key_manager.get_key_path(
            config.get("private_key_file", "secret.key")
        )
        self.relin_key_file = key_manager.get_key_path(
            config.get("relin_key_file", "relin.key")
        )

        # 缓存
        self._encrypt_cache = {}
        self._decrypt_cache = {}
        self.cache_hits = 0

        # 如果密钥文件存在，加载它们；否则创建新的密钥
        if os.path.exists(self.context_file) and os.path.exists(self.public_key_file):
            try:
                logger.info(f"Loading FHE keys from files")
                self._load_keys()
            except Exception as e:
                logger.error(f"Error loading FHE keys: {e}")
                logger.info("Creating new FHE context and keys")
                self._initialize_context()
        else:
            logger.info("Creating new FHE context and keys")
            self._initialize_context()

    def _initialize_context(self):
        """初始化FHE上下文和密钥"""
        try:
            # 设置加密参数 (BFV 方案)
            self.parms = seal.EncryptionParameters(seal.scheme_type.bfv)
            self.parms.set_poly_modulus_degree(self.config["poly_modulus_degree"])
            self.parms.set_coeff_modulus(
                seal.CoeffModulus.BFVDefault(self.config["poly_modulus_degree"])
            )
            self.parms.set_plain_modulus(self.config["plain_modulus"])

            # 创建上下文
            self.context = seal.SEALContext(self.parms)

            # 生成密钥
            keygen = seal.KeyGenerator(self.context)
            self.public_key = keygen.create_public_key()
            self.secret_key = keygen.secret_key()
            self.relin_keys = keygen.create_relin_keys()

            # 创建加密器、评估器和解密器
            self.encryptor = seal.Encryptor(self.context, self.public_key)
            self.evaluator = seal.Evaluator(self.context)
            if not self.encrypt_only:
                self.decryptor = seal.Decryptor(self.context, self.secret_key)

            # 创建批处理编码器 (替代IntegerEncoder)
            self.encoder = seal.BatchEncoder(self.context)

            logger.info("FHE context initialized successfully")

            # 保存新生成的密钥
            self._save_keys()
        except Exception as e:
            logger.error(f"Error initializing FHE context: {e}")
            raise

    def _save_keys(self):
        """保存FHE上下文和密钥"""
        try:
            # 保存加密参数
            self.parms.save(self.context_file)

            # 保存公钥
            self.public_key.save(self.public_key_file)

            # 保存私钥和重线性化密钥
            if not self.encrypt_only:
                self.secret_key.save(self.private_key_file)
                self.relin_keys.save(self.relin_key_file)

            logger.info("FHE keys saved successfully")
        except Exception as e:
            logger.error(f"Error saving FHE keys: {e}")
            raise

    def _load_keys(self):
        """加载FHE上下文和密钥"""
        try:
            # 加载加密参数
            self.parms = seal.EncryptionParameters()
            self.parms.load(self.context_file)

            # 创建上下文
            self.context = seal.SEALContext(self.parms)

            # 加载公钥
            self.public_key = seal.PublicKey()
            self.public_key.load(self.context, self.public_key_file)

            # 创建加密器和评估器
            self.encryptor = seal.Encryptor(self.context, self.public_key)
            self.evaluator = seal.Evaluator(self.context)

            # 创建批处理编码器 (替代IntegerEncoder)
            self.encoder = seal.BatchEncoder(self.context)

            # 如果不是仅加密模式，加载私钥和重线性化密钥
            if not self.encrypt_only:
                self.secret_key = seal.SecretKey()
                self.secret_key.load(self.context, self.private_key_file)

                self.relin_keys = seal.RelinKeys()
                self.relin_keys.load(self.context, self.relin_key_file)

                self.decryptor = seal.Decryptor(self.context, self.secret_key)
                logger.info("Loaded all FHE keys")
            else:
                logger.info("Encrypt-only mode: Loaded public key only")

        except Exception as e:
            logger.error(f"Error loading FHE keys: {e}")
            raise

    def encrypt_int(self, value: int) -> bytes:
        """
        加密整数值

        Args:
            value: 要加密的整数

        Returns:
            加密后的压缩字节数据
        """
        # 检查缓存
        cache_key = f"enc:{value}"
        if cache_key in self._encrypt_cache:
            self.cache_hits += 1
            return self._encrypt_cache[cache_key]

        try:
            # 创建一个只包含一个值的向量
            values = np.array([value], dtype=np.int64)

            # 编码整数 - 使用BatchEncoder替代IntegerEncoder
            plain = self.encoder.encode(values)

            # 加密
            encrypted = self.encryptor.encrypt(plain)

            # 序列化
            serialized = encrypted.to_string()
            compressed = self.key_manager.compress_data(serialized)

            # 更新缓存
            self._encrypt_cache[cache_key] = compressed

            return compressed
        except Exception as e:
            logger.error(f"Error encrypting integer {value}: {e}")
            raise

    def decrypt_int(self, compressed_bytes: bytes) -> int:
        """
        解密整数值

        Args:
            compressed_bytes: 压缩的加密字节数据

        Returns:
            解密后的整数
        """
        if self.encrypt_only:
            raise ValueError("Cannot decrypt in encrypt-only mode")

        # 检查缓存
        cache_key = f"dec:{compressed_bytes.hex()[:32]}"
        if cache_key in self._decrypt_cache:
            self.cache_hits += 1
            return self._decrypt_cache[cache_key]

        try:
            # 解压缩并加载密文
            serialized = self.key_manager.decompress_data(compressed_bytes)
            encrypted = self.context.from_cipher_str(serialized)

            # 解密
            plain_result = self.decryptor.decrypt(encrypted)

            # 使用BatchEncoder解码
            result_array = self.encoder.decode(plain_result)
            result = int(result_array[0])  # 获取第一个值并转换为int

            # 更新缓存
            self._decrypt_cache[cache_key] = result

            return result
        except Exception as e:
            logger.error(f"Error decrypting integer: {e}")
            raise

    def compare_encrypted(self, encrypted_bytes: bytes, query_value: int) -> bool:
        """
        比较加密索引与查询值是否相等

        Args:
            encrypted_bytes: 加密的索引字节数据
            query_value: 要比较的查询值

        Returns:
            如果相等返回True，否则返回False
        """
        if self.encrypt_only:
            raise ValueError("Cannot compare in encrypt-only mode")

        try:
            # 解压缩并加载密文
            serialized = self.key_manager.decompress_data(encrypted_bytes)
            encrypted = self.context.from_cipher_str(serialized)

            # 加密查询值
            values = np.array([query_value], dtype=np.int64)
            query_plain = self.encoder.encode(values)
            query_encrypted = self.encryptor.encrypt(query_plain)

            # 计算差值
            result = self.evaluator.sub(encrypted, query_encrypted)

            # 解密结果
            plain_result = self.decryptor.decrypt(result)

            # 使用BatchEncoder解码
            diff_array = self.encoder.decode(plain_result)
            diff = int(diff_array[0])  # 获取第一个值

            return diff == 0
        except Exception as e:
            logger.error(f"Error comparing encrypted values: {e}")
            raise

    def encrypt_string(self, text: str) -> List[bytes]:
        """
        加密字符串

        Args:
            text: 要加密的字符串

        Returns:
            加密字符的字节列表
        """
        result = []
        for char in text:
            encrypted_char = self.encrypt_int(ord(char))
            result.append(encrypted_char)
        return result

    def decrypt_string(self, encrypted_chars: List[bytes]) -> str:
        """
        解密字符串

        Args:
            encrypted_chars: 加密字符的字节列表

        Returns:
            解密后的字符串
        """
        if self.encrypt_only:
            raise ValueError("Cannot decrypt in encrypt-only mode")

        result = []
        for enc_char in encrypted_chars:
            ascii_val = self.decrypt_int(enc_char)
            result.append(chr(ascii_val))
        return "".join(result)

    def clear_cache(self):
        """清除缓存"""
        self._encrypt_cache.clear()
        self._decrypt_cache.clear()
        self.cache_hits = 0
