"""
生成脚本：调用通义千问为每个城市生成 POI 数据

工作流程：
  1. 读取 mashes/{城市}_merged.csv 获取该城市的服务项目列表（作为 item_code 映射依据）
  2. 调用 DashScope 通义千问，让 LLM 生成符合六类最小单元体系的 POI 数据
  3. 输出到 data/pois/{城市}_pois.json

POI 与 mashes 的关系：
  - POI 侧重于"方便自定义路线编排"：包含时段、时长、关联、交通判断等维度
  - mashes 侧重于"成本统计"：包含单价、淡旺季价格
  - 两个表通过 item_code / ticket_item_code 字段一一对应
  - POI 不包含导游/车辆类服务（属于 service 类，走报价链路，不走路线编排）

使用方式：
  python scripts/generate_city_pois.py --city 北京          # 生成单个城市
  python scripts/generate_city_pois.py --all                # 生成全部 10 个城市
  python scripts/generate_city_pois.py --city 北京 --dry-run  # 仅预览 prompt，不调用 API
"""

from __future__ import annotations

import csv
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── 路径 ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
MASHES_DIR = ROOT / "data" / "products" / "services" / "mashes"
POIS_DIR = ROOT / "data" / "pois"
ENV_FILE = ROOT / ".env"

# 城市列表（与 product_engine 保持一致）
ALL_CITIES = ["北京", "上海", "广州", "重庆", "西安", "阳朔", "张家界", "贵州", "云南", "成都"]

# 城市代码前缀（用于 unit_id：{code}-ANC-001）
CITY_CODE_MAP = {
    "北京": "BJ", "上海": "SH", "广州": "GZ", "重庆": "CQ",
    "西安": "XA", "阳朔": "YS", "张家界": "ZJJ", "贵州": "GUIZ",
    "云南": "YN", "成都": "CD",
}

# ── 城市差异化生成指引 ────────────────────────────────────────
# 告诉 LLM：经典层已覆盖什么、差异化方向是什么、叙事主题建议


