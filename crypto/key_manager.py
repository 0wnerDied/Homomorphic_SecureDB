"""
密钥管理模块 - 处理FHE和AES密钥的生成、存储和加载
"""

import os
import pickle
import logging
import datetime
import tarfile
import tempfile
import shutil
from typing import Tuple, Optional

import zstandard as zstd
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

logger = logging.getLogger(__name__)


class KeyManager:
    """密钥管理器, 处理FHE和AES密钥的安全存储和加载"""

    def __init__(self, keys_dir: str):
        """
        初始化密钥管理器

        Args:
            keys_dir: 密钥存储目录
        """
        self.keys_dir = keys_dir
        os.makedirs(keys_dir, exist_ok=True)
        logger.info(f"Key manager initialized with directory: {keys_dir}")

        # 压缩器
        self.compressor = zstd.ZstdCompressor(level=9)
        self.decompressor = zstd.ZstdDecompressor()

    def get_key_path(self, filename: str) -> str:
        """
        获取密钥文件的完整路径

        Args:
            filename: 密钥文件名

        Returns:
            密钥文件的完整路径
        """
        return os.path.join(self.keys_dir, filename)

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

    # ===== AES密钥管理功能 =====

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
            encrypted_data: 加密的数据 (IV + 加密密钥) 
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

            # 准备保存的数据 (salt + encrypted_key) 
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

    # ===== FHE密钥对管理功能 =====

    def save_fhe_keys(
        self,
        public_key: bytes,
        secret_key: bytes,
        public_key_file: str,
        secret_key_file: str,
        password: Optional[str] = None,
    ) -> None:
        """
        保存FHE密钥对

        Args:
            public_key: 公钥数据
            secret_key: 私钥数据
            public_key_file: 公钥文件名
            secret_key_file: 私钥文件名
            password: 如果提供, 将使用此密码加密私钥
        """
        try:
            # 压缩公钥
            compressed_public_key = self.compress_data(public_key)
            self.save_file(compressed_public_key, public_key_file)

            # 处理私钥 (可选加密) 
            compressed_secret_key = self.compress_data(secret_key)

            if password:
                # 生成AES密钥用于加密私钥
                aes_key = get_random_bytes(32)

                # 使用AES密钥加密压缩后的私钥
                cipher = AES.new(aes_key, AES.MODE_CBC)
                iv = cipher.iv
                encrypted_key = cipher.encrypt(
                    pad(compressed_secret_key, AES.block_size)
                )

                # 将IV和加密数据合并
                encrypted_data = iv + encrypted_key

                # 保存加密的私钥
                self.save_file(encrypted_data, secret_key_file)

                # 保存用于解密私钥的AES密钥 (本身也是加密的) 
                aes_key_file = f"{os.path.splitext(secret_key_file)[0]}_aes.key"
                self.save_aes_key(aes_key, aes_key_file, password)

                logger.info(f"Saved encrypted FHE secret key to {secret_key_file}")
            else:
                # 不加密, 直接保存压缩的私钥
                self.save_file(compressed_secret_key, secret_key_file)
                logger.info(f"Saved unencrypted FHE secret key to {secret_key_file}")

            logger.info(f"Saved FHE public key to {public_key_file}")

        except Exception as e:
            logger.error(f"Error saving FHE keys: {e}")
            raise

    def load_fhe_public_key(self, public_key_file: str) -> bytes:
        """
        加载FHE公钥

        Args:
            public_key_file: 公钥文件名

        Returns:
            解压缩后的公钥数据
        """
        try:
            compressed_public_key = self.load_file(public_key_file)
            public_key = self.decompress_data(compressed_public_key)
            logger.info(f"Loaded FHE public key from {public_key_file}")
            return public_key
        except Exception as e:
            logger.error(f"Error loading FHE public key: {e}")
            raise

    def load_fhe_secret_key(
        self, secret_key_file: str, password: Optional[str] = None
    ) -> bytes:
        """
        加载FHE私钥

        Args:
            secret_key_file: 私钥文件名
            password: 如果私钥已加密, 需提供密码

        Returns:
            解压缩后的私钥数据
        """
        try:
            encrypted_data = self.load_file(secret_key_file)

            # 检查是否需要解密
            aes_key_file = f"{os.path.splitext(secret_key_file)[0]}_aes.key"
            if os.path.exists(self.get_key_path(aes_key_file)):
                if not password:
                    raise ValueError("Password required to decrypt FHE secret key")

                # 加载AES密钥
                aes_key = self.load_aes_key(aes_key_file, password)

                # 解密私钥
                iv = encrypted_data[:16]
                encrypted_key = encrypted_data[16:]

                cipher = AES.new(aes_key, AES.MODE_CBC, iv=iv)
                compressed_secret_key = unpad(
                    cipher.decrypt(encrypted_key), AES.block_size
                )
            else:
                # 私钥未加密
                compressed_secret_key = encrypted_data

            # 解压缩私钥
            secret_key = self.decompress_data(compressed_secret_key)
            logger.info(f"Loaded FHE secret key from {secret_key_file}")
            return secret_key

        except Exception as e:
            logger.error(f"Error loading FHE secret key: {e}")
            raise

    def rotate_fhe_keys(
        self,
        old_public_key_file: str,
        old_secret_key_file: str,
        new_public_key: bytes,
        new_secret_key: bytes,
        new_public_key_file: str,
        new_secret_key_file: str,
        password: Optional[str] = None,
    ) -> None:
        """
        轮换FHE密钥对 (保存新密钥并备份旧密钥) 

        Args:
            old_public_key_file: 旧公钥文件名
            old_secret_key_file: 旧私钥文件名
            new_public_key: 新公钥数据
            new_secret_key: 新私钥数据
            new_public_key_file: 新公钥文件名
            new_secret_key_file: 新私钥文件名
            password: 如果提供, 将使用此密码加密新私钥
        """
        try:
            # 备份旧密钥
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_public_key_file = f"{old_public_key_file}.{timestamp}.bak"
            backup_secret_key_file = f"{old_secret_key_file}.{timestamp}.bak"

            # 复制旧密钥文件
            old_public_key_path = self.get_key_path(old_public_key_file)
            old_secret_key_path = self.get_key_path(old_secret_key_file)

            if os.path.exists(old_public_key_path):
                shutil.copy2(
                    old_public_key_path, self.get_key_path(backup_public_key_file)
                )

            if os.path.exists(old_secret_key_path):
                shutil.copy2(
                    old_secret_key_path, self.get_key_path(backup_secret_key_file)
                )

                # 如果旧私钥有关联的AES密钥, 也要备份
                old_aes_key_file = f"{os.path.splitext(old_secret_key_file)[0]}_aes.key"
                old_aes_key_path = self.get_key_path(old_aes_key_file)
                if os.path.exists(old_aes_key_path):
                    backup_aes_key_file = f"{old_aes_key_file}.{timestamp}.bak"
                    shutil.copy2(
                        old_aes_key_path, self.get_key_path(backup_aes_key_file)
                    )

            # 保存新密钥
            self.save_fhe_keys(
                new_public_key,
                new_secret_key,
                new_public_key_file,
                new_secret_key_file,
                password,
            )

            logger.info(
                f"Rotated FHE keys. Old keys backed up with timestamp {timestamp}"
            )

        except Exception as e:
            logger.error(f"Error rotating FHE keys: {e}")
            raise

    # ===== 数据压缩功能 =====

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

    # ===== 备份和恢复功能 =====

    def generate_backup(self, backup_dir: Optional[str] = None) -> str:
        """
        生成密钥备份

        Args:
            backup_dir: 备份目录, 如果为None则使用默认目录

        Returns:
            备份文件路径
        """
        try:
            # 确定备份目录
            if backup_dir is None:
                backup_dir = os.path.join(os.path.dirname(self.keys_dir), "backups")

            os.makedirs(backup_dir, exist_ok=True)

            # 创建备份文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"keys_backup_{timestamp}.tar.gz")

            # 创建tar文件
            with tarfile.open(backup_file, "w:gz") as tar:
                # 添加密钥目录中的所有文件
                for filename in os.listdir(self.keys_dir):
                    file_path = os.path.join(self.keys_dir, filename)
                    if os.path.isfile(file_path):
                        tar.add(file_path, arcname=filename)

            logger.info(f"Key backup created at {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Error creating key backup: {e}")
            raise

    def restore_backup(self, backup_file: str, password: Optional[str] = None) -> None:
        """
        从备份恢复密钥

        Args:
            backup_file: 备份文件路径
            password: 如果提供, 将验证密钥是否可以使用此密码解密
        """
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()

            try:
                # 解压备份文件到临时目录
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(path=temp_dir)

                # 如果提供了密码, 验证AES密钥
                if password is not None:
                    # 查找AES密钥文件
                    aes_key_files = [
                        f for f in os.listdir(temp_dir) if f.endswith(".key")
                    ]
                    if aes_key_files:
                        # 尝试使用密码加载AES密钥
                        try:
                            temp_key_manager = KeyManager(temp_dir)
                            temp_key_manager.load_aes_key(aes_key_files[0], password)
                        except Exception as e:
                            raise ValueError(
                                f"Failed to decrypt key with provided password: {e}"
                            )

                # 复制文件到密钥目录
                for filename in os.listdir(temp_dir):
                    src_path = os.path.join(temp_dir, filename)
                    dst_path = os.path.join(self.keys_dir, filename)
                    if os.path.isfile(src_path):
                        shutil.copy2(src_path, dst_path)

                logger.info(f"Keys restored from backup {backup_file}")
            finally:
                # 清理临时目录
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Error restoring keys from backup: {e}")
            raise
