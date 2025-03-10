import os
import re
import shutil
from ollama import chat
from tavily import TavilyClient
from pydantic import BaseModel
from langchain_community.document_loaders import CSVLoader, TextLoader, PDFPlumberLoader
from Module.vector_db import add_documents

class Evaluation(BaseModel):
    is_relevant: bool

class Queries(BaseModel):
    queries: list[str]

def parse_output(text):
    think = re.search(r'<think>(.*?)</think>', text, re.DOTALL).group(1).strip()
    output = re.search(r'</think>\s*(.*?)$', text, re.DOTALL).group(1).strip()

    return {
        "reasoning": think,
        "response": output
    }

def format_documents_with_metadata(documents):
    """
        将文档列表转换为包含元数据的格式化字符串。

    Args:
        documents: 文档对象的列表

    Returns:
        包含文档内容和元数据的字符串
    """
    formatted_docs = []
    for doc in documents:
        source = doc.metadata.get('source', 'Unknown source')
        formatted_doc = f"Source: {source}\nContent: {doc.page_content}"
        formatted_docs.append(formatted_doc)

    return "\n\n---\n\n".join(formatted_docs)

def invoke_ollama(model, system_prompt, user_prompt, output_format=None):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response = chat(
        messages=messages,
        model=model,
        format=output_format.model_json_schema() if output_format else None
    )

    if output_format:
        return output_format.model_validate_json(response.message.content)
    else:
        return response.message.content
    
def invoke_llm(
    model,
    system_prompt,
    user_prompt,
    output_format=None,
    temperature=0
):
        
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=model, 
        temperature=temperature,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base= "https://openrouter.ai/api/v1",
    )
    
    # 如果提供了响应格式，使用结构化输出
    if output_format:
        llm = llm.with_structured_output(output_format)
    
    # Invoke LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response = llm.invoke(messages)
    
    if output_format:
        return response
    return response.content # str response

def tavily_search(query, include_raw_content=True, max_results=3):
    """ 使用Tavily API联网搜索

    Args:
        query (str)：执行的搜索查询
        include_raw_content (bool)：是否在格式化字符串中包含来自Tavily的raw_content
        max_results (int)：返回的最大结果数

    Returns:
        dict: Search response 包含:
            - results (list)：搜索结果字典的列表，每个字典包含:
                - title (str): 查询结果的标题
                - url (str): 查询结果的url
                - content (str): 内容的片段/摘要
                - raw_content (str): 页面的完整内容，需判断可用"""

    tavily_client = TavilyClient()
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content
    )

def get_report_structures(reports_folder="reply template"):
    """
    从指定文件加载模板结构。
    返回字典格式的模板结构.
    """
    report_structures = {}

    # 如果文件夹不存在，创建该文件夹
    os.makedirs(reports_folder, exist_ok=True)

    try:
        # 列出文件夹中所有的.md和.txt文件
        for filename in os.listdir(reports_folder):
            if filename.endswith(('.md', '.txt')):
                report_name = os.path.splitext(filename)[0]  # Remove extension
                file_path = os.path.join(reports_folder, filename)

                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        report_structures[report_name] = {
                            "content": content
                        }
                except Exception as e:
                    print(f"加载错误 {filename}: {str(e)}")

    except Exception as e:
        print(f"加载文件夹错误: {str(e)}")

    return report_structures

def process_uploaded_files(uploaded_files):
    temp_folder = "temp_files"
    os.makedirs(temp_folder, exist_ok=True)

    try:
        for uploaded_file in uploaded_files:
            file_extension = uploaded_file.name.split(".")[-1].lower()
            temp_file_path = os.path.join(temp_folder, uploaded_file.name)

            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            # 选择合适的加载程序
            if file_extension == "csv":
                loader = CSVLoader(temp_file_path)
            elif file_extension in ["txt", "md"]:
                loader = TextLoader(temp_file_path)
            elif file_extension == "pdf":
                loader = PDFPlumberLoader(temp_file_path)
            else:
                continue

            # 加载和追加文档
            docs = loader.load()
            add_documents(docs)

        return True
    finally:
        # 删除临时文件夹及其内容
        shutil.rmtree(temp_folder, ignore_errors=True)