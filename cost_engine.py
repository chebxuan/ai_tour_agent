
# cost_engine.py
# 职责：基于产品编号列表 + 人数构成 + 用户偏好，计算总报价
# 输入：product Dict + user_intent Dict
# 输出：报价明细 Dict

import csv
import os
import math

# ── 常量配置 ─────────────────────────────────────────────────────

COST_CSV = "mashes/北京_merged.csv"

# 儿童折扣规则（按项目编号单独配置）
CHILD_DISCOUNT = {
    "BJ-TICKET-05": 0.0,   # 故宫：1.2m以下免费
    "BJ-TICKET-04": 0.5,   # 慕田峪：儿童半价
    "BJ-TICKET-01": 0.5,   # 天坛：儿童半价
    "BJ-TICKET-08": 0.5,   # 颐和园：儿童半价
    "DEFAULT":       1.0,   # 默认：全价
}

# 老人折扣规则
SENIOR_DISCOUNT = {
    "BJ-TICKET-05": 0.5,   # 故宫：老人半价
    "BJ-TICKET-04": 0.5,   # 慕田峪：老人半价
    "DEFAULT":       1.0,
}

# 车辆选择规则
def get_transport_code(total_people):
    if total_people <= 4:
        return "BJ-TRANS-01"   # 5座车 500/天
    else:
        return "BJ-TRANS-02"   # 7座车 650/天

# ── 核心函数 ─────────────────────────────────────────────────────

def load_cost_db(csv_path=None):
    """
    读取成本库CSV，返回以项目编号为Key的字典
    输出格式: {"BJ-TICKET-05": {"单价": 40, "单价（旺季）": 60, ...}}
    """
    if csv_path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base, COST_CSV)

    db = {}
    try:
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row['项目编号'].strip()
                db[code] = {
                    "name":       row['项目名称'].strip(),
                    "category":   row['服务类目'].strip(),
                    "price":      float(row['单价'] or 0),
                    "price_peak": float(row['单价（旺季）'] or 0),
                    "unit":       row['单位'].strip(),
                    "note":       row.get('项目备注', '').strip()
                }
    except FileNotFoundError:
        print(f"[错误] 找不到成本库文件: {csv_path}")
    return db


def get_item_price(code, is_peak):
    """获取单个项目的适用单价"""
    db = load_cost_db()
    if code not in db:
        return 0, "未知项目"
    item = db[code]
    price = item['price_peak'] if is_peak else item['price']
    return price, item['name']


def calc_ticket_activity_cost(item_codes, adults, children,
                               seniors, is_peak):
    """
    计算门票+活动的总成本
    返回：{
        "breakdown": [每项明细],
        "subtotal": 小计
    }
    """
    db = load_cost_db()
    breakdown = []
    subtotal = 0.0

    for code in item_codes:
        code = code.strip()
        if code not in db:
            continue
        item = db[code]
        unit_price = item['price_peak'] if is_peak else item['price']

        if unit_price == 0:
            breakdown.append({
                "code": code,
                "name": item['name'],
                "unit_price": 0,
                "adults": adults,
                "children": children,
                "seniors": seniors,
                "line_total": 0,
                "note": "免费"
            })
            continue

        # 成人费用
        adult_cost = unit_price * adults

        # 儿童费用
        child_rate = CHILD_DISCOUNT.get(code,
                     CHILD_DISCOUNT["DEFAULT"])
        child_cost = unit_price * child_rate * children

        # 老人费用
        senior_rate = SENIOR_DISCOUNT.get(code,
                      SENIOR_DISCOUNT["DEFAULT"])
        senior_cost = unit_price * senior_rate * seniors

        line_total = adult_cost + child_cost + senior_cost
        subtotal += line_total

        breakdown.append({
            "code":        code,
            "name":        item['name'],
            "unit_price":  unit_price,
            "adults":      adults,
            "children":    children,
            "seniors":     seniors,
            "line_total":  line_total,
            "note":        item['note']
        })

    return {"breakdown": breakdown, "subtotal": round(subtotal, 2)}