CITY_GUIDANCE: Dict[str, str] = {
    "北京": """- 经典层已覆盖：故宫、长城（慕田峪）、天坛、颐和园、雍和宫、景山
- 差异化方向：798/751艺术区、胡同深度体验（避开南锣鼓巷主街）、驻京办餐厅、潘家园旧货市场、五道营胡同、法源寺/牛街片区、东交民巷老使馆区
- 主题建议：Morning_Beijing（天坛/地坛/日坛晨练文化）、New_Beijing_Art（798及草场地艺术区）、Old_Beijing_Living（胡同里的真实日常——不是商业街）、Central_Axis_Secrets（中轴线上的隐秘角落：什刹海野冰/野泳、钟鼓楼时间故事）、Canteen_Diplomacy（驻京办餐厅=不出北京吃遍中国）""",

    "上海": """- 经典层已覆盖：外滩、豫园、城隍庙、上海博物馆、迪士尼、朱家角
- 差异化方向：法租界弄堂深处（非武康路主街——走复兴西路/永福路/湖南路）、苏州河工业遗存（福新面粉厂/M50/四行仓库）、本地菜市场（乌中市集/嘉善老市）、1933老场坊、愚园路弄堂、隆昌公寓（"中国版九龙城寨"外观）、徐汇滨江跑步道
- 主题建议：Concession_Echoes（法租界弄堂里的文艺日常）、Suzhou_Creek_Rebirth（苏州河——从工业锈带到艺术走廊）、Shanghai_Lanes（弄堂清晨——晾衣杆、馄饨摊、老邻居聊天）、Morning_in_Shanghai（菜市场的烟火气 vs 咖啡馆的精致）、Lilong_Stories（里弄人家的建筑密码——石库门门楣上的雕花在说什么）""",

    "广州": """- 经典层已覆盖：陈家祠、沙面、广州塔、永庆坊、越秀公园、南越王博物院
- 差异化方向：西关大屋群（宝源路/多宝路/龙津西路骑楼）、恩宁路打铜街、一德路海味干货街、东山口洋楼群（中共三大会址周边的民国别墅群）、芳村/岭南花卉市场、荔湾湖公园早茶+私伙局粤曲、海珠区小洲村（"广州最后的岭南水乡"）
- 主题建议：Canton_Neighborhood（老城街区漫步——骑楼下的广州）、Xiguan_Morning（西关清晨：趟栊门、满洲窗、一盅两件）、Pearl_River_Life（珠江边的日常——人民桥到海珠桥）、Lingnan_Artisan（打铜、广绣、牙雕——还活着的手艺）、Dongshan_Republic_Era（东山洋楼里的民国往事）""",

    "重庆": """- 经典层已覆盖：人民大礼堂、山城巷、长江索道、武隆、大足石刻、磁器口
- 差异化方向：交通茶馆（黄桷坪——重庆最后一个老茶馆）、山城步道（第三步道/张家花园步道/南滨路步道——非游客段）、下浩里老街背街小巷、鹅岭二厂+鹅岭公园瞰江台、黄桷坪涂鸦街+川美老校区、南山上废弃的抗战遗址群（重庆作为陪都的记忆）
- 主题建议：Mountain_City_Steps（山城步道的日常——爬坡上坎才是真正的重庆）、Chongqing_Teahouse（茶馆江湖——交通茶馆里的棋局与人生）、Riverside_Life（两江交汇处的码头基因）、Wartime_Chongqing（陪都记忆——南山上的防空洞与大使馆旧址）、Night_CQ（不是洪崖洞——是南滨路看对岸的万家灯火）""",

    "西安": """- 经典层已覆盖：兵马俑、大雁塔、明城墙、钟鼓楼、回民街主街、大唐不夜城
- 差异化方向：西仓集市（周四/周日——西安最原生态的鸟市+古玩市集）、碑林周边老街区（书院门/三学街——不是景点是文人生活）、小雁塔（比大雁塔安静太多+西安博物院）、半坡国际艺术区（纺织城旧厂房改造）、洒金桥（本地人吃的美食街——非回民街主街）、城墙根下的秦腔自乐班（环城公园傍晚）
- 主题建议：Old_Xian_Market（西仓集市——只有周四/周日才有的老西安）、Tang_Traces（寻找唐代长安——小雁塔/天坛遗址/大明宫遗址公园）、Muslim_Quarter_Deep（回坊深处：洒金桥→庙后街→大皮院——本地人的美食地图）、Xian_Calligraphy（书院门的笔墨纸砚——还在写字的老先生们）、City_Wall_Life（城墙根下的日常：秦腔、广场舞、下棋、剃头摊）""",

    "阳朔": """- 经典层已覆盖：遇龙河漂流、十里画廊骑行、西街、漓江电动竹筏、相公山
- 差异化方向：旧县村古民居（唐代旧县治——完整保存的明清建筑群+秘密花园客栈）、石头城遗址（阳朔西北的无人石城——喀斯特山顶的古城）、福利古镇（画扇之乡——可以看到手艺人现场画扇面）、兴坪渔村的傍晚（20元人民币背景，但游客散尽后才是真正的漓江）、漓江边野餐点（非码头的安静河滩）、七仙峰茶园（阳朔山间的茶山）
- 主题建议：Karst_Village（喀斯特峰林间的古村落——旧县/朗梓/龙潭）、Li_River_Hidden（漓江隐秘角落——游客退去之后的兴坪/杨堤）、Yangshuo_Farm（田园阳朔——稻田、茶山、柚子林间的骑行）、Old_County_Stories（旧县不是旅游景点——是活着的唐代县城）、Artisan_Yangshuo（画扇/竹编/手工红糖——还在做手艺的人）""",

    "张家界": """- 经典层已覆盖：天门山、张家界国家森林公园、芙蓉镇、凤凰古城
- 差异化方向：石堰坪古村落（中国保存最好的土家族吊脚楼群——全国重点文保）、槟榔谷（未开发的地下河+峡谷+天坑）、七星山非游客路线、本地赶集（张家界周边乡镇的土家族集市——腊肉/酸鱼/糍粑）、苦竹寨（澧水边的千年古寨）、八大公山（真正的原始森林——需要向导）
- 主题建议：Tujia_Village（土家吊脚楼——石堰坪的日出与炊烟）、Zhangjiajie_Wild（野趣张家界——游客不去的峡谷与溶洞）、Mountain_Market（山里赶集——背篓里的腊肉与山货）、Lishui_River（澧水河畔的千年古渡与寨子）、Avatar_Beyond（不只是阿凡达取景地——砂岩峰林的地质故事）""",

    "贵州": """- 经典层已覆盖：甲秀楼、青岩古镇、施洞苗银村、下司古镇、肇兴侗寨、荔波小七孔
- 差异化方向：丹寨蜡染体验（真正的蜡染村——排莫村/基加村）、控拜苗寨（中国最后的银匠村——银饰锻造全过程）、堂安梯田徒步（肇兴→堂安，中国最美徒步路线之一）、凯里周末非遗市集（每周五/六的苗族刺绣+银饰赶集）、西江苗寨的背面（避开观景台和主街——走东引村/也东寨的田埂）、榕江大利侗寨（未被开发的侗寨——比肇兴安静10倍）
- 主题建议：Miao_Life（苗寨不是景区——是苗族人真实的家）、Dong_Song（侗族大歌——无指挥无伴奏的多声部合唱，世界非遗）、Guizhou_Crafts（蜡染/银饰/刺绣——手工艺的完整链条从原材料开始）、Terrace_Walk（梯田不只是风景——是千年农耕文明的活化石）、Village_Market（赶集——苗族阿姨的绣片/银饰/草药摊）""",

    "云南": """- 经典层已覆盖：昆明石林、大理古城、洱海、丽江古城、香格里拉、虎跳峡、普达措
- 差异化方向：沙溪古镇（茶马古道上唯一幸存的古集市——四方街的清晨）、喜洲白族扎染（周城——扎染从板蓝根种植到成品的全流程）、巍山古城（南诏故都——未被商业化的真实古城）、白沙古镇的纳西日常（避开大研古城——看纳西老奶奶在四方街晒太阳）、诺邓古村（千年白族村——火腿和盐井的故事）、碧色寨（滇越铁路上的法式车站——《芳华》取景地之外的百年沧桑）
- 主题建议：Tea_Horse_Road（茶马古道遗存——沙溪/鲁史/云南驿的拴马石还在）、Bai_Tie_Dye（板蓝根如何变成扎染——从种蓝到成布的全部手艺）、Naxi_Morning（白沙的清晨——纳西老人在四方街晒太阳，游客还没到）、Yunnan_Market（云南的菜市场是植物学课堂——菌子季/各种不认识的花和草）、Old_Railway（滇越铁路/个碧石铁路——米轨上的百年云南）""",

    "成都": """- 经典层已覆盖：武侯祠、大熊猫基地、宽窄巷子、太古里、人民公园鹤鸣茶社
- 差异化方向：彭镇老茶馆（双流彭镇——成都最后一个百年老茶馆，每天凌晨4点开门）、抚琴社区夜市（不是游客的锦里——是成都人的深夜食堂）、曹家巷工人村（正在消失的老成都记忆——红砖楼/邻里食堂/街头理发摊）、望江楼公园（川大旁的竹林——唐代女诗人薛涛的纪念地，本地人喝茶打麻将的日常）、送仙桥古玩市场（周末地摊——比宽窄巷子有趣100倍的成都）、崇德里/镋钯街（老街区的新生——不是太古里的精致商业，是社区有机更新）
- 主题建议：Teahouse_Chengdu（茶馆是成都人的第二客厅——彭镇/望江楼/大慈寺里的龙门阵）、Night_Market_CD（抚琴夜市/建设路——成都人的深夜食堂不是火锅是路边摊）、Old_Chengdu_Vanishing（正在消失的老成都——曹家巷/水井坊/耿家巷）、Bamboo_and_Poetry（竹与诗——望江楼公园的150种竹子与薛涛笺的故事）、Community_Rebirth（镋钯街/崇德里的社区实验——老街区如何长出新的日常）""",
}


