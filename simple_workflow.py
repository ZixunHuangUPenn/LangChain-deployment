from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

# ===== State 定义 =====
class BMIState(TypedDict):
    name: str
    height_cm: float
    weight_kg: float
    bmi: float
    category: str
    advice: str
    report: str
    error: Optional[str]

# ===== 节点定义 =====

def validate_input(state: BMIState) -> dict:
    """验证输入数据"""
    height = state["height_cm"]
    weight = state["weight_kg"]

    if height <= 0 or height > 300:
        return {"error": f"身高数据异常: {height}cm"}
    if weight <= 0 or weight > 500:
        return {"error": f"体重数据异常: {weight}kg"}

    return {"error": None}

def calculate_bmi(state: BMIState) -> dict:
    """计算 BMI"""
    if state.get("error"):
        return {}

    height_m = state["height_cm"] / 100
    bmi = state["weight_kg"] / (height_m ** 2)
    bmi = round(bmi, 2)

    return {"bmi": bmi}

def classify_bmi(state: BMIState) -> dict:
    """BMI 分类"""
    if state.get("error"):
        return {}

    bmi = state["bmi"]

    if bmi < 18.5:
        category = "偏瘦"
    elif bmi < 24.9:
        category = "正常"
    elif bmi < 29.9:
        category = "超重"
    else:
        category = "肥胖"

    return {"category": category}

def generate_advice(state: BMIState) -> dict:
    """生成健康建议"""
    if state.get("error"):
        return {}

    category = state["category"]
    advice_map = {
        "偏瘦": "建议适量增加营养摄入，加强力量训练，必要时咨询营养师。",
        "正常": "保持当前的饮食和运动习惯，定期体检。",
        "超重": "建议控制饮食，每周至少进行 150 分钟中等强度有氧运动。",
        "肥胖": "建议在医生指导下制定减重计划，注意饮食结构和规律运动。",
    }

    return {"advice": advice_map[category]}

def format_report(state: BMIState) -> dict:
    """生成最终报告"""
    if state.get("error"):
        report = f"错误：{state['error']}"
    else:
        report = f"""
=== BMI 健康报告 ===
姓名：{state['name']}
身高：{state['height_cm']} cm
体重：{state['weight_kg']} kg
BMI：{state['bmi']}
分类：{state['category']}
建议：{state['advice']}
""".strip()

    return {"report": report}

# ===== 组装图 =====

graph = StateGraph(BMIState)

# 添加节点
graph.add_node("validate", validate_input)
graph.add_node("calculate", calculate_bmi)
graph.add_node("classify", classify_bmi)
graph.add_node("advise", generate_advice)
graph.add_node("format", format_report)

# 设置顺序边
graph.set_entry_point("validate")
graph.add_edge("validate", "calculate")
graph.add_edge("calculate", "classify")
graph.add_edge("classify", "advise")
graph.add_edge("advise", "format")
graph.add_edge("format", END)

app = graph.compile()

# 正常输入
chunks = app.stream({
    "name": "张三",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "bmi": 0.0,
    "category": "",
    "advice": "",
    "report": "",
    "error": None,
})
for chunk in chunks:
    print(chunk)