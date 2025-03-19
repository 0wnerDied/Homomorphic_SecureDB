"""
同态加密模块 - 使用SEAL-Python库实现BFV方案
"""

import seal
import os
import logging
import random
import time
import xxhash
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

    def compare_encrypted(self, encrypted_bytes: bytes, query_value: int) -> bool:
        """
        比较加密索引与查询值是否相等, 使用BFV单重掩码方案
        同时最大化安全性和性能

        Args:
            encrypted_bytes: 加密的索引字节数据
            query_value: 要比较的查询值

        Returns:
            如果相等返回True, 否则返回False
        """
        if self.encrypt_only:
            raise ValueError("Cannot compare in encrypt-only mode")

        try:
            # 解压缩并加载密文
            serialized = self.key_manager.decompress_data(encrypted_bytes)
            encrypted = self.context.from_cipher_str(serialized)

            # 获取明文模数值
            plain_modulus = int(self.parms.plain_modulus().value())

            # 使用会话相关的种子
            session_seed = int(time.time() * 1000) & 0xFFFFFFFF

            # 生成高强度掩码
            # 使用会话种子和查询值生成掩码基础
            query_bytes = str(query_value).encode()
            # 混合随机熵增强安全性
            entropy = os.urandom(16)

            # 多层哈希增强安全性
            base_hash1 = xxhash.xxh64(
                query_bytes + entropy, seed=session_seed
            ).intdigest()
            base_hash2 = xxhash.xxh64(
                str(base_hash1).encode(), seed=session_seed ^ 0xDEADBEEF
            ).intdigest()

            # 复杂掩码生成
            mask_candidate = (
                (base_hash1 ^ base_hash2)
                ^ ((base_hash1 >> 13) | (base_hash2 << 7))
                ^ ((query_value * 0xC6A4A7935BD1E995 + base_hash2) & 0xFFFFFFFFFFFFFFFF)
            ) % (plain_modulus - 1) + 1

            # 确保掩码与明文模数互质
            def extended_gcd(a, b):
                """扩展欧几里得算法，计算最大公约数和贝祖系数"""
                if a == 0:
                    return (b, 0, 1)
                else:
                    gcd, x, y = extended_gcd(b % a, a)
                    return (gcd, y - (b // a) * x, x)

            def mod_inverse(a, m):
                """计算模逆元，确保掩码可逆"""
                gcd, x, y = extended_gcd(a, m)
                if gcd != 1:
                    return None
                else:
                    return x % m

            # 寻找与明文模数互质且有模逆元的掩码值
            mask_value = mask_candidate
            while True:
                if mod_inverse(mask_value, plain_modulus) is not None:
                    break
                mask_value = (mask_value + 1) % plain_modulus
                if mask_value == 0:
                    mask_value = 1

            # 创建掩码明文
            mask_plain = self.encoder.encode([mask_value])

            # 计算掩码查询值: query * mask mod plain_modulus
            masked_query = (query_value * mask_value) % plain_modulus
            masked_query_plain = self.encoder.encode([masked_query])

            # 对加密索引应用掩码: E(index) * mask
            encrypted_masked = self.evaluator.multiply_plain(encrypted, mask_plain)

            # 智能重线性化决策, 检查是否需要重线性化
            ciphertext_size = encrypted_masked.size()
            if ciphertext_size > 2 and self.relin_keys is not None:
                # 只有当密文大小超过2且有重线性化密钥时才执行
                self.evaluator.relinearize_inplace(encrypted_masked, self.relin_keys)

            # 计算差值: E(index*mask) - (query*mask)
            diff = self.evaluator.sub_plain(encrypted_masked, masked_query_plain)

            # 安全性增强: 添加随机噪声掩码
            # 如果 index == query，则 diff = 0
            # 如果 index != query，则 diff != 0
            # 我们可以安全地添加 r*plain_modulus 到差值, 不会影响结果, 因为在BFV中, 任何 plain_modulus 的倍数在解密后都等于0
            # 生成随机噪声 (r*plain_modulus)
            noise_factor = random.randint(1, 10)  # 小范围足够
            noise_plain = self.encoder.encode([noise_factor * plain_modulus])
            # 添加噪声: diff + r*plain_modulus
            # 不会改变比较结果, 混淆真实差值
            diff = self.evaluator.add_plain(diff, noise_plain)

            # 解密结果
            plain_result = self.decryptor.decrypt(diff)

            # 解码结果
            result_array = self.encoder.decode(plain_result)

            # BFV精确检查, 取模以处理可能的噪声掩码
            result = int(round(result_array[0])) % plain_modulus
            return result == 0

        except Exception as e:
            logger.error(f"Secure comparison failed: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Secure comparison failed: {type(e).__name__}")

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
