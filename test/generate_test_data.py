"""
测试数据生成脚本 - 生成民航客户隐私数据测试记录
"""

import os
import sys
import json
import random
import logging
import string
from test_config import (
    TEST_DATA_CONFIG,
    PRIVACY_DATA_TYPES,
    PROJECT_ROOT,
    TEST_KEY_CONFIG,
    AIRLINES,
    CITIES,
    TRAVEL_PURPOSES,
    SEAT_PREFERENCES,
    SPECIAL_SERVICES,
    FREQUENT_FLYER_TIERS,
    PAYMENT_METHODS,
)

# 添加项目根目录到Python路径
sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目模块
try:
    from core.secure_db import SecureDB
except ImportError as e:
    logger = logging.getLogger("测试数据生成")
    logger.error(f"导入项目模块失败: {e}")
    logger.error("请确保项目结构正确，并且已安装所有依赖")
    sys.exit(1)

logger = logging.getLogger("测试数据生成")


def generate_random_name():
    """生成随机姓名"""
    surnames = [
        "王",
        "李",
        "张",
        "刘",
        "陈",
        "杨",
        "黄",
        "赵",
        "吴",
        "周",
        "徐",
        "孙",
        "马",
        "朱",
        "胡",
        "林",
        "郭",
        "何",
        "高",
        "罗",
    ]
    names = [
        "伟",
        "芳",
        "娜",
        "秀英",
        "敏",
        "静",
        "丽",
        "强",
        "磊",
        "洋",
        "艳",
        "勇",
        "军",
        "杰",
        "娟",
        "涛",
        "明",
        "超",
        "秀兰",
        "霞",
    ]

    return random.choice(surnames) + random.choice(names)


def generate_random_phone():
    """生成随机手机号"""
    prefixes = [
        "130",
        "131",
        "132",
        "133",
        "134",
        "135",
        "136",
        "137",
        "138",
        "139",
        "150",
        "151",
        "152",
        "153",
        "155",
        "156",
        "157",
        "158",
        "159",
        "170",
        "171",
        "172",
        "173",
        "175",
        "176",
        "177",
        "178",
        "179",
        "180",
        "181",
        "182",
        "183",
        "184",
        "185",
        "186",
        "187",
        "188",
        "189",
    ]

    return random.choice(prefixes) + "".join(random.choices("0123456789", k=8))


def generate_random_email(name):
    """根据姓名生成随机邮箱"""
    domains = [
        "qq.com",
        "163.com",
        "126.com",
        "gmail.com",
        "outlook.com",
        "hotmail.com",
        "sina.com",
        "sohu.com",
        "yahoo.com",
    ]
    pinyin_map = {
        "王": "wang",
        "李": "li",
        "张": "zhang",
        "刘": "liu",
        "陈": "chen",
        "杨": "yang",
        "黄": "huang",
        "赵": "zhao",
        "吴": "wu",
        "周": "zhou",
        "伟": "wei",
        "芳": "fang",
        "娜": "na",
        "秀英": "xiuying",
        "敏": "min",
        "静": "jing",
        "丽": "li",
        "强": "qiang",
        "磊": "lei",
        "洋": "yang",
    }

    first_char = name[0]
    pinyin = pinyin_map.get(first_char, "user")

    # 添加随机数字
    pinyin += str(random.randint(100, 9999))

    return f"{pinyin}@{random.choice(domains)}"


def generate_random_id_card():
    """生成随机身份证号"""
    # 省份代码
    province_code = random.choice(
        [
            "11",
            "12",
            "13",
            "14",
            "15",
            "21",
            "22",
            "23",
            "31",
            "32",
            "33",
            "34",
            "35",
            "36",
            "37",
            "41",
            "42",
            "43",
            "44",
            "45",
            "46",
            "50",
            "51",
            "52",
            "53",
            "54",
            "61",
            "62",
            "63",
            "64",
            "65",
        ]
    )

    # 地区代码
    city_code = f"{random.randint(0, 9)}{random.randint(0, 9)}"

    # 区县代码
    district_code = f"{random.randint(0, 9)}{random.randint(0, 9)}"

    # 出生日期
    year = random.randint(1950, 2003)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # 简化处理，避免月份天数问题
    birth_date = f"{year}{month:02d}{day:02d}"

    # 顺序码
    sequence = f"{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"

    # 校验码（简化处理，实际应该根据前17位计算）
    check_code = random.choice("0123456789X")

    return (
        f"{province_code}{city_code}{district_code}{birth_date}{sequence}{check_code}"
    )


def generate_random_passport():
    """生成随机护照号"""
    # 中国护照号码通常为E开头加8位数字
    return f"E{''.join(random.choices('0123456789', k=8))}"


