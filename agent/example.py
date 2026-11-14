"""
最小可运行入口：验证 Python AI Agent 环境与 DashScope/Qwen 调用。
不依赖 Milvus/Redis，仅使用 LCEL 调用 ChatTongyi。
"""
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

def main():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("请在 .env 中设置 DASHSCOPE_API_KEY")
        return
    model_name = os.getenv("MODEL_NAME", "qwen-plus")

    model = ChatTongyi(model=model_name)
    prompt = ChatPromptTemplate.from_messages([
        ("human", "{question}"),
    ])
    chain = prompt | model | StrOutputParser()

    reply = chain.invoke({"question": "用一句话介绍你自己。"})
    print("模型回复:", reply)

if __name__ == "__main__":
    main()
