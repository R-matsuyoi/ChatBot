import os
from langchain_community.document_loaders import DirectoryLoader
from langchain_experimental.text_splitter import SemanticChunker 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

VECTOR_DB_PATH = "database"
 
def get_or_create_vector_db():
    """获取或创建向量库"""
    embeddings = HuggingFaceEmbeddings(model_name='D:/work/pycharm/Project/ChatBot/all-MiniLM-L6-v2')

    if os.path.exists(VECTOR_DB_PATH) and os.listdir(VECTOR_DB_PATH):
        # 使用存在的 vector store
        vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embeddings)
    else:
        # 加载文档后建立新词向量库
        loader = DirectoryLoader("D:/work/pycharm/Project/ChatBot/files")
        docs = loader.load()

        # 处理新文档
        semantic_text_splitter = SemanticChunker(embeddings)
        documents = semantic_text_splitter.split_documents(docs)

        # 将结果文档拆分为更小的块
        # 使用RecursiveCharacterTextSplitter来设置块大小
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        split_documents = text_splitter.split_documents(documents)
        vectorstore = Chroma.from_documents(split_documents, embeddings, persist_directory=VECTOR_DB_PATH)

    return vectorstore

def add_documents(documents):
    """
        将新文档添加到现有的向量库中。


    Args:
        documents: 要添加到vector存储的文档列表
    """
    embeddings = HuggingFaceEmbeddings()

    # 处理新文档
    semantic_text_splitter = SemanticChunker(embeddings)
    documents = semantic_text_splitter.split_documents(documents)

    # 将结果文档拆分为更小的块
    # 使用RecursiveCharacterTextSplitter来设置块大小
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
    split_documents = text_splitter.split_documents(documents)

    if os.path.exists(VECTOR_DB_PATH) and os.listdir(VECTOR_DB_PATH):
        # 使用存在的 vector store
        vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embeddings)
        vectorstore.add_documents(split_documents)
    else:
        # 加载文档后建立新词向量库
        vectorstore = Chroma.from_documents(
            split_documents,
            embeddings,
            persist_directory=VECTOR_DB_PATH
        )

    return vectorstore