from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import SecretStr

import time
from langchain_core.exceptions import OutputParserException

from dotenv import load_dotenv

load_dotenv()

import os
api_key = os.environ["OPENAI_API_KEY"]
api_base_url = os.environ["OPENAI_API_BASE_URL"]
llm = ChatOpenAI(model="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", temperature=0.7, api_key=SecretStr(api_key), base_url=api_base_url)

def robust_llm_node(state: dict) -> dict:
    """带重试的 LLM 节点"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = llm.invoke([HumanMessage(content=state["prompt"])])
            return {"result": response.content}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避, like computer networks do to avoid overwhelming the server
                continue
            else:
                return {"result": f"错误：{str(e)}", "error": True}
    

# ===== State =====
class ContentState(TypedDict):
    topic: str
    keywords: str
    outline: str
    article: str

# ===== 节点 =====

def extract_keywords(state: ContentState) -> dict:
    """提取关键词"""
    response = llm.invoke([
        HumanMessage(content=f"从主题'{state['topic']}'中提取 5 个核心关键词，用逗号分隔，只输出关键词：")
    ])
    return {"keywords": response.content.strip()}

def create_outline(state: ContentState) -> dict:
    """根据关键词生成大纲"""
    response = llm.invoke([
        HumanMessage(content=(
            f"基于主题'{state['topic']}'和关键词'{state['keywords']}'，"
            f"生成一个 4 节的文章大纲，每节一行，格式为：数字. 标题"
        ))
    ])
    return {"outline": response.content.strip()}

def write_article(state: ContentState) -> dict:
    """根据大纲写文章"""
    response = llm.invoke([
        HumanMessage(content=(
            f"根据以下大纲，写一篇关于'{state['topic']}'的短文（约 300 字）：\n\n"
            f"{state['outline']}"
        ))
    ])
    return {"article": response.content.strip()}

# ===== 图 =====

graph = StateGraph(ContentState)
graph.add_node("keywords", extract_keywords)
graph.add_node("outline", create_outline)
graph.add_node("write", write_article)

graph.set_entry_point("keywords")
graph.add_edge("keywords", "outline")
graph.add_edge("outline", "write")
graph.add_edge("write", END)

app = graph.compile()

# ===== 运行 =====
if __name__ == "__main__":
    result = app.invoke({
        "topic": "LangGraph 状态图编程",
        "keywords": "",
        "outline": "",
        "article": "",
    })

    print("关键词:", result["keywords"])
    print("\n大纲:\n", result["outline"])
    print("\n文章:\n", result["article"])