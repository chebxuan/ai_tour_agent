# survey_architect.py
# 职责：返回固定的问卷结构，不调用任何API
# 输入：无
# 输出：问卷列表 List[Dict]

# survey_architect.py 更新版

def get_beijing_survey():
    return [
        # ── 原有问题 ──────────────────────────────
        {
            "step": 1,
            "question": "您计划游览北京几天？",
            "options": [
                {"text": "2天", "weight": {"city": "北京", "days": 2, "style": "经典"}},
                {"text": "3天", "weight": {"city": "北京", "days": 3, "style": "深度"}},
                {"text": "4天", "weight": {"city": "北京", "days": 4, "style": "全景"}}
            ]
        },
        {
            "step": 2,
            "question": "请输入同行人数（直接输入数字，用逗号分隔）\n  格式：成人数,儿童数(12岁以下),老人数(65岁以上)\n  示例：2,1,0 表示2个成人+1个小孩",
            "input_type": "text",   # ← 标记为文字输入题
            "options": []           # ← 无选项，直接输入
        },
        # ── 新增问题 ──────────────────────────────
        {
            "step": 3,
            "question": "出行季节？（影响部分景点票价）",
            "options": [
                {"text": "旺季（4月-10月）",
                 "weight": {"is_peak": True}},
                {"text": "淡季（11月-3月）",
                 "weight": {"is_peak": False}}
            ]
        },
        {
            "step": 4,
            "question": "是否需要英文导游？",
            "options": [
                {"text": "需要全程英文导游",
                 "weight": {"guide": "BJ-GUIDE-01"}},
                {"text": "不需要导游（自由行）",
                 "weight": {"guide": None}}
            ]
        },
        {
            "step": 5,
            "question": "酒店档次偏好？",
            "options": [
                {"text": "经济型（全季-亚运村，¥550/间/晚）",
                 "weight": {"hotel": "BJ-HOTEL-01", "hotel_price": 550}},
                {"text": "舒适型（全季-前门四合院，¥800/间/晚）",
                 "weight": {"hotel": "BJ-HOTEL-02", "hotel_price": 800}},
                {"text": "精品型（青普文化行馆，¥1000/间/晚）",
                 "weight": {"hotel": "BJ-HOTEL-03", "hotel_price": 1000}}
            ]
        },
        {
            "step": 6,
            "question": "是否需要接送服务？",
            "options": [
                {"text": "需要接机（首都机场）",
                 "weight": {"transfer": "BJ-TRANS-04", "transfer_price": 200}},
                {"text": "需要接机（大兴机场）",
                 "weight": {"transfer": "BJ-TRANS-05", "transfer_price": 200}},
                {"text": "需要接站（北京南站）",
                 "weight": {"transfer": "BJ-TRANS-03", "transfer_price": 100}},
                {"text": "不需要接送",
                 "weight": {"transfer": None, "transfer_price": 0}}
            ]
        }
    ]