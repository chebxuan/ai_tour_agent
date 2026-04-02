"""
Hexa Blueprint™ API - 北京行程规划服务
FastAPI 版本，用于扣子(Coze)智能体集成

运行方式:
    uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload

环境变量:
    API_KEY: API 认证密钥 (必需)
    
作者: Hexa China Tours
版本: 1.0.0
"""

import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载现有模块
from survey_architect import get_beijing_survey
from product_engine import get_product_recommendation
from cost_engine import calculate_total_cost

# 加载环境变量
load_dotenv()

# ── FastAPI 应用初始化 ───────────────────────────────────────────

app = FastAPI(
    title="Hexa Blueprint™ API",
    description="北京旅游行程规划与报价服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置（允许扣子跨域调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为扣子域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Key 认证 ─────────────────────────────────────────────────

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("请设置环境变量 API_KEY，用于 API 认证")

async def verify_api_key(x_api_key: str = Header(..., description="API 认证密钥")):
    """验证 API Key"""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key"
        )
    return x_api_key

# ── Pydantic 数据模型 ────────────────────────────────────────────

class SurveyStepOption(BaseModel):
    """问卷选项"""
    text: str = Field(..., description="选项文本")
    weight: Dict[str, Any] = Field(..., description="权重映射")

class SurveyStep(BaseModel):
    """问卷步骤"""
    question: str = Field(..., description="问题文本")
    options: Optional[List[SurveyStepOption]] = Field(None, description="选项列表")
    input_type: str = Field("choice", description="输入类型: choice/text")

class SurveyResponse(BaseModel):
    """问卷响应"""
    survey: List[SurveyStep]
    total_steps: int
    version: str = "1.0.0"

class UserIntentRequest(BaseModel):
    """用户意图请求"""
    city: str = Field("北京", description="目标城市")
    days: int = Field(..., ge=1, le=7, description="行程天数")
    style: str = Field("经典", description="行程风格")
    persona: str = Field("standard", description="用户画像: family/couple/solo/senior")
    has_child: bool = Field(False, description="是否带儿童")
    interest: Optional[str] = Field(None, description="兴趣标签")
    adults: int = Field(2, ge=1, description="成人数量")
    children: int = Field(0, ge=0, description="儿童数量")
    seniors: int = Field(0, ge=0, description="老人数量")
    is_peak: bool = Field(True, description="是否旺季")
    guide: Optional[str] = Field(None, description="导游代码")
    hotel: str = Field("BJ-HOTEL-01", description="酒店代码")
    hotel_price: float = Field(550.0, description="酒店单价")
    transfer: Optional[str] = Field(None, description="接送代码")
    transfer_price: float = Field(0.0, description="接送单价")
    recommend_optional: Optional[str] = Field(None, description="推荐可选项")

class ProductInfo(BaseModel):
    """产品信息"""
    product_name: str
    days: int
    itinerary: str
    regular_items: str
    optional_items: str
    recommended_optional: str

class ProductResponse(BaseModel):
    """产品推荐响应"""
    success: bool
    data: Optional[ProductInfo] = None
    error: Optional[str] = None
    timestamp: str

class CostSummary(BaseModel):
    """费用汇总"""
    product_name: str
    days: int
    adults: int
    children: int
    seniors: int
    total_people: int
    is_peak: bool
    grand_total: float
    per_person: float

class CostBreakdown(BaseModel):
    """费用明细项"""
    code: str
    name: str
    unit_price: float
    adults: int
    children: int
    seniors: int
    line_total: float
    note: str

class TicketActivityCost(BaseModel):
    """门票活动费用"""
    breakdown: List[CostBreakdown]
    subtotal: float

class HotelCost(BaseModel):
    """酒店费用"""
    hotel_code: str
    hotel_price: float
    rooms: int
    nights: int
    subtotal: float

class TransportCost(BaseModel):
    """交通费用"""
    car_code: str
    car_daily_price: float
    days: int
    car_subtotal: float
    transfer_code: Optional[str]
    transfer_price: float
    transfer_times: int
    transfer_subtotal: float
    subtotal: float

class GuideCost(BaseModel):
    """导游费用"""
    guide_code: Optional[str]
    guide_name: Optional[str]
    daily_price: float
    days: int
    subtotal: float

class CostResponse(BaseModel):
    """费用计算响应"""
    success: bool
    summary: Optional[CostSummary] = None
    ticket_activity: Optional[TicketActivityCost] = None
    hotel: Optional[HotelCost] = None
    transport: Optional[TransportCost] = None
    guide: Optional[GuideCost] = None
    error: Optional[str] = None
    timestamp: str

class CompleteRequest(BaseModel):
    """一键完成请求"""
    intent: UserIntentRequest

class CompleteResponse(BaseModel):
    """一键完成响应"""
    success: bool
    product: Optional[ProductInfo] = None
    cost: Optional[CostResponse] = None
    error: Optional[str] = None
    timestamp: str

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str

