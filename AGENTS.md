# AGENTS.md

> 项目概览详见 [README.md](./README.md)

## 运行命令

```bash
# Web 界面
streamlit run app.py

# 命令行测试
python client.py
```

## 架构

本项目是基于 **LangGraph** 的有向图 Agent，工作流如下：

```
用户输入 → 生成查询 → 分批检索(并行) → 总结 → 最终报告
                ↓
    [子图: RAG检索 → 相关性评估 → (联网搜索回退) → 总结]
```

- **主图**: `Module/graph.py` → `researcher` (入口图对象)
- **子图**: `query_search_subgraph` — 每条查询独立运行 RAG + 评估 + 可选联网搜索
- **状态**: `Module/state.py` — `ResearcherState`(主图) 和 `QuerySearchState`(子图)

## 技术栈

| 组件 | 用途 |
|------|------|
| Ollama  | 本地 LLM |
| ChromaDB | 向量存储 |
| SentenceTransformer (all-MiniLM-L6-v2) | 嵌入模型 |
| Tavily API | 联网搜索回退 |
| Streamlit | Web UI |
| Pydantic | 结构化输出解析 |

## 关键约定

- 所有 LLM 调用通过 `Module/utils.py` 的 `invoke_ollama()`（本地）或 `invoke_llm()`（OpenRouter）进行
- LLM 的结构化输出使用 Pydantic BaseModel 定义（`Queries`, `Evaluation`）
- Prompt 模板统一在 `Module/prompts.py` 中管理
- DeepSeek R1 的 `<｜end▁of▁thinking｜> 标签：在最终输出前用 `parse_output()` 剥离

## 注意事项

- **Ollama 服务必须运行**：确保 `ollama serve` 已在本地启动
- **`.env` 文件必需**：需配置 `TAVILY_API_KEY` 用于联网搜索（可选，也可在 UI 中关闭）
- **向量库初始化**：首次运行需在 `files/` 目录下放置文档，向量库会自动创建
- **路径问题**：`vector_db.py` 和部分配置中使用了绝对路径 (`D:/work/pycharm/...`)，在新环境需调整
- **嵌入模型**：`all-MiniLM-L6-v2/` 目录为本地嵌入模型文件，首次使用需确保路径正确
- **已注释代码**：graph.py 和 utils.py 中保留了 OpenRouter 替代方案的注释代码，如需切换外部 LLM 可取消注释
