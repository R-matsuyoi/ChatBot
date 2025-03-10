import datetime
from typing_extensions import Literal
from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from langchain_core.runnables.config import RunnableConfig
from Module.configuration import Configuration
from Module.vector_db import get_or_create_vector_db
from Module.state import ResearcherState, ResearcherStateInput, ResearcherStateOutput, QuerySearchState, \
    QuerySearchStateInput, QuerySearchStateOutput
from Module.prompts import RESEARCH_QUERY_WRITER_PROMPT, RELEVANCE_EVALUATOR_PROMPT, SUMMARIZER_PROMPT, \
    REPORT_WRITER_PROMPT
from Module.utils import format_documents_with_metadata, invoke_llm, invoke_ollama, parse_output, tavily_search, \
    Evaluation, Queries

# 每批并行处理的查询数
# 根据系统的性能进行更改
BATCH_SIZE = 3


def generate_research_queries(state: ResearcherState, config: RunnableConfig):
    print("--- 生成queries ---")
    user_instructions = state["user_instructions"]
    max_queries = config["configurable"].get("max_search_queries", 3)

    query_writer_prompt = RESEARCH_QUERY_WRITER_PROMPT.format(
        max_queries=max_queries,
        date=datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    )

    # 使用本地Deepseek R1模型
    result = invoke_ollama(
        model='deepseek-r1:1.5b',
        system_prompt=query_writer_prompt,
        user_prompt=f"为用户指令生成查询: {user_instructions}",
        output_format=Queries
    )

    # 使用外部LLM提供商与OpenRouter
    # result = invoke_llm(
    #     model='gpt-4o-mini',
    #     system_prompt=query_writer_prompt,
    #     user_prompt=f"Generate research queries for this user instruction: {user_instructions}",
    #     output_format=Queries
    # )

    return {"research_queries": result.queries}


def search_queries(state: ResearcherState):
    # 通过调用initiate_query_research来启动对每个查询的搜索
    print("--- 检索queries ---")
    pass


def initiate_query_research(state: ResearcherState):
    # 使用Send方法并调用“search_and_summarize_query”子图并行地开始对每个查询的搜索
    return [
        Send("search_and_summarize_query", {"query": s})
        for s in state["research_queries"]
    ]


def search_queries(state: ResearcherState):
    # 通过调用initiate_query_research来启动对每个查询的搜索
    print("--- 检索queries ---")
    # Get the current processing position from state or initialize to 0
    current_position = state.get("current_position", 0)

    return {"current_position": current_position + BATCH_SIZE}


def check_more_queries(state: ResearcherState) -> Literal["search_queries", "generate_final_answer"]:
    """核查queries数量"""
    current_position = state.get("current_position", 0)
    if current_position < len(state["research_queries"]):
        return "search_queries"
    return "generate_final_answer"


def initiate_query_research(state: ResearcherState):
    # 获取下一批查询
    queries = state["research_queries"]
    current_position = state["current_position"]
    batch_end = min(current_position, len(queries))
    current_batch = queries[current_position - BATCH_SIZE:batch_end]

    # 返回要处理的查询批次
    return [
        Send("search_and_summarize_query", {"query": s})
        for s in current_batch
    ]


def retrieve_rag_documents(state: QuerySearchState):
    """从RAG数据库检索文档"""
    print("--- 检索 documents ---")
    query = state["query"]
    vectorstore = get_or_create_vector_db()
    vectorstore_retreiver = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    documents = vectorstore_retreiver.invoke(query)

    return {"retrieved_documents": documents}


def evaluate_retrieved_documents(state: QuerySearchState):
    query = state["query"]
    retrieved_documents = state["retrieved_documents"]
    evaluation_prompt = RELEVANCE_EVALUATOR_PROMPT.format(
        query=query,
        documents=format_documents_with_metadata(retrieved_documents)
    )

    # Using local Deepseek R1 model with Ollama
    evaluation = invoke_ollama(
        model='deepseek-r1:1.5b',
        system_prompt=evaluation_prompt,
        user_prompt=f"检索文档，评估与文档用户请求的相关性: {query}",
        output_format=Evaluation
    )

    # 使用外部LLM提供商与OpenRouter
    # evaluation = invoke_llm(
    #     model='gpt-4o-mini',
    #     system_prompt=evaluation_prompt,
    #     user_prompt=f"Evaluate the relevance of the retrieved documents for this query: {query}",
    #     output_format=Evaluation
    # )

    return {"are_documents_relevant": evaluation.is_relevant}


