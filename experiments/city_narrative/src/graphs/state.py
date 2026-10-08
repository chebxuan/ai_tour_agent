from typing import Optional, Literal, List
from pydantic import BaseModel, Field

class GlobalState(BaseModel):
    """全局状态定义"""
    raw_content: str = Field(default="", description="原始文本内容（可直接输入或从网页抓取）")
    analysis_result: dict = Field(default={}, description="叙事解构分析结果")

class GraphInput(BaseModel):
    """工作流的输入"""
    raw_content: str = Field(..., description="原始文本内容（小红书文案、文章内容等）")

class GraphOutput(BaseModel):
    """工作流的输出"""
    analysis_result: dict = Field(..., description="叙事解构分析结果（JSON格式）")

class BatchGraphInput(BaseModel):
    """批量处理的输入"""
    notes: List[str] = Field(..., description="笔记列表，每个笔记是一个字符串")
    region_id: int = Field(..., description="区域ID")
    region_name: str = Field(..., description="区域名称")

class BatchGraphOutput(BaseModel):
    """批量处理的输出"""
    region_id: int = Field(..., description="区域ID")
    region_name: str = Field(..., description="区域名称")
    all_nodes: List[dict] = Field(..., description="所有提取的地标节点")
    total_count: int = Field(..., description="节点总数")
    notes_processed: int = Field(..., description="处理的笔记数量")

class FetchContentInput(BaseModel):
    """内容抓取节点的输入"""
    xhs_url: str = Field(..., description="小红书链接")

class FetchContentOutput(BaseModel):
    """内容抓取节点的输出"""
    raw_content: str = Field(..., description="从网页提取的文本内容")

class NarrativeAnalysisInput(BaseModel):
    """叙事解构节点的输入"""
    raw_content: str = Field(..., description="从网页提取的文本内容")

class NarrativeAnalysisOutput(BaseModel):
    """叙事解构节点的输出"""
    analysis_result: dict = Field(..., description="叙事解构分析结果（JSON格式）")