def generate_city_specific_guidance(city: str) -> str:
    """生成城市特异性指引文本"""
    guidance = CITY_GUIDANCE.get(city)
    if guidance:
        return f"### {city} 的差异化方向\n\n{guidance}"
    # 兜底：针对未知城市的通用指引
    return f"""### {city} 的差异化方向

- 请基于你对该城市的了解，挖掘经典景点之外的差异化内容
- 重点关注：本地人的日常去处、免费但有意思的地方、小众文化体验、社区菜市场/老街/工业遗存/大学周边
- 避开该城市最著名的 3-5 个必去景点（经典层已覆盖）
- 每一类 POI 尽量对应一个稳定的 narrative theme"""


# ── 加载环境变量 ───────────────────────────────────────────────
def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


# ── 读取 mash CSV ──────────────────────────────────────────────
def load_mash_items(city: str) -> List[Dict[str, str]]:
    """读取指定城市的 mash CSV，返回结构化 item 列表"""
    path = MASHES_DIR / f"{city}_merged.csv"
    if not path.exists():
        print(f"[错误] 找不到成本库文件: {path}")
        sys.exit(1)

    items = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("项目编号") or "").strip()
            name = (row.get("项目名称") or "").strip()
            category = (row.get("服务类目") or "").strip()
            price = (row.get("单价") or "").strip()
            price_peak = (row.get("单价（旺季）") or "").strip()
            unit = (row.get("单位") or "").strip()
            note = (row.get("项目备注") or "").strip()
            if code:
                items.append({
                    "code": code,
                    "name": name,
                    "category": category,
                    "unit": unit,
                    "price": price or "0",
                    "price_peak": price_peak or price or "0",
                    "note": note,
                })
    return items


