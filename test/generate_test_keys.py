"""
测试密钥生成脚本 - 生成测试用的加密密钥
"""

import os
import sys
import logging
from test_config import TEST_KEY_CONFIG, PROJECT_ROOT

# 添加项目根目录到Python路径
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目模块
try:
    from crypto.key_manager import KeyManager
    from crypto.aes import AESManager
    from crypto.fhe import FHEManager
except ImportError as e:
    logger = logging.getLogger("测试密钥生成")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确，并且已安装所有依赖")
    sys.exit(1)

logger = logging.getLogger("测试密钥生成")


def generate_test_keys():
    """生成测试用的加密密钥"""
    try:
        logger.info("开始生成测试密钥...")

        # 确保密钥目录存在
        keys_dir = TEST_KEY_CONFIG["keys_dir"]
        os.makedirs(keys_dir, exist_ok=True)

        # 初始化密钥管理器
        key_manager = KeyManager(keys_dir)

        # 生成AES密钥
        logger.info("生成AES密钥...")
        aes_manager = AESManager()
        aes_key = aes_manager.get_key()

        # 保存AES密钥
        aes_key_path = os.path.join(keys_dir, TEST_KEY_CONFIG["aes_key_file"])
        key_manager.save_aes_key(aes_key, aes_key_path, TEST_KEY_CONFIG["password"])
        logger.info(f"AES密钥已保存: {aes_key_path}")

        # 初始化FHE管理器并生成密钥
        logger.info("生成FHE密钥...")
        fhe_manager = FHEManager({"key_size": 2048, "precision": 40}, key_manager)

        # 保存FHE密钥
        public_key_path = os.path.join(keys_dir, TEST_KEY_CONFIG["fhe_public_key"])
        private_key_path = os.path.join(keys_dir, TEST_KEY_CONFIG["fhe_private_key"])

        key_manager.save_fhe_keys(
            fhe_manager.public_key,
            fhe_manager.private_key,
            public_key_path,
            private_key_path,
            TEST_KEY_CONFIG["password"],
        )

        logger.info(f"FHE密钥已生成并保存在: {keys_dir}")
        logger.info("测试密钥生成完成")
        return True

    except Exception as e:
        logger.error(f"测试密钥生成失败: {e}")
        return False


if __name__ == "__main__":
    success = generate_test_keys()
    sys.exit(0 if success else 1)
