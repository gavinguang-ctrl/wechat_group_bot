"""配置模块 - 所有可调参数集中管理"""

import os
from datetime import date

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================== 路径配置 ====================
# 群二维码图片根目录（内含按日期分的子文件夹）
QR_CODE_ROOT = r"C:\Users\gavin\xhs_qr_scraper\data\qr_codes"
# 默认扫描今天的文件夹，如不存在则取最新的子文件夹
_today_dir = os.path.join(QR_CODE_ROOT, date.today().isoformat())
if os.path.isdir(_today_dir):
    QR_CODE_DIR = _today_dir
else:
    # 取最新的日期文件夹
    _subs = sorted(
        [d for d in os.listdir(QR_CODE_ROOT)
         if os.path.isdir(os.path.join(QR_CODE_ROOT, d))],
        reverse=True,
    )
    QR_CODE_DIR = os.path.join(QR_CODE_ROOT, _subs[0]) if _subs else QR_CODE_ROOT

# 消息模板文件夹
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# 默认消息模板文件
DEFAULT_TEMPLATE = os.path.join(TEMPLATE_DIR, "default.txt")

# 运行日志文件
LOG_FILE = os.path.join(BASE_DIR, "run.log")

# 已处理记录文件（避免重复进群）
PROCESSED_FILE = os.path.join(BASE_DIR, "processed.json")

# 群数据库文件（记录进群状态、发消息时间等）
GROUP_DB_FILE = os.path.join(BASE_DIR, "group_db.json")

# ==================== 发消息轮换间隔（天） ====================
SEND_INTERVAL_MIN_DAYS = 1
SEND_INTERVAL_MAX_DAYS = 3

# ==================== 时间间隔配置（秒） ====================
# 进群后等待间隔（随机取范围内的值）
JOIN_DELAY_MIN = 30
JOIN_DELAY_MAX = 60

# 发消息间隔
SEND_DELAY_MIN = 5
SEND_DELAY_MAX = 15

# UI 操作步骤间的短暂等待
UI_STEP_DELAY = 1.5

# ==================== 风控配置 ====================
# 每个账号每天最大进群数
MAX_GROUPS_PER_ACCOUNT = 20

# 允许运行的时间段（24小时制）
WORK_HOUR_START = 8
WORK_HOUR_END = 22

# ==================== 微信账号配置 ====================
# 账号列表，name 用于显示提示，groups_limit 为该账号进群上限
ACCOUNTS = [
    {"name": "宇昊", "groups_limit": MAX_GROUPS_PER_ACCOUNT},
    {"name": "微信号2", "groups_limit": MAX_GROUPS_PER_ACCOUNT},
    {"name": "微信号3", "groups_limit": MAX_GROUPS_PER_ACCOUNT},
]

# ==================== AI 改写配置 ====================
# 使用 OpenAI 兼容接口进行消息个性化改写
# 支持 OpenAI / DeepSeek / 通义千问等兼容接口
AI_BASE_URL = "https://www.fucheers.top/v1"  # 改成你的 API 地址
AI_API_KEY = "sk-scjr0Ac9IbyLbAqerspoP5hNujNX7ZAq5fSXB1ikURkNZRHV"  # 填入你的 API Key
AI_MODEL = "gemini-3-flash"  # 模型名，如 deepseek-chat、qwen-turbo 等

AI_REWRITE_PROMPT = """你是一个微信群消息改写助手。你的任务是根据群的信息，将一段推广文案进行个性化改写，让它看起来像是专门为这个群写的，而不是群发广告。

要求：
1. 保留原文的核心卖点和联系方式，不能丢失关键信息
2. 根据群名和群简介，在开头加一句贴合该群主题的打招呼/引入语
3. 适当调整语气和用词，让内容与群的氛围匹配
4. 保持自然口语化，像是群成员真诚分享而非硬广
5. 总字数不要超过原文太多，控制在原文1.2倍以内
6. 不要加任何解释说明，直接输出改写后的消息文本"""

# ==================== 支持的图片格式 ====================
SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
