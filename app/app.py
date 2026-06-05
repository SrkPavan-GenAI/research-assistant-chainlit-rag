import os
import chainlit as cl
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# -------------------------------------------------
# 1. Load environment variables
# -------------------------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------------------------------
# 2. Load PDFs
# -------------------------------------------------
PDF_DIR = "pdfs"
documents = []

for file in os.listdir(PDF_DIR):
    if file.endswith(".pdf"):
        loader = PyPDFLoader(os.path.join(PDF_DIR, file))
        documents.extend(loader.load())

# -------------------------------------------------
# 3. Split into chunks
# -------------------------------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(documents)

# -------------------------------------------------
# 4. Embeddings + Vector Store
# -------------------------------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="db"
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# -------------------------------------------------
# 5. Gemini LLM
# -------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=GEMINI_API_KEY,
    temperature=0.2
)

# -------------------------------------------------
# 6. RAG Prompt + Chain
# -------------------------------------------------
prompt = ChatPromptTemplate.from_template("""
You are an AI assistant. Answer ONLY using the context below.

Context:
{context}

Question:
{question}

Answer:
""")

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# -------------------------------------------------
# 7. Chainlit UI
# -------------------------------------------------
@cl.on_chat_start
async def start():
    await cl.Message(
        content="👋 Hi Buddy! Your RAG Chainlit app is ready. Ask me anything from the PDFs!"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    answer = rag_chain.invoke(message.content)
    await cl.Message(content=answer).send()