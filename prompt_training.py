from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()

import os
api_key = os.environ["OPENAI_API_KEY"]
api_base_url = os.environ["OPENAI_API_BASE_URL"]
llm = ChatOpenAI(model="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", temperature=0.7, api_key=SecretStr(api_key), base_url=api_base_url)

# ===== State =====
class BlogState(TypedDict):
    topic: str
    outline: str
    draft: str
    final_article: str

# ===== 节点  =====

# def generate_outline(state: BlogState) -> dict:
#     """第一步：生成文章大纲"""
#     topic = state["topic"]

#     # 这里用占位符表示 LLM 调用，下面会展示真实代码
#     prompt = f"""为以下主题创建一个清晰的博客文章大纲：

# 主题：{topic}

# 请提供：
# 1. 引言要点
# 2. 3-4 个主要章节标题
# 3. 结论要点

# 大纲："""

#     # outline = llm.invoke(prompt)  # 替换成真实 LLM 调用
#     # 示例输出（演示用）
#     outline = f"""
# ## {topic} 完整指南

# **引言**：介绍 {topic} 的背景和重要性

# **第一章：基础概念**
# - 核心定义
# - 关键术语

# **第二章：实现方式**
# - 主流方案对比
# - 最佳实践

# **第三章：实战案例**
# - 具体示例
# - 常见问题

# **结论**：总结要点，给出建议
# """.strip()

    # return {"outline": outline}
def generate_outline(state: BlogState) -> dict:
    topic = state["topic"]
    prompt = f"为主题'{topic}'创建博客大纲（3-4个章节）："

    response = llm.invoke([HumanMessage(content=prompt)])
    return {"outline": response.content}

def check_outline_quality(state: BlogState) -> str:
    """检查大纲质量，决定是直接展开还是重新生成"""
    outline = state["outline"]

    # 简单检查：大纲是否包含足够的章节
    if outline.count("##") >= 3:
        return "expand"  # 质量够，继续展开
    else:
        return "regenerate_outline"  # 质量不够，重新生成


def expand_content(state: BlogState) -> dict:
    """第二步：根据大纲生成正文草稿"""
    outline = state["outline"]
    topic = state["topic"]

    prompt = f"""根据以下大纲，为主题"{topic}"写一篇详细的博客文章草稿。
            每个章节至少写 2-3 段，包含具体示例。

            大纲：
            {outline}

            文章草稿："""

    draft = llm.invoke(prompt)  # 替换成真实 LLM 调用
    # draft = f"""# {topic} 完整指南

    # ## 引言

    # {topic} 是现代软件开发中的重要话题...（正文草稿）

    # ## 基础概念

    # 理解 {topic} 首先需要掌握几个核心概念...

    # ## 实现方式

    # 在实际项目中，有多种方式可以实现 {topic}...

    # ## 实战案例

    # 以下是一个典型的 {topic} 应用场景...

    # ## 结论

    # 通过本文的介绍，我们深入了解了 {topic} 的各个方面...
    # """.strip()

    return {"draft": draft}

def polish_article(state: BlogState) -> dict:
    """第三步：润色优化文章"""
    draft = state["draft"]

    prompt = f"""请对以下文章草稿进行润色，使其：
        1. 语言更流畅自然
        2. 逻辑更清晰
        3. 适合技术博客读者

        草稿：
        {draft}

        润色后的文章："""

    final = llm.invoke(prompt)  # 替换成真实 LLM 调用
    # final = draft + "\n\n---\n*（已润色优化）*"

    return {"final_article": final}

# ===== 组装图 =====

graph = StateGraph(BlogState)

graph.add_node("outline", generate_outline)
graph.add_node("expand", expand_content)
graph.add_node("polish", polish_article)

graph.set_entry_point("outline")
graph.add_conditional_edges(
    "outline",
    check_outline_quality,
    {
        "expand": "expand",
        "regenerate_outline": "outline",  # 循环回去重新生成
    }
)
graph.add_edge("expand", "polish")
graph.add_edge("polish", END)

app = graph.compile()

for step in app.stream({
    "topic": "LangGraph 入门指南",
    "outline": "",
    "draft": "",
    "final_article": "",
}):
    node_name = list(step.keys())[0]
    print(f"\n--- [{node_name}] 完成 ---")
    if node_name == "outline":
        print(step["outline"]["outline"])
    elif node_name == "expand":
        print(step["expand"]["draft"])
    elif node_name == "polish":
        print("文章已润色完成")