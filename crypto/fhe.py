"""
同态加密模块 - 使用SEAL-Python库实现BFV方案
"""

import seal
import os
import logging
import numpy as np
from typing import Dict, Any, List

from .key_manager import KeyManager
from core.utils import LRUCache

logger = logging.getLogger(__name__)


class FHEManager:
    """同态加密管理器, 处理BFV加密操作"""

    def __init__(
        self,
        config: Dict[str, Any],
        key_manager: KeyManager,
        encrypt_only: bool = False,
        cache_size: int = 2000,
    ):
        """
        初始化同态加密管理器

        Args:
            config: 配置字典, 包含scheme, poly_modulus_degree, plain_modulus等参数
            key_manager: 密钥管理器实例
            encrypt_only: 是否仅用于加密 (不需要私钥)
            cache_size: 缓存大小, 默认2000项
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
        self.galois_key_file = key_manager.get_key_path(
            config.get("galois_key_file", "galois.key")
        )

        self._encrypt_cache = LRUCache[str, bytes](capacity=cache_size)
        self._decrypt_cache = LRUCache[str, int](capacity=cache_size)

        # 如果密钥文件存在, 加载它们；否则创建新的密钥
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
                seal.CoeffModulus.Create(
                    self.config["poly_modulus_degree"],
                    self.config["coeff_modulus_bits"],
                )
            )

            self.parms.set_plain_modulus(self.config["plain_modulus"])

            # 创建上下文
            self.context = seal.SEALContext(self.parms)

            # 生成密钥
            keygen = seal.KeyGenerator(self.context)
            self.public_key = keygen.create_public_key()
            self.secret_key = keygen.secret_key()
            self.relin_keys = keygen.create_relin_keys()
            self.galois_keys = keygen.create_galois_keys()

            # 创建加密器、评估器和解密器
            self.encryptor = seal.Encryptor(self.context, self.public_key)
            self.evaluator = seal.Evaluator(self.context)
            if not self.encrypt_only:
                self.decryptor = seal.Decryptor(self.context, self.secret_key)

            # 创建批处理编码器
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

            # 保存私钥、重线性化密钥和Galois密钥
            if not self.encrypt_only:
                self.secret_key.save(self.private_key_file)
                self.relin_keys.save(self.relin_key_file)
                self.galois_keys.save(self.galois_key_file)

            logger.info("FHE keys saved successfully")
        except Exception as e:
            logger.error(f"Error saving FHE keys: {e}")
            raise

    def _load_keys(self):
        """加载FHE上下文和密钥"""
        try:
            # 加载加密参数
            self.parms = seal.EncryptionParameters(
                seal.scheme_type.bfv
            )  # 使用BFV方案创建参数对象

            # 从文件加载参数
            self.parms.load(self.context_file)

            # 创建上下文
            self.context = seal.SEALContext(self.parms)

            # 加载公钥
            self.public_key = seal.PublicKey()
            self.public_key.load(self.context, self.public_key_file)

            # 创建加密器和评估器
            self.encryptor = seal.Encryptor(self.context, self.public_key)
            self.evaluator = seal.Evaluator(self.context)

            # 创建批处理编码器
            self.encoder = seal.BatchEncoder(self.context)

            # 如果不是仅加密模式, 加载私钥和重线性化密钥
            if not self.encrypt_only:
                self.secret_key = seal.SecretKey()
                self.secret_key.load(self.context, self.private_key_file)

                self.relin_keys = seal.RelinKeys()
                self.relin_keys.load(self.context, self.relin_key_file)

                self.galois_keys = seal.GaloisKeys()
                if os.path.exists(self.galois_key_file):
                    self.galois_keys.load(self.context, self.galois_key_file)

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
        cached_result = self._encrypt_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            # 创建一个只包含一个值的向量
            values = np.array([value], dtype=np.int64)

            # 编码整数
            plain = self.encoder.encode(values)

            # 加密
            encrypted = self.encryptor.encrypt(plain)

            # 序列化
            serialized = encrypted.to_string()
            compressed = self.key_manager.compress_data(serialized)

            # 更新缓存
            self._encrypt_cache.put(cache_key, compressed)

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
        cached_result = self._decrypt_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

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
            self._decrypt_cache.put(cache_key, result)

            return result
        except Exception as e:
            logger.error(f"Error decrypting integer: {e}")
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
            encrypted = self.encrypt_int(ord(char))
            result.append(encrypted)
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
        for char_bytes in encrypted_chars:
            char_code = self.decrypt_int(char_bytes)
            result.append(chr(char_code))
        return "".join(result)

    def _compute_encrypted_comparison(
        self, encrypted_index_bytes: bytes, encrypted_query_bytes: bytes
    ) -> bytes:
        """
        计算两个加密值是否相等，但不解密结果
        返回加密的比较结果供用户端解密判断

        Args:
            encrypted_index_bytes: 加密的索引字节数据
            encrypted_query_bytes: 加密的查询值字节数据

        Returns:
            加密的比较结果字节数据
        """
        try:
            # 解压缩并加载索引密文
            serialized_index = self.key_manager.decompress_data(encrypted_index_bytes)
            encrypted_index = self.context.from_cipher_str(serialized_index)

            # 解压缩并加载查询密文
            serialized_query = self.key_manager.decompress_data(encrypted_query_bytes)
            encrypted_query = self.context.from_cipher_str(serialized_query)

            # 获取明文模数值
            plain_modulus = int(self.parms.plain_modulus().value())

            # 掩码生成 - 直接生成1到plain_modulus-1之间的随机数
            import secrets

            mask_value = secrets.randbelow(plain_modulus - 1) + 1

            # 创建掩码明文
            mask_plain = self.encoder.encode([mask_value])

            # 对加密索引应用掩码: E(index) * mask
            encrypted_index_masked = self.evaluator.multiply_plain(
                encrypted_index, mask_plain
            )

            # 对加密查询应用掩码: E(query) * mask
            encrypted_query_masked = self.evaluator.multiply_plain(
                encrypted_query, mask_plain
            )

            # 智能重线性化决策
            if encrypted_index_masked.size() > 2 and self.relin_keys is not None:
                self.evaluator.relinearize_inplace(
                    encrypted_index_masked, self.relin_keys
                )

            if encrypted_query_masked.size() > 2 and self.relin_keys is not None:
                self.evaluator.relinearize_inplace(
                    encrypted_query_masked, self.relin_keys
                )

            # 计算差值: E(index*mask) - E(query*mask)
            diff = self.evaluator.sub(encrypted_index_masked, encrypted_query_masked)

            # 序列化并压缩加密的比较结果
            serialized_diff = diff.to_string()
            compressed_diff = self.key_manager.compress_data(serialized_diff)

            return compressed_diff

        except Exception as e:
            logger.error(
                f"Secure comparison calculation failed: {type(e).__name__}: {str(e)}"
            )
            # 使用通用错误消息，略过详细的错误信息
            raise ValueError("Secure comparison calculation failed")

    def _decrypt_comparison_result(self, encrypted_comparison_bytes: bytes) -> bool:
        """
        解密比较结果并判断是否相等

        Args:
            encrypted_comparison_bytes: 加密的比较结果字节数据

        Returns:
            如果相等返回True, 否则返回False
        """
        if self.encrypt_only:
            raise ValueError("Cannot decrypt in encrypt-only mode")

        try:
            # 解压缩并加载比较结果密文
            serialized_comparison = self.key_manager.decompress_data(
                encrypted_comparison_bytes
            )
            encrypted_comparison = self.context.from_cipher_str(serialized_comparison)

            # 解密结果
            plain_result = self.decryptor.decrypt(encrypted_comparison)
            result_array = self.encoder.decode(plain_result)

            # 获取明文模数值
            plain_modulus = int(self.parms.plain_modulus().value())
            result = int(round(result_array[0])) % plain_modulus

            # 常量时间的零值检测
            is_zero = 1
            for i in range(0x100):
                is_zero &= ~((result >> i) & 1) & 1

            return is_zero == 1

        except Exception as e:
            logger.error(
                f"Comparison result decryption failed: {type(e).__name__}: {str(e)}"
            )
            raise ValueError("Comparison result decryption failed")

    def compare_encrypted(
        self, encrypted_index_bytes: bytes, encrypted_query_bytes: bytes
    ) -> bool:
        """
        比较两个加密值是否相等, 使用BFV单重掩码方案
        同时最大化安全性和性能，确保解密结果不被暴露

        Args:
            encrypted_index_bytes: 加密的索引字节数据
            encrypted_query_bytes: 加密的查询值字节数据

        Returns:
            如果相等返回True, 否则返回False
        """
        if self.encrypt_only:
            raise ValueError("Cannot compare in encrypt-only mode")

        try:
            # 计算加密的比较结果
            encrypted_comparison = self._compute_encrypted_comparison(
                encrypted_index_bytes, encrypted_query_bytes
            )

            # 解密比较结果
            return self._decrypt_comparison_result(encrypted_comparison)

        except Exception as e:
            logger.error(f"Secure comparison failed: {type(e).__name__}: {str(e)}")
            # 使用通用错误消息，略过详细的错误信息
            raise ValueError("Secure comparison failed")

    def clear_cache(self):
        """清除缓存"""
        self._encrypt_cache.clear()
        self._decrypt_cache.clear()

    def encrypt_for_range_query(self, value: int, bits: int = 32) -> List[bytes]:
        """
        为范围查询加密整数值

        Args:
            value: 要加密的整数
            bits: 位数, 默认32位

        Returns:
            加密后的位表示列表
        """
        # 将整数转换为二进制表示
        binary = bin(value)[2:].zfill(bits)

        # 加密每一位
        encrypted_bits = []
        for bit in binary:
            bit_value = int(bit)
            encrypted_bit = self.encrypt_int(bit_value)
            encrypted_bits.append(encrypted_bit)

        return encrypted_bits

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
        if self.encrypt_only:
            raise ValueError("Cannot compare in encrypt-only mode")

        # 将查询值转换为二进制表示
        query_binary = bin(query_value)[2:].zfill(bits)

        # 使用同态比较方法
        try:
            # 从高位到低位比较
            for i in range(bits):
                # 解压缩并加载当前位密文
                serialized = self.key_manager.decompress_data(encrypted_bits[i])
                enc_bit = self.context.from_cipher_str(serialized)

                # 获取查询值当前位
                query_bit = int(query_binary[i])

                # 创建查询位明文
                query_plain = self.encoder.encode([query_bit])

                # 如果当前位不同, 可以确定大小关系
                # 计算 enc_bit - query_bit
                diff = self.evaluator.sub_plain(enc_bit, query_plain)

                # 解密差值
                plain_diff = self.decryptor.decrypt(diff)
                diff_array = self.encoder.decode(plain_diff)
                bit_diff = int(diff_array[0])

                if bit_diff < 0:  # enc_bit < query_bit
                    return True
                elif bit_diff > 0:  # enc_bit > query_bit
                    return False

            # 如果所有位都相等, 则值相等
            return False
        except Exception as e:
            logger.error(f"Error in homomorphic less than comparison: {e}")
            raise

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
        if self.encrypt_only:
            raise ValueError("Cannot compare in encrypt-only mode")

        # 将查询值转换为二进制表示
        query_binary = bin(query_value)[2:].zfill(bits)

        # 使用同态比较方法
        try:
            # 从高位到低位比较
            for i in range(bits):
                # 解压缩并加载当前位密文
                serialized = self.key_manager.decompress_data(encrypted_bits[i])
                enc_bit = self.context.from_cipher_str(serialized)

                # 获取查询值当前位
                query_bit = int(query_binary[i])

                # 创建查询位明文
                query_plain = self.encoder.encode([query_bit])

                # 如果当前位不同, 可以确定大小关系
                # 计算 enc_bit - query_bit
                diff = self.evaluator.sub_plain(enc_bit, query_plain)

                # 解密差值
                plain_diff = self.decryptor.decrypt(diff)
                diff_array = self.encoder.decode(plain_diff)
                bit_diff = int(diff_array[0])

                if bit_diff > 0:  # enc_bit > query_bit
                    return True
                elif bit_diff < 0:  # enc_bit < query_bit
                    return False

            # 如果所有位都相等, 则值相等
            return False
        except Exception as e:
            logger.error(f"Error in homomorphic greater than comparison: {e}")
            raise

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
        if self.encrypt_only:
            raise ValueError("Cannot compare in encrypt-only mode")

        # 检查下限
        if min_value is not None:
            less_than_min = self.compare_less_than(encrypted_bits, min_value, bits)
            if less_than_min:
                return False

        # 检查上限
        if max_value is not None:
            greater_than_max = self.compare_greater_than(
                encrypted_bits, max_value, bits
            )
            if greater_than_max:
                return False

        return True

    def batch_encrypt_int(self, values: List[int]) -> List[bytes]:
        """
        批量加密整数值

        Args:
            values: 要加密的整数列表

        Returns:
            加密后的字节列表
        """
        result = []
        for value in values:
            encrypted = self.encrypt_int(value)
            result.append(encrypted)
        return result

    def batch_decrypt_int(self, encrypted_values: List[bytes]) -> List[int]:
        """
        批量解密整数值

        Args:
            encrypted_values: 加密的字节列表

        Returns:
            解密后的整数列表
        """
        if self.encrypt_only:
            raise ValueError("Cannot decrypt in encrypt-only mode")

        result = []
        for encrypted in encrypted_values:
            decrypted = self.decrypt_int(encrypted)
            result.append(decrypted)
        return result
