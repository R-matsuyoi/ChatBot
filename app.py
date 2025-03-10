import pyperclip
import streamlit as st
import streamlit_nested_layout
from Module import researcher
from Module import get_report_structures, process_uploaded_files
from dotenv import load_dotenv

load_dotenv()


def generate_response(user_input, enable_web_search, report_structure, max_search_queries):
    """
    使用agent和stream steps生成响应
    """
    # 初始化状态
    initial_state = {
        "user_instructions": user_input,
    }

    # Langgraph config
    config = {"configurable": {
        "enable_web_search": enable_web_search,
        "report_structure": report_structure,
        "max_search_queries": max_search_queries,
    }}

    # 为 global process 创建状态
    langgraph_status = st.status("**Researcher Running...**", state="running")

    with langgraph_status:
        generate_queries_expander = st.expander("Generate Research Queries", expanded=False)
        search_queries_expander = st.expander("Search Queries", expanded=True)
        final_answer_expander = st.expander("Generate Final Answer", expanded=False)

        steps = []

        # 运行 graph 和 stream outputs
        for output in researcher.stream(initial_state, config=config):
            for key, value in output.items():
                expander_label = key.replace("_", " ").title()

                if key == "generate_research_queries":
                    with generate_queries_expander:
                        st.write(value)

                elif key.startswith("search_and_summarize_query"):
                    with search_queries_expander:
                        with st.expander(expander_label, expanded=False):
                            st.write(value)

                elif key == "generate_final_answer":
                    with final_answer_expander:
                        st.write(value)

                steps.append({"step": key, "content": value})

    # 更新状态
    langgraph_status.update(state="complete", label="**Using Langgraph** (Research completed)")

    # 返回最终报告
    return steps[-1]["content"] if steps else "No response generated"


def clear_chat():
    st.session_state.messages = []
    st.session_state.processing_complete = False
    st.session_state.uploader_key = 0


def main():
    st.set_page_config(page_title="DeepSeek RAG Researcher", layout="wide")

    # Initialize session states
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_report_structure" not in st.session_state:
        st.session_state.selected_report_structure = None
    if "max_search_queries" not in st.session_state:
        st.session_state.max_search_queries = 5
    if "files_ready" not in st.session_state:
        st.session_state.files_ready = False  # 如果文件上传但未处理时Tracks

    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("🤖 RAG Chat Bot 🤖")
    with col2:
        if st.button("清空聊天", use_container_width=True):
            clear_chat()
            st.rerun()

    st.sidebar.title("设置")

    report_structures = get_report_structures()
    default_report = "template1"

    selected_structure = st.sidebar.selectbox(
        "选择回复模板",
        options=list(report_structures.keys()),
        index=list(map(str.lower, report_structures.keys())).index(default_report)
    )

    st.session_state.selected_report_structure = report_structures[selected_structure]

    # 最大输入请求数
    st.session_state.max_search_queries = st.sidebar.number_input(
        "最大搜索请求数",
        min_value=1,
        max_value=10,
        value=st.session_state.max_search_queries,
        help="为单次问题建立的搜索请求设置最大值 (1-10)"
    )

    enable_web_search = st.sidebar.checkbox("启用联网搜索", value=True)

    # 上传文档
    uploaded_files = st.sidebar.file_uploader(
        "上传文档",
        type=["pdf", "txt", "csv", "md"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}"
    )

    # 检查文件是否已上传但尚未处理
    if uploaded_files:
        st.session_state.files_ready = True
        st.session_state.processing_complete = False

    # 仅当文件上传但未处理时显示“文档记忆中...”按钮**
    if st.session_state.files_ready and not st.session_state.processing_complete:
        process_button_placeholder = st.sidebar.empty()

        with process_button_placeholder.container():
            process_clicked = st.button("记忆该文档", use_container_width=True)

        if process_clicked:
            with process_button_placeholder:
                with st.status("文档记忆中...", expanded=False) as status:
                    # Process files (Replace this with your actual function)
                    if process_uploaded_files(uploaded_files):
                        st.session_state.processing_complete = True
                        st.session_state.files_ready = False
                        st.session_state.uploader_key += 1

                    status.update(label="文档记忆成功!", state="complete", expanded=False)
                    # st.rerun()

    # 显示聊天信息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

            # 在底部显示AI信息的复制按钮
            if message["role"] == "assistant":
                if st.button("📋", key=f"copy_{len(st.session_state.messages)}"):
                    pyperclip.copy(message["content"])

    # 聊天输入和响应处理
    if user_input := st.chat_input("此处输入信息..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # 生成并显示响应
        report_structure = st.session_state.selected_report_structure["content"]
        assistant_response = generate_response(
            user_input,
            enable_web_search,
            report_structure,
            st.session_state.max_search_queries
        )

        # 存储信息
        st.session_state.messages.append({"role": "assistant", "content": assistant_response["final_answer"]})

        with st.chat_message("assistant"):
            st.write(assistant_response["final_answer"])

            # Copy button below the AI message
            if st.button("📋", key=f"copy_{len(st.session_state.messages)}"):
                pyperclip.copy(assistant_response["final_answer"])


if __name__ == "__main__":
    main()