# ── 构建 LLM Prompt ────────────────────────────────────────────
def build_prompt(city: str, mash_items: List[Dict[str, str]]) -> str:
    """为指定城市构建差异化 POI 生成提示词（v2）

    关键设计原则：
    1. 先定义"不是什么"，再定义"是什么"——明确排除经典层的重复内容
    2. 内嵌 Few-Shot 示例——每类 1 个高质量示例（北京），定调"差异化"的标准
    3. mash 降级为二级参考——只用于 item_code 映射，不作为灵感来源
    4. 城市特异性指令——基于 CITY_GUIDANCE 中的人工标注方向
    5. 叙事主题驱动——每个 POI 有 theme，同类可串联成故事线
    """

    city_code = CITY_CODE_MAP.get(city, city[:2].upper())

    # ── mash 摘要：只列出门票/活动，用于 item_code 映射参考（不作为灵感来源）──
    by_cat: Dict[str, List[Dict]] = {}
    for item in mash_items:
        if item.get("category") in {"导游", "车辆", "打车", "补贴服务费"}:
            continue
        by_cat.setdefault(item["category"], []).append(item)

    mash_summary_parts = []
    for cat_name in ["门票", "活动"]:
        if cat_name in by_cat:
            items = by_cat[cat_name]
            lines = "\n".join(f"  {it['code']} | {it['name']} | ¥{it['price']}" for it in items)
            mash_summary_parts.append(f"{cat_name}（仅用于 item_code 映射，不作为灵感来源）:\n{lines}")

    mash_summary = "\n\n".join(mash_summary_parts) if mash_summary_parts else "（该城市暂无成本库数据。item_code/ticket_item_code 留空即可。）"

    # ── 城市特异性指引 ──
    city_guidance = generate_city_specific_guidance(city)

    return f"""你是一位深谙中国在地文化的旅行体验设计师。请为 **{city}** 构建一个"差异化 POI 库"，用于 AI 动态行程编排引擎。

## 🎯 核心定位：与"经典产品层"的关系

我们已有 **经典产品层**（21 个固定线路），覆盖该城市最著名的必去景点。经典层能很好地服务"第一次来中国"的游客。

**你现在构建的差异化 POI 库，服务于另一个场景：**
- 回头客（"去过故宫了，这次想看不一样的"）
- 深度文化爱好者（"我想理解中国，不只是拍照打卡"）
- 追求独特体验的年轻旅客（"不要旅行团路线，要本地人的日常"）

**核心原则：经典层已覆盖的景点，不要作为 anchor 重复生成。你要挖掘的是：本地人珍视的、外国人不知道的、有故事可讲的地方。**

---

## 六类最小单元（附 Few-Shot 差异化示例）

以下示例来自北京，展示你应该达到的"差异化"质量标准。请为 {city} 生成同等质量的 POI。

### 1. anchor — 主题锚点（4-6 个）

不是"著名景点"，而是"叙事主题的物理载体"。一个好 anchor = 外国人走进去会说"我不知道中国还有这样的地方"。

**Few-Shot：**
```json
{{
  "unit_id": "BJ-ANC-006",
  "city": "北京",
  "category": "anchor",
  "name": "798艺术区",
  "name_en": "798 Art District",
  "duration_min": 180,
  "duration_min_min": 120,
  "duration_max_min": 300,
  "preferred_slot": "afternoon",
  "opening_start": "10:00",
  "opening_end": "18:00",
  "closed_days": ["Monday"],
  "lat": 39.9842,
  "lng": 116.4951,
  "area": "朝阳区-酒仙桥",
  "indoor_outdoor": "mixed",
  "is_rainy_friendly": true,
  "is_hot_weather_friendly": true,
  "is_family_friendly": true,
  "is_senior_friendly": true,
  "min_age": 0,
  "unit_price_adult": 0,
  "is_free": true,
  "tags": ["当代艺术", "工业遗存", "苏联建筑", "画廊", "摄影"],
  "theme": "New_Beijing_Art",
  "related_units": [],
  "incompatible_units": [],
  "energy_level": 2,
  "crowd_level": 3,
  "uniqueness_score": 5,
  "is_must_see": false,
  "requires_reservation": false,
  "advance_days": 0,
  "ticket_item_code": ""
}}
```
**为什么这是好 anchor：** 它不是传统"景点"，但它是理解当代中国的最佳窗口——包豪斯工厂改建的画廊群、苏联/东德援建的历史、中国当代艺术的中心。对外国游客来说比第 3 个寺庙更有记忆点。

**生成要求：**
- ❌ 跳过：该城市旅游 Top 3 的必去景点（经典层已覆盖）。不要生成故宫/长城/天坛/颐和园/兵马俑/外滩/豫园 等
- ✅ 寻找：艺术区、历史街区、本地市场、大学周边、工业遗址改造、河流/湖畔生活区、非主流古镇
- ✅ 每个 anchor 必须有明确的 narrative theme（如 "New_Beijing_Art"、"Old_City_Rebirth"、"Morning_Culture"）
- ⚠️ 如果某个经典景点有你认为必须保留的——可以作为 anchor 生成，但 `is_must_see` 必须为 false，并在 `uniqueness_score` 中体现其大众程度

### 2. experience — 文化体验（3-5 个）

利润中心。关键是可预订、有明确价格、外国人能参与。不是"看"，是"做"。

**Few-Shot：**
```json
{{
  "unit_id": "BJ-EXP-004",
  "city": "北京",
  "category": "experience",
  "name": "跟胡同大爷学抖空竹",
  "name_en": "Diabolo Lesson with a Hutong Local",
  "duration_min": 60,
  "preferred_slot": "morning",
  "lat": 39.9365,
  "lng": 116.3872,
  "area": "东城区-什刹海",
  "indoor_outdoor": "outdoor",
  "is_rainy_friendly": false,
  "is_family_friendly": true,
  "is_senior_friendly": true,
  "unit_price_adult": 150,
  "is_free": false,
  "tags": ["非遗技艺", "本地互动", "肢体体验", "老少皆宜"],
  "theme": "Old_Beijing_Living",
  "energy_level": 2,
  "crowd_level": 1,
  "uniqueness_score": 5,
  "requires_min_people": 2,
  "max_people_per_session": 8,
  "requires_guide": true,
  "language_support": ["EN", "ZH"],
  "item_code": ""
}}
```
**为什么这是好 experience：** 不是"看京剧"（经典层已有），而是"跟真实的人学一个动作"。外国人拍了视频会发 Instagram——免费营销。成本 ¥150/人，可定价 ¥300-400。需要导游翻译（`requires_guide: true`）。

**生成要求：**
- ❌ 跳过：汉服拍照、京剧观赏、标准 cooking class（除非有独特的在地 twist——比如"在敦煌壁画前学唐代妆容"才值得保留）
- ✅ 寻找：本地人日常技能（抖空竹、写毛笔字、打太极、包饺子）、手工艺人工作室拜访（蜡染/银饰/陶艺/年画/剪纸）、社区菜市场导览（跟本地阿姨学挑菜+隔壁摊现做）、晨练参与（跟公园大爷学一招半式）、本地乐器/戏曲体验（不只是听——上手试）
- ✅ 需要导游翻译陪同的标注 `requires_guide: true`
- ✅ 给出可信的人均价格（RMB），考虑材料费和人工费

### 3. freebie — 免费节点（4-6 个）★ 最重要的类别

**这是你最重要的类别。** 零成本 + 高记忆点 = 产品独特性的核心来源。用免费在地体验替换景区门票，提高利润率。

**Few-Shot：**
```json
{{
  "unit_id": "BJ-FRE-005",
  "city": "北京",
  "category": "freebie",
  "name": "地坛公园书市与晨练",
  "name_en": "Ditan Park — Morning Rituals & Book Market",
  "duration_min": 45,
  "preferred_slot": "morning",
  "opening_start": "06:00",
  "opening_end": "09:00",
  "lat": 39.9523,
  "lng": 116.4175,
  "area": "东城区-地坛",
  "indoor_outdoor": "outdoor",
  "is_rainy_friendly": false,
  "is_family_friendly": true,
  "is_senior_friendly": true,
  "unit_price_adult": 0,
  "is_free": true,
  "tags": ["晨练", "太极拳", "书法地书", "二手书市", "本地社交"],
  "theme": "Morning_Beijing",
  "energy_level": 1,
  "crowd_level": 2,
  "uniqueness_score": 5,
  "best_time_note": "周六日上午有旧书市集（北京仅存的露天书市）。平日早上 6:30-7:30 退休老人们打太极、写地书、甩鞭子——这是游客永远看不到的北京",
  "photo_score": 5
}}
```
**为什么这是好 freebie：** 有明确时间窗口（早上 6-8 点）、独特场景（写地书的退休大爷——外国游客从未见过的画面）、完全免费、极高的好奇心价值。"北京人的早晨"本身就是一个可以卖的故事。

**生成要求：**
- ✅ `best_time_note` 要写清楚：在什么时间、能看到什么、为什么这个时间好。要有画面感。
- ✅ `photo_score` 1-5 出片指数（Instagrammability），帮助引擎为喜欢拍照的客人选择
- ✅ 寻找：公园晨练点（太极/地书/广场舞/毽子/陀螺）、菜市场/花鸟鱼虫市场、老社区弄堂清晨、校园开放区域、河边步道傍晚、城市观景台/天桥、古建筑外观/街头老手艺人摊位
- ✅ `is_free` 必须为 true

### 4. meal — 餐饮体验（2-3 个）

不只是"在哪吃"——"吃饭的过程本身就是文化体验"。重点选本地人日常消费的场景，而不是游客餐厅。

**Few-Shot：**
```json
{{
  "unit_id": "BJ-MEA-003",
  "city": "北京",
  "category": "meal",
  "name": "牛街清真小吃巡礼",
  "name_en": "Niujie Muslim Street Food Walk",
  "duration_min": 90,
  "preferred_slot": "lunch",
  "lat": 39.8845,
  "lng": 116.363,
  "area": "西城区-牛街",
  "indoor_outdoor": "mixed",
  "is_rainy_friendly": true,
  "is_family_friendly": true,
  "is_senior_friendly": true,
  "unit_price_adult": 0,
  "is_free": false,
  "tags": ["清真美食", "烟火气", "本地人排队", "胡同深处"],
  "theme": "Old_Beijing_Living",
  "energy_level": 1,
  "crowd_level": 3,
  "uniqueness_score": 4,
  "cuisine_type": "清真/北京小吃",
  "meal_period": "lunch",
  "price_per_person_range": "50-100",
  "is_social": true,
  "item_code": ""
}}
```
**为什么这是好 meal：** 不是所有外国人都知道的"烤鸭"，而是真正的本地人日常。牛街是北京最有烟火气的美食街——排队买甑糕、牛肉包子、驴打滚……整个过程就是一部微型纪录片。不是南锣鼓巷那种游客街。

**生成要求：**
- ❌ 跳过：该城市最著名的 1-2 道菜（如北京烤鸭、上海小笼包——经典层菜单已覆盖）
- ✅ 寻找：本地人排队的小吃街/夜市、特定社区饮食文化（清真街/少数民族菜/驻京办餐厅）、菜市场里的熟食摊、深夜大排档、老字号（非游客店）
- ✅ `is_social` 标注是否适合社交（涮肉=是，快餐=否）
- ✅ `price_per_person_range` 给出合理的人均区间

### 5. rest — 休憩/氛围节点（1-2 个）

节奏缓冲，但本身就应该是一个小的文化体验。不能是"星巴克"——必须是只有这个城市才有的空间。

**Few-Shot：**
```json
{{
  "unit_id": "BJ-RES-002",
  "city": "北京",
  "category": "rest",
  "name": "春风书院",
  "name_en": "Spring Breeze Academy — Courtyard Cafe",
  "duration_min": 30,
  "preferred_slot": "flexible",
  "lat": 39.9332,
  "lng": 116.4035,
  "area": "东城区-南锣鼓巷",
  "indoor_outdoor": "mixed",
  "is_rainy_friendly": true,
  "is_family_friendly": true,
  "is_senior_friendly": true,
  "unit_price_adult": 0,
  "is_free": false,
  "tags": ["四合院", "咖啡", "书店", "静坐"],
  "theme": "Old_Beijing_Courtyard",
  "energy_level": 1,
  "crowd_level": 2,
  "uniqueness_score": 3,
  "has_wifi": true,
  "has_restroom": true,
  "item_code": ""
}}
```
**为什么这是好 rest：** 不是 "Starbucks"。它是四合院改建的书院咖啡馆——"我在一个中国老院子里喝咖啡"这个场景本身就是 Instagrammable 的，同时也让客人从高体力 anchor 中恢复。

**生成要求：**
- ❌ 跳过：星巴克、麦当劳、任何全国连锁品牌
- ✅ 寻找：独立咖啡馆（最好在特色建筑里/有在地文化元素）、老建筑改造的书店/茶馆、可以坐着看街景的百年老店

---

## 📋 {city} 差异化生成指引

{city_guidance}

---

## 🔗 成本库关联（仅用于报价映射）

以下是 {city} 成本库中已有的项目。仅用于 item_code/ticket_item_code 关联——**不要基于此列表生成 POI**。如果某个 POI 在成本库中没有对应项目，item_code/ticket_item_code 留空即可。

{mash_summary}

---

## 📐 输出格式

输出一个 **严格 JSON 数组** `[...]`。不要 markdown 代码块标记，不要任何说明文字。直接输出纯 JSON。

**城市代码前缀：** `{city_code}` ← 所有 unit_id 必须以此为前缀（如 `{city_code}-ANC-001`）

**数量要求：** 15-25 个 POI
- anchor: 4-6（主题锚点，优先非经典景点）
- experience: 3-5（可预订的文化体验）
- freebie: 4-6（免费在地节点——最重要的类别，不要偷工减料）
- meal: 2-3（本地人饮食场景）
- rest: 1-2（独立/在地空间）

**质量要求：**
- 所有经纬度使用真实坐标
- `theme` 字段必须填写：同一城市的 POI 至少有 2-3 个不同的 theme（否则编排会很单调）
- `uniqueness_score`: 1=每个游客都知道，3=旅游攻略里能查到，5=只有本地人知道。anchor 平均 ≥4，freebie 平均 ≥4
- `best_time_note`（freebie 专属）：要写清楚什么时间能看到什么，有画面感
- `is_free: true` 的 POI 至少占 30%
- 不生成 service 类（导游/车辆/酒店走独立报价链路）
- 不生成仅有名无实的 POI（如"XX广场"只有一个空名没有具体可做的事）"""