def route_research(state: QuerySearchState, config: RunnableConfig) -> Literal[
    "summarize_query_research", "web_research", "__end__"]:
    """ 根据文件的相关性进行研究 """

    if state["are_documents_relevant"]:
        return "summarize_query_research"
    elif config["configurable"].get("enable_web_search", False):
        return "web_research"
    else:
        print("无相关文档且网络被禁用，该请求跳过")
        return "__end__"


def web_research(state: QuerySearchState):
    print("--- 联网搜索 ---")
    output = tavily_search(state["query"])
    search_results = output["results"]

    return {"web_search_results": search_results}


def summarize_query_research(state: QuerySearchState):
    query = state["query"]

    information = None
    if state["are_documents_relevant"]:
        # 如果文档是相关的：使用RAG文档
        information = state["retrieved_documents"]
    else:
        # 如果文档是不相关的：使用网络搜索结果，
        # 如果启用，否则将跳过上一个路由器节点的查询
        information = state["web_search_results"]

    summary_prompt = SUMMARIZER_PROMPT.format(
        query=query,
        docmuents=information
    )

    summary = invoke_ollama(
        model='deepseek-r1:1.5b',
        system_prompt=summary_prompt,
        user_prompt=f"为这个请求生成一个摘要: {query}"
    )
    # 移除thinking
    summary = parse_output(summary)["response"]

    # 使用外部LLM提供商与OpenRouter
    # summary = invoke_llm(
    #     model='gpt-4o-mini',
    #     system_prompt=summary_prompt,
    #     user_prompt=f"Generate a research summary for this query: {query}"
    # )

    return {"search_summaries": [summary]}


def generate_final_answer(state: ResearcherState, config: RunnableConfig):
    print("--- 生成回答 ---")
    report_structure = config["configurable"].get("report_structure", "")
    answer_prompt = REPORT_WRITER_PROMPT.format(
        instruction=state["user_instructions"],
        report_structure=report_structure,
        information="\n\n---\n\n".join(state["search_summaries"])
    )

    # Using local Deepseek R1 model with Ollama
    result = invoke_ollama(
        model='deepseek-r1:1.5b',
        system_prompt=answer_prompt,
        user_prompt=f"使用提供的信息生成研究摘要。"
    )
    # 移除thinking
    answer = parse_output(result)["response"]

    # 使用外部LLM提供商与OpenRouter
    # answer = invoke_llm(
    #     model='gpt-4o-mini',
    #     system_prompt=answer_prompt,
    #     user_prompt=f"Generate a research summary using the provided information."
    # )

    return {"final_answer": answer}


# 创建用于搜索每个查询的子图
query_search_subgraph = StateGraph(QuerySearchState, input=QuerySearchStateInput, output=QuerySearchStateOutput)

# 定义用于搜索查询的子图节点
query_search_subgraph.add_node(retrieve_rag_documents)
query_search_subgraph.add_node(evaluate_retrieved_documents)
query_search_subgraph.add_node(web_research)
query_search_subgraph.add_node(summarize_query_research)

# 为子图设置入口点并定义转换
query_search_subgraph.add_edge(START, "retrieve_rag_documents")
query_search_subgraph.add_edge("retrieve_rag_documents", "evaluate_retrieved_documents")
query_search_subgraph.add_conditional_edges("evaluate_retrieved_documents", route_research)
query_search_subgraph.add_edge("web_research", "summarize_query_research")
query_search_subgraph.add_edge("summarize_query_research", END)

# 创建主图
researcher_graph = StateGraph(ResearcherState, input=ResearcherStateInput, output=ResearcherStateOutput,
                              config_schema=Configuration)

# 定义主节点
researcher_graph.add_node(generate_research_queries)
researcher_graph.add_node(search_queries)
researcher_graph.add_node("search_and_summarize_query", query_search_subgraph.compile())
researcher_graph.add_node(generate_final_answer)

# 定义主图的关系
researcher_graph.add_edge(START, "generate_research_queries")
researcher_graph.add_edge("generate_research_queries", "search_queries")
researcher_graph.add_conditional_edges("search_queries", initiate_query_research, ["search_and_summarize_query"])
researcher_graph.add_conditional_edges("search_and_summarize_query", check_more_queries)
researcher_graph.add_edge("generate_final_answer", END)

# 创建主图对象
researcher = researcher_graph.compile()