def generate_random_credit_card():
    """生成随机信用卡号（模拟）"""
    # 常见信用卡前缀
    prefixes = ["4", "5", "6"]  # Visa, MasterCard, 银联等

    # 生成16位卡号
    prefix = random.choice(prefixes)
    remaining_digits = "".join(random.choices("0123456789", k=15))

    return f"{prefix}{remaining_digits}"


def generate_random_date(start_year=2020, end_year=2025):
    """生成随机日期"""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # 简化处理，避免月份天数问题

    return f"{year}-{month:02d}-{day:02d}"


def generate_privacy_test_data(customer_id: int) -> str:
    """生成民航客户隐私数据"""
    data_type = random.choice(PRIVACY_DATA_TYPES)

    # 生成通用的客户姓名，用于各种数据类型
    customer_name = generate_random_name()

    if data_type == "个人基本信息":
        data = {
            "customer_id": customer_id,  # 用作索引
            "type": "个人基本信息",
            "name": customer_name,
            "gender": random.choice(["男", "女"]),
            "birth_date": generate_random_date(1960, 2005),
            "nationality": "中国",
            "marital_status": random.choice(["未婚", "已婚", "离异", "丧偶"]),
            "occupation": random.choice(
                [
                    "工程师",
                    "教师",
                    "医生",
                    "学生",
                    "商人",
                    "公务员",
                    "自由职业",
                    "退休",
                    "其他",
                ]
            ),
            "education": random.choice(
                ["高中", "大专", "本科", "硕士", "博士", "其他"]
            ),
            "annual_income": random.choice(
                ["10万以下", "10-30万", "30-50万", "50-100万", "100万以上", "保密"]
            ),
        }

    elif data_type == "联系方式":
        data = {
            "customer_id": customer_id,  # 用作索引
            "type": "联系方式",
            "name": customer_name,
            "mobile_phone": generate_random_phone(),
            "email": generate_random_email(customer_name),
            "home_address": f"{random.choice(CITIES)}市{random.choice(['东', '西', '南', '北', '中'])}区{random.randint(1, 100)}号",
            "work_address": f"{random.choice(CITIES)}市{random.choice(['高新', '经济', '科技', '文化'])}区{random.choice(['创业', '科技', '商务', '金融'])}中心{random.randint(1, 50)}楼",
            "postal_code": f"{random.randint(100000, 999999)}",
            "emergency_contact": generate_random_name(),
            "emergency_phone": generate_random_phone(),
            "preferred_contact_method": random.choice(["手机", "邮箱", "微信", "短信"]),
        }

    elif data_type == "证件信息":
        # 随机选择证件类型
        id_type = random.choice(
            ["身份证", "护照", "港澳通行证", "台湾通行证", "外国人永久居留证"]
        )

        if id_type == "身份证":
            id_number = generate_random_id_card()
        elif id_type == "护照":
            id_number = generate_random_passport()
        else:
            # 其他证件类型，生成通用格式
            id_number = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=9)
            )

        data = {
            "customer_id": customer_id,  # 用作索引
            "type": "证件信息",
            "name": customer_name,
            "id_type": id_type,
            "id_number": id_number,
            "issue_date": generate_random_date(2015, 2022),
            "expiry_date": generate_random_date(2023, 2033),
            "issuing_authority": random.choice(
                ["公安局", "出入境管理局", "外交部", "移民局"]
            ),
            "issuing_place": random.choice(CITIES),
            "verification_status": random.choice(
                ["已验证", "未验证", "验证中", "验证失败"]
            ),
        }

    elif data_type == "旅行偏好":
        data = {
            "customer_id": customer_id,  # 用作索引
            "type": "旅行偏好",
            "name": customer_name,
            "preferred_airlines": random.sample(
                [airline["code"] for airline in AIRLINES], k=random.randint(1, 3)
            ),
            "seat_preference": random.choice(SEAT_PREFERENCES),
            "meal_preference": random.choice(
                [
                    "普通餐",
                    "素食",
                    "清真餐",
                    "儿童餐",
                    "糖尿病餐",
                    "低盐餐",
                    "无特殊要求",
                ]
            ),
            "travel_purpose": random.choice(TRAVEL_PURPOSES),
            "travel_frequency": random.choice(["频繁", "经常", "偶尔", "很少"]),
            "preferred_cabin_class": random.choice(
                ["经济舱", "经济舱优选", "商务舱", "头等舱"]
            ),
            "special_service_request": random.choice(SPECIAL_SERVICES),
            "preferred_departure_time": random.choice(
                ["早晨", "上午", "下午", "晚上", "深夜", "无特殊要求"]
            ),
            "preferred_destinations": random.sample(CITIES, k=random.randint(1, 5)),
        }

    elif data_type == "支付信息":
        # 随机选择支付方式
        payment_method = random.choice(PAYMENT_METHODS)

        # 根据支付方式生成不同的支付详情
        if payment_method in ["信用卡", "借记卡"]:
            payment_details = {
                "card_type": random.choice(
                    ["Visa", "MasterCard", "UnionPay", "American Express", "JCB"]
                ),
                "card_number": generate_random_credit_card(),
                "card_holder": customer_name,
                "expiry_date": f"{random.randint(1, 12):02d}/{random.randint(23, 30)}",
                "billing_address": f"{random.choice(CITIES)}市{random.choice(['东', '西', '南', '北', '中'])}区{random.randint(1, 100)}号",
            }
        elif payment_method in ["支付宝", "微信支付"]:
            payment_details = {
                "account": (
                    generate_random_phone()
                    if random.random() < 0.5
                    else generate_random_email(customer_name)
                ),
                "account_name": customer_name,
            }
        else:
            payment_details = {
                "account_type": payment_method,
                "reference": f"REF-{random.randint(10000, 99999)}",
            }

        data = {
            "customer_id": customer_id,  # 用作索引
            "type": "支付信息",
            "name": customer_name,
            "preferred_payment_method": payment_method,
            "payment_details": payment_details,
            "billing_currency": random.choice(["CNY", "USD", "EUR", "JPY", "GBP"]),
            "auto_payment": random.choice([True, False]),
            "last_payment_date": generate_random_date(2022, 2023),
            "invoice_preference": random.choice(["电子邮件", "短信", "邮寄", "不接收"]),
            "tax_id": random.choice([None, f"TAX{random.randint(100000, 999999)}"]),
            "payment_verification_status": random.choice(
                ["已验证", "未验证", "验证中"]
            ),
        }

    else:  # 常旅客信息
        # 随机选择一个航空公司
        airline = random.choice(AIRLINES)

        data = {
            "customer_id": customer_id,  # 用作索引
            "type": "常旅客信息",
            "name": customer_name,
            "airline_code": airline["code"],
            "airline_name": airline["name"],
            "frequent_flyer_number": f"{airline['code']}{random.randint(10000000, 99999999)}",
            "membership_tier": random.choice(FREQUENT_FLYER_TIERS),
            "enrollment_date": generate_random_date(2010, 2023),
            "miles_balance": random.randint(0, 1000000),
            "tier_expiry_date": generate_random_date(2024, 2026),
            "lifetime_miles": random.randint(0, 5000000),
            "recent_flights": random.randint(0, 50),
            "partner_airlines": random.sample(
                [a["code"] for a in AIRLINES if a != airline], k=random.randint(0, 3)
            ),
            "special_privileges": random.sample(
                ["优先登机", "额外行李", "贵宾休息室", "优先升舱", "专属服务热线"],
                k=random.randint(0, 3),
            ),
            "status_match_eligibility": random.choice([True, False]),
        }

    return json.dumps(data, ensure_ascii=False)