# ── 调用 DashScope API ─────────────────────────────────────────
def call_llm(prompt: str, api_key: str) -> str:
    """调用通义千问（DashScope）"""
    import httpx

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "qwen-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 8192,
    }

    print(f"  调用 LLM...（prompt={len(prompt)}字符）", end=" ", flush=True)
    with httpx.Client(timeout=300) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"\n  API 错误: {resp.status_code}")
            print(f"  响应: {resp.text[:500]}")
            resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {})
    print(f"完成（input_tokens={tokens.get('prompt_tokens', '?')}, output_tokens={tokens.get('completion_tokens', '?')}）")
    return content


# ── 解析 LLM 输出 ──────────────────────────────────────────────
def parse_llm_response(content: str, city: str) -> List[Dict[str, Any]]:
    """从 LLM 输出中提取 POI JSON 数组"""
    import re

    content = content.strip()

    # 去掉可能的 markdown 代码块标记
    if content.startswith("```"):
        lines = content.splitlines()
        cleaned = []
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                cleaned.append(line)
        content = "\n".join(cleaned).strip()

    # 策略 1: 尝试直接解析为 JSON 数组或对象
    for parser in [
        lambda c: json.loads(c),                                    # 完整 JSON（数组或对象）
        lambda c: json.loads(c[c.find("["):c.rfind("]")+1]),       # 提取数组区域
        lambda c: json.loads(c[c.find("{"):c.rfind("}")+1]),       # 提取对象区域
    ]:
        try:
            data = parser(content)
            if isinstance(data, dict):
                if "pois" in data:
                    return data["pois"]
                if "data" in data:
                    return data["data"]
                return [data]
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, ValueError, IndexError):
            continue

    # 策略 2: 多个独立 JSON 对象拼接（无逗号分隔）
    objects = []
    idx = 0
    while idx < len(content):
        start = content.find("{", idx)
        if start == -1:
            break
        # 找到匹配的 }
        brace_depth = 0
        for end in range(start, len(content)):
            if content[end] == "{":
                brace_depth += 1
            elif content[end] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    try:
                        obj = json.loads(content[start:end+1])
                        objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    idx = end + 1
                    break
        else:
            break

    if objects:
        return objects

    raise ValueError("无法从 LLM 输出中提取任何 JSON 对象")


