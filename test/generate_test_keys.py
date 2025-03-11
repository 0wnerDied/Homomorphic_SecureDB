"""
测试密钥生成脚本 - 生成测试用的加密密钥
"""

import os
import sys
import logging
from test_config import TEST_KEY_CONFIG, PROJECT_ROOT

# 添加项目根目录到Python路径
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目配置和模块
try:
    from core.config import ENCRYPTION_CONFIG
    from crypto.key_manager import KeyManager
    from crypto.aes import AESManager
    from crypto.fhe import FHEManager
except ImportError as e:
    logger = logging.getLogger("测试密钥生成")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确, 并且已安装所有依赖")
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

        # 使用主配置中的 FHE 配置, 并修改密钥文件名
        logger.info("生成FHE密钥...")
        fhe_config = ENCRYPTION_CONFIG["fhe"].copy()  # 复制一份以避免修改原配置

        # 添加密钥文件名配置
        fhe_config.update(
            {
                "context_file": "context.con",
                "public_key_file": TEST_KEY_CONFIG["fhe_public_key"],
                "private_key_file": TEST_KEY_CONFIG["fhe_private_key"],
                "relin_key_file": "relin.key",
            }
        )

        # 初始化FHE管理器并生成密钥
        fhe_manager = FHEManager(fhe_config, key_manager)

        logger.info(f"FHE密钥已生成并保存在: {keys_dir}")
        logger.info("测试密钥生成完成")
        return True

    except Exception as e:
        logger.error(f"测试密钥生成失败: {e}")
        return False


if __name__ == "__main__":
    success = generate_test_keys()
    sys.exit(0 if success else 1)
