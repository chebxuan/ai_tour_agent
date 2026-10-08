from langgraph.graph import StateGraph, END
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput
)
from graphs.nodes.narrative_analysis_node import narrative_analysis_node

# 创建状态图，指定工作流的入参和出参
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点
builder.add_node("narrative_analysis", narrative_analysis_node, metadata={"type": "agent", "llm_cfg": "config/narrative_analysis_cfg.json"})

# 设置入口点
builder.set_entry_point("narrative_analysis")

# 添加边
builder.add_edge("narrative_analysis", END)

# 编译图
main_graph = builder.compile()