# ── 质量校验 ────────────────────────────────────────────────────


def validate_pois(pois: List[Dict[str, Any]], city: str, city_code: str) -> List[str]:
    """对生成的 POI 做质量检查，返回问题列表"""

    issues: List[str] = []

    # 基础检查
    if len(pois) < 10:
        issues.append(f"POI 数量={len(pois)}，少于推荐的 15-25 个")

    # 分类统计
    cats: Dict[str, int] = {}
    themes: Dict[str, int] = {}
    free_count = 0
    for p in pois:
        cat = p.get("category", "")
        cats[cat] = cats.get(cat, 0) + 1
        theme = p.get("theme", "")
        if theme:
            themes[theme] = themes.get(theme, 0) + 1

        if p.get("is_free"):
            free_count += 1

        # unit_id 前缀检查
        uid = p.get("unit_id", "")
        if not uid.startswith(city_code + "-"):
            issues.append(f"unit_id 前缀错误: {uid}（期望以 {city_code}- 开头）")

    # 类别分布
    if cats.get("freebie", 0) < 3:
        issues.append(f"freebie 数量={cats.get('freebie', 0)}，建议 ≥4（这是最重要的类别）")
    if cats.get("anchor", 0) < 3:
        issues.append(f"anchor 数量={cats.get('anchor', 0)}，建议 ≥4")
    if cats.get("experience", 0) < 2:
        issues.append(f"experience 数量={cats.get('experience', 0)}，建议 ≥3")

    # is_free 比例
    if len(pois) > 0:
        free_ratio = free_count / len(pois)
        if free_ratio < 0.25:
            issues.append(f"is_free 比例={free_ratio:.0%}，建议 ≥30%")

    # theme 多样性
    if len(themes) < 2:
        issues.append(f"theme 种类={len(themes)}，建议 ≥2 个不同叙事主题（否则编排会很单调）")

    # uniqueness_score 检查
    low_uniq = [p for p in pois if p.get("uniqueness_score", 0) <= 2]
    if low_uniq:
        names = [p.get("name", "?") for p in low_uniq]
        issues.append(f"以下 POI uniqueness_score≤2（偏大众）: {names}")

    return issues