def generate_test_records():
    """生成测试记录"""
    try:
        logger.info(
            f"开始生成 {TEST_DATA_CONFIG['record_count']} 条民航客户隐私数据测试记录..."
        )

        # 初始化安全数据库系统，使用测试配置
        secure_db = SecureDB(
            load_keys=True,
            cache_size=TEST_DATA_CONFIG["cache_size"],
            keys_dir=TEST_KEY_CONFIG["keys_dir"],
        )

        # 批量添加记录
        batch_size = min(
            TEST_DATA_CONFIG["batch_size"], TEST_DATA_CONFIG["record_count"]
        )
        batches = []

        for i in range(0, TEST_DATA_CONFIG["record_count"], batch_size):
            batch = []
            for j in range(batch_size):
                if i + j < TEST_DATA_CONFIG["record_count"]:
                    customer_id = random.randint(*TEST_DATA_CONFIG["index_range"])
                    data = generate_privacy_test_data(customer_id)
                    # 对客户ID启用范围查询
                    enable_range = True
                    batch.append((customer_id, data, enable_range))
            batches.append(batch)

        # 执行批量添加
        record_ids = []
        total_added = 0

        for i, batch in enumerate(batches):
            logger.info(f"添加批次 {i+1}/{len(batches)}，包含 {len(batch)} 条记录")
            batch_ids = secure_db.add_records_batch(batch)
            record_ids.extend(batch_ids)
            total_added += len(batch_ids)

        logger.info(f"成功生成 {total_added} 条测试记录")

        # 保存记录ID列表，以便后续测试使用
        record_ids_file = os.path.join(PROJECT_ROOT, "test", "record_ids.json")
        with open(record_ids_file, "w") as f:
            json.dump(record_ids, f)
        logger.info(f"记录ID列表已保存: {record_ids_file}")

        return True

    except Exception as e:
        logger.error(f"生成测试记录失败: {e}")
        return False


if __name__ == "__main__":
    success = generate_test_records()
    sys.exit(0 if success else 1)
