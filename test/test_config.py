"""
测试环境配置 - 民航客户隐私数据安全数据库系统
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# 测试数据库配置
TEST_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "privacy_db_test",
    "password": "privacy_test_pwd",
    "database": "aviation_privacy_test",
    "admin_user": "0wnerd1ed",  # 使用标准的PostgreSQL管理员用户
    "admin_password": "",
}

# 管理员数据库连接字符串 (连接到postgres数据库) 
ADMIN_DB_CONNECTION_STRING = f"postgresql://{TEST_DB_CONFIG['admin_user']}:{TEST_DB_CONFIG['admin_password']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/postgres"

# 测试数据库连接字符串 (连接到测试数据库) 
TEST_DB_CONNECTION_STRING = f"postgresql://{TEST_DB_CONFIG['user']}:{TEST_DB_CONFIG['password']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"

# 测试数据配置
TEST_DATA_CONFIG = {
    "record_count": 100,  # 要生成的记录数量
    "batch_size": 10,  # 批量操作的大小
    "export_file": os.path.join(PROJECT_ROOT, "test", "test_export.json"),
    "index_range": (100000, 999999),  # 索引值范围 (客户ID范围) 
    "cache_size": 50,  # 测试用缓存大小
}

# 测试密钥配置
TEST_KEY_CONFIG = {
    "keys_dir": os.path.join(PROJECT_ROOT, "test", "keys"),
    "aes_key_file": "test_aes.key",
    "fhe_public_key": "test_fhe_public.key",
    "fhe_private_key": "test_fhe_private.key",
    "password": "privacy_secure_pwd",  # 用于加密密钥的密码
}

# 测试日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, "test", "test.log")),
        logging.StreamHandler(),
    ],
)

# 民航客户隐私数据类型
PRIVACY_DATA_TYPES = [
    "个人基本信息",
    "联系方式",
    "证件信息",
    "旅行偏好",
    "支付信息",
    "常旅客信息",
]

# 航空公司代码
AIRLINES = [
    {"code": "CA", "name": "中国国际航空"},
    {"code": "MU", "name": "中国东方航空"},
    {"code": "CZ", "name": "中国南方航空"},
    {"code": "HU", "name": "海南航空"},
    {"code": "3U", "name": "四川航空"},
    {"code": "MF", "name": "厦门航空"},
    {"code": "ZH", "name": "深圳航空"},
    {"code": "KN", "name": "中国联合航空"},
    {"code": "SC", "name": "山东航空"},
    {"code": "FM", "name": "上海航空"},
]

# 常用城市
CITIES = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "成都",
    "重庆",
    "杭州",
    "武汉",
    "西安",
    "南京",
    "天津",
    "苏州",
    "郑州",
    "长沙",
    "青岛",
    "沈阳",
    "宁波",
    "东莞",
    "无锡",
    "济南",
]

# 常见旅行目的
TRAVEL_PURPOSES = ["商务", "休闲", "探亲", "学习", "医疗", "会议", "展览", "其他"]

# 常见座位偏好
SEAT_PREFERENCES = ["靠窗", "靠走道", "中间", "前排", "后排", "紧急出口", "无偏好"]

# 特殊服务需求
SPECIAL_SERVICES = [
    "轮椅服务",
    "婴儿摇篮",
    "特殊餐食",
    "无人陪伴儿童",
    "医疗协助",
    "导盲犬",
    "无",
]

# 常旅客等级
FREQUENT_FLYER_TIERS = [
    "普通会员",
    "银卡会员",
    "金卡会员",
    "白金会员",
    "黑金会员",
    "终身会员",
    "非会员",
]

# 支付方式
PAYMENT_METHODS = [
    "信用卡",
    "借记卡",
    "支付宝",
    "微信支付",
    "银联",
    "PayPal",
    "现金",
    "积分兑换",
    "企业支付",
]