def calc_hotel_cost(hotel_code, hotel_price, total_people, days):
    """
    计算酒店成本
    房间数 = ceil(总人数 / 2)，住宿天数 = 行程天数 - 1
    """
    nights = max(days - 1, 1)
    rooms  = math.ceil(total_people / 2)
    total  = hotel_price * rooms * nights

    return {
        "hotel_code":  hotel_code,
        "hotel_price": hotel_price,
        "rooms":       rooms,
        "nights":      nights,
        "subtotal":    round(total, 2)
    }


def calc_transport_cost(total_people, days,
                        transfer_code, transfer_price):
    """
    计算交通成本：包车 + 接送
    """
    db = load_cost_db()
    trans_code  = get_transport_code(total_people)
    trans_item  = db.get(trans_code, {})
    daily_price = trans_item.get('price', 500)
    car_total   = daily_price * days

    # 接送：去程+返程 = 2次
    transfer_total = transfer_price * 2 if transfer_code else 0

    return {
        "car_code":        trans_code,
        "car_daily_price": daily_price,
        "days":            days,
        "car_subtotal":    round(car_total, 2),
        "transfer_code":   transfer_code,
        "transfer_price":  transfer_price,
        "transfer_times":  2 if transfer_code else 0,
        "transfer_subtotal": round(transfer_total, 2),
        "subtotal":        round(car_total + transfer_total, 2)
    }


def calc_guide_cost(guide_code, days):
    """计算导游成本"""
    db = load_cost_db()
    if not guide_code:
        return {
            "guide_code": None,
            "guide_name": None,
            "daily_price": 0,
            "days": days,
            "subtotal": 0
        }
    item  = db.get(guide_code, {})
    price = item.get('price', 800)
    total = price * days
    return {
        "guide_code":  guide_code,
        "guide_name":  item.get('name', '英文导游'),
        "daily_price": price,
        "days":        days,
        "subtotal":    round(total, 2)
    }


def calculate_total_cost(product, user_intent):
    """
    主函数：汇总所有成本
    输入:
        product     ← product_engine.py 的输出
        user_intent ← cli_app.py 汇总的意图
    输出:
        完整报价单 Dict
    """
    # ── 解析人数 ──────────────────────────────────────────────────
    adults   = int(user_intent.get('adults',   2))
    children = int(user_intent.get('children', 0))
    seniors  = int(user_intent.get('seniors',  0))
    total_people = adults + children + seniors

    # ── 解析其他参数 ──────────────────────────────────────────────
    days         = int(product.get('days', 1))
    is_peak      = bool(user_intent.get('is_peak', True))
    guide_code   = user_intent.get('guide')
    hotel_code   = user_intent.get('hotel', 'BJ-HOTEL-01')
    hotel_price  = float(user_intent.get('hotel_price', 550))
    transfer_code  = user_intent.get('transfer')
    transfer_price = float(user_intent.get('transfer_price', 0))

    # ── 解析常规项目编号 ──────────────────────────────────────────
    regular_codes_raw = str(
        product.get('常规项目项目编号列表',
        product.get('regular_item_codes', ''))
    )
    regular_codes = [
        c.strip()
        for c in regular_codes_raw.split(',')
        if c.strip()
    ]

    # ── 分项计算 ──────────────────────────────────────────────────
    ticket_result    = calc_ticket_activity_cost(
                           regular_codes, adults,
                           children, seniors, is_peak)
    hotel_result     = calc_hotel_cost(
                           hotel_code, hotel_price,
                           total_people, days)
    transport_result = calc_transport_cost(
                           total_people, days,
                           transfer_code, transfer_price)
    guide_result     = calc_guide_cost(guide_code, days)

    # ── 汇总 ──────────────────────────────────────────────────────
    grand_total = (
        ticket_result['subtotal']    +
        hotel_result['subtotal']     +
        transport_result['subtotal'] +
        guide_result['subtotal']
    )

    return {
        "summary": {
            "product_name":  product.get('product_name', ''),
            "days":          days,
            "adults":        adults,
            "children":      children,
            "seniors":       seniors,
            "total_people":  total_people,
            "is_peak":       is_peak,
            "grand_total":   round(grand_total, 2),
            "per_person":    round(grand_total / max(total_people, 1), 2)
        },
        "ticket_activity": ticket_result,
        "hotel":           hotel_result,
        "transport":       transport_result,
        "guide":           guide_result
    }