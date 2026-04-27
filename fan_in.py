from typing import TypedDict, Annotated, List
import operator
from langgraph.graph import StateGraph, END

# ===== State =====
class CricketState(TypedDict):
    player_name: str
    batting_avg: float
    bowling_avg: float
    fielding_rating: float
    analyses: Annotated[List[str], operator.add]  # 三个并行节点的输出
    final_report: str

# ===== 并行节点 =====

def analyze_batting(state: CricketState) -> dict:
    """分析击球表现"""
    avg = state["batting_avg"]

    if avg >= 50:
        level = "世界级"
    elif avg >= 35:
        level = "优秀"
    elif avg >= 20:
        level = "一般"
    else:
        level = "较弱"

    analysis = f"[击球] 平均分 {avg}，评级：{level}"
    return {"analyses": [analysis]}

def analyze_bowling(state: CricketState) -> dict:
    """分析投球表现（投球均值越低越好）"""
    avg = state["bowling_avg"]

    if avg <= 20:
        level = "世界级"
    elif avg <= 30:
        level = "优秀"
    elif avg <= 40:
        level = "一般"
    else:
        level = "较弱"

    analysis = f"[投球] 平均分 {avg}，评级：{level}"
    return {"analyses": [analysis]}

def analyze_fielding(state: CricketState) -> dict:
    """分析防守表现"""
    rating = state["fielding_rating"]

    if rating >= 8:
        level = "出色"
    elif rating >= 6:
        level = "良好"
    elif rating >= 4:
        level = "一般"
    else:
        level = "需改进"

    analysis = f"[防守] 评分 {rating}/10，评级：{level}"
    return {"analyses": [analysis]}

# ===== 汇聚节点 =====

def aggregate_results(state: CricketState) -> dict:
    """汇聚三个分析结果，生成总报告"""
    name = state["player_name"]
    analyses = state["analyses"]

    report = f"=== {name} 综合评估报告 ===\n"
    for a in analyses:
        report += f"  {a}\n"

    # 计算综合评分（简化逻辑）
    score = (
        min(state["batting_avg"] / 50, 1.0) * 40 +
        max(0, (40 - state["bowling_avg"]) / 40) * 40 +
        state["fielding_rating"] / 10 * 20
    )
    report += f"\n综合得分：{score:.1f} / 100"

    return {"final_report": report}

# ===== 入口节点 =====

def start_node(state: CricketState) -> dict:
    """入口节点：什么都不做，只是作为 Fan-out 的起点"""
    return {}

# ===== 组装图 =====

graph = StateGraph(CricketState)

graph.add_node("start", start_node)
graph.add_node("batting", analyze_batting)
graph.add_node("bowling", analyze_bowling)
graph.add_node("fielding", analyze_fielding)
graph.add_node("aggregate", aggregate_results)

graph.set_entry_point("start")

# Fan-out：start 同时触发三个分析节点
graph.add_edge("start", "batting")
graph.add_edge("start", "bowling")
graph.add_edge("start", "fielding")

# Fan-in：三个节点都汇入 aggregate
graph.add_edge("batting", "aggregate")
graph.add_edge("bowling", "aggregate")
graph.add_edge("fielding", "aggregate")

graph.add_edge("aggregate", END)

app = graph.compile()

result = app.invoke({
    "player_name": "Virat Kohli",
    "batting_avg": 59.8,
    "bowling_avg": 34.0,
    "fielding_rating": 9.0,
    "analyses": [],
    "final_report": "",
})

print(result["final_report"])