# ── API 端点 ─────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
async def root():
    """根路径 - 服务状态检查"""
    return HealthResponse(
        status="running",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/v1/survey", response_model=SurveyResponse)
async def get_survey(api_key: str = Depends(verify_api_key)):
    """
    获取问卷数据
    
    返回结构化的问卷步骤，用于扣子端渲染交互式问卷
    """
    try:
        survey_data = get_beijing_survey()
        return SurveyResponse(
            survey=survey_data,
            total_steps=len(survey_data),
            version="1.0.0"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问卷加载失败: {str(e)}"
        )

@app.post("/api/v1/recommend", response_model=ProductResponse)
async def get_recommendation(
    intent: UserIntentRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    获取产品推荐
    
    根据用户意图匹配最适合的旅游产品
    """
    try:
        # 转换 Pydantic 模型为字典
        user_intent = intent.model_dump()
        
        # 调用产品引擎
        product = get_product_recommendation(user_intent)
        
        if product.get("error"):
            return ProductResponse(
                success=False,
                error=product["error"],
                timestamp=datetime.now().isoformat()
            )
        
        return ProductResponse(
            success=True,
            data=ProductInfo(**product),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        return ProductResponse(
            success=False,
            error=f"推荐失败: {str(e)}",
            timestamp=datetime.now().isoformat()
        )

@app.post("/api/v1/cost", response_model=CostResponse)
async def calculate_cost(
    intent: UserIntentRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    计算行程费用
    
    根据用户意图和产品信息计算详细报价
    """
    try:
        user_intent = intent.model_dump()
        
        # 先获取产品推荐
        product = get_product_recommendation(user_intent)
        
        if product.get("error"):
            return CostResponse(
                success=False,
                error=product["error"],
                timestamp=datetime.now().isoformat()
            )
        
        # 计算费用
        cost_result = calculate_total_cost(product, user_intent)
        
        return CostResponse(
            success=True,
            summary=CostSummary(**cost_result["summary"]),
            ticket_activity=TicketActivityCost(**cost_result["ticket_activity"]),
            hotel=HotelCost(**cost_result["hotel"]),
            transport=TransportCost(**cost_result["transport"]),
            guide=GuideCost(**cost_result["guide"]),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        return CostResponse(
            success=False,
            error=f"费用计算失败: {str(e)}",
            timestamp=datetime.now().isoformat()
        )

@app.post("/api/v1/complete", response_model=CompleteResponse)
async def complete_planning(
    request: CompleteRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    一键完成行程规划
    
    整合推荐和报价，一次调用返回完整结果
    """
    try:
        user_intent = request.intent.model_dump()
        
        # 获取产品推荐
        product = get_product_recommendation(user_intent)
        
        if product.get("error"):
            return CompleteResponse(
                success=False,
                error=product["error"],
                timestamp=datetime.now().isoformat()
            )
        
        # 计算费用
        cost_result = calculate_total_cost(product, user_intent)
        
        return CompleteResponse(
            success=True,
            product=ProductInfo(**product),
            cost=CostResponse(
                success=True,
                summary=CostSummary(**cost_result["summary"]),
                ticket_activity=TicketActivityCost(**cost_result["ticket_activity"]),
                hotel=HotelCost(**cost_result["hotel"]),
                transport=TransportCost(**cost_result["transport"]),
                guide=GuideCost(**cost_result["guide"]),
                timestamp=datetime.now().isoformat()
            ),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        return CompleteResponse(
            success=False,
            error=f"规划失败: {str(e)}",
            timestamp=datetime.now().isoformat()
        )

# ── 飞书 API 扩展接口（预留）──────────────────────────────────────

class FeishuWebhookRequest(BaseModel):
    """飞书 Webhook 请求"""
    challenge: Optional[str] = Field(None, description="飞书验证挑战")
    token: Optional[str] = Field(None, description="验证 Token")
    type: Optional[str] = Field(None, description="事件类型")
    event: Optional[Dict[str, Any]] = Field(None, description="事件数据")

class FeishuWebhookResponse(BaseModel):
    """飞书 Webhook 响应"""
    challenge: Optional[str] = None
    message: str = "ok"

@app.post("/api/v1/feishu/webhook", response_model=FeishuWebhookResponse)
async def feishu_webhook(request: FeishuWebhookRequest):
    """
    飞书机器人 Webhook 接口（预留）
    
    用于接收飞书事件推送，实现飞书机器人集成
    目前返回验证响应，后续可扩展为处理消息事件
    """
    # 飞书首次配置时的 URL 验证
    if request.challenge:
        return FeishuWebhookResponse(challenge=request.challenge)
    
    # TODO: 实现飞书消息处理逻辑
    # 1. 解析用户消息
    # 2. 调用行程规划逻辑
    # 3. 返回格式化结果
    
    return FeishuWebhookResponse(message="收到飞书事件")

@app.post("/api/v1/feishu/card", response_model=Dict[str, Any])
async def feishu_card_template(
    intent: UserIntentRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    飞书卡片模板接口（预留）
    
    返回飞书交互卡片 JSON，用于在飞书中展示行程
    """
    try:
        user_intent = intent.model_dump()
        product = get_product_recommendation(user_intent)
        
        if product.get("error"):
            return {"success": False, "error": product["error"]}
        
        cost_result = calculate_total_cost(product, user_intent)
        
        # 构建飞书卡片模板（简化版）
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🗺️ {product['product_name']}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**行程天数:** {product['days']} 天\n**团费总计:** ¥{cost_result['summary']['grand_total']:.0f}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**每日行程:**\n{product['itinerary']}"
                    }
                }
            ]
        }
        
        return {"success": True, "card": card}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── 错误处理 ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"服务器内部错误: {str(exc)}",
            "timestamp": datetime.now().isoformat()
        }
    )

# ── 启动入口 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