# ── 主流程 ──────────────────────────────────────────────────────
def generate_city_pois(city: str, dry_run: bool = False) -> None:
    """为一个城市生成 POI 数据"""
    print(f"\n{'='*60}")
    print(f"生成 {city} POI 数据")
    print(f"{'='*60}")

    # 1. 读取 mash
    mash_items = load_mash_items(city)
    print(f"  成本库项目数: {len(mash_items)}")

    # 2. 构建 prompt
    prompt = build_prompt(city, mash_items)

    if dry_run:
        prompt_path = POIS_DIR / f"{city}_prompt.txt"
        POIS_DIR.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        print(f"  [dry-run] Prompt 已写入 {prompt_path}")
        print(f"  [dry-run] Prompt 长度: {len(prompt)} 字符")
        return

    # 3. 调用 LLM
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("[错误] 未设置 OPENAI_API_KEY 环境变量")
        sys.exit(1)

    try:
        content = call_llm(prompt, api_key)
    except Exception as e:
        print(f"[错误] API 调用失败: {e}")
        # 保存 prompt 以便重试
        error_path = POIS_DIR / f"{city}_error_prompt.txt"
        POIS_DIR.mkdir(parents=True, exist_ok=True)
        error_path.write_text(prompt, encoding="utf-8")
        print(f"  Prompt 已保存到 {error_path}")
        return

    # 4. 解析
    try:
        pois = parse_llm_response(content, city)
    except Exception as e:
        print(f"[错误] 解析 LLM 输出失败: {e}")
        error_path = POIS_DIR / f"{city}_error_response.txt"
        POIS_DIR.mkdir(parents=True, exist_ok=True)
        error_path.write_text(content, encoding="utf-8")
        print(f"  原始输出已保存到 {error_path}")
        return

    print(f"  生成 POI 数: {len(pois)}")

    # 5. 分类统计
    cats = {}
    for p in pois:
        cat = p.get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1
    print(f"  分类分布: {cats}")

    # 6. 质量校验
    city_code = CITY_CODE_MAP.get(city, city[:2].upper())
    issues = validate_pois(pois, city, city_code)

    # 7. 输出 JSON
    POIS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "city": city,
        "version": "1.0.0",
        "count": len(pois),
        "pois": pois,
    }
    output_path = POIS_DIR / f"{city}_pois.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  已写入: {output_path}")

    # 8. 质量报告
    print(f"\n  质量检查 ({len(issues)} 个问题):")
    if issues:
        for issue in issues:
            print(f"    ⚠️  {issue}")
    else:
        print(f"    ✅ 全部通过")
    print(f"  ✅ {city} 完成")


# ── CLI ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="生成城市 POI 数据（调用通义千问）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python scripts/generate_city_pois.py --all
  python scripts/generate_city_pois.py --city 北京
  python scripts/generate_city_pois.py --city 上海 --dry-run
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--city", type=str, help=f"城市名称，如 北京。可选: {', '.join(ALL_CITIES)}")
    group.add_argument("--all", action="store_true", help="生成全部 10 个城市")
    parser.add_argument("--dry-run", action="store_true", help="仅生成 prompt，不调用 API")

    args = parser.parse_args()

    # 加载环境变量
    load_env()

    if args.all:
        cities = ALL_CITIES
    else:
        if args.city not in ALL_CITIES:
            print(f"[错误] 不支持的城市: {args.city}。可选: {', '.join(ALL_CITIES)}")
            sys.exit(1)
        cities = [args.city]

    for city in cities:
        generate_city_pois(city, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    if args.dry_run:
        print("dry-run 完成。Prompt 已保存，检查无误后可去掉 --dry-run 执行。")
    else:
        print("全部生成完成！运行以下命令验证：")
        print("  python3 -c \"from engines.poi_registry import load_city_pois, list_available_poi_cities; print('可用城市:', list_available_poi_cities()); [print(f'  {c}: {len(load_city_pois(c))} POIs') for c in list_available_poi_cities()]\"")


if __name__ == "__main__":
    main()
