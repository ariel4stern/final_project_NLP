import gradio as gr
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_community.document_loaders import Docx2txtLoader
from langchain_openai import ChatOpenAI
from transformers import pipeline
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-large"
HF_LLM_MODEL = "google/flan-t5-large"
CHROMA_DIR = "main_dir_chroma"

vectorstores = {}
current_collection = None


def get_llm():

    if os.getenv("OPENAI_API_KEY") is None:
        print("free llm")
        llm = pipeline(
            "text2text-generation",
            model=HF_LLM_MODEL
        )

    else:
        llm = ChatOpenAI(model="gpt-4o-mini",
                         temperature=0,
                         max_tokens=300)
    return llm

def load_and_index(docx_path: str):
    """Load a PDF, chunk it, embed it, and return a retriever."""
    loader = Docx2txtLoader(docx_path)
    pages = loader.load()
    file_name = os.path.basename(docx_path).split(".")[0]

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(pages)

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL) if os.getenv("OPENAI_API_KEY") else HuggingFaceEmbeddings()

    if os.path.exists(f"{CHROMA_DIR}/{file_name}"):
        db = Chroma(
            embedding_function=embeddings,
            persist_directory=f"{CHROMA_DIR}/{file_name}",
        )

    else:
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=f"{CHROMA_DIR}/{file_name}",
        )

    return db,file_name

def build_prompt(question: str, docs, history):
    context_parts = []

    if not docs:
        return None

    for idx, doc in enumerate(docs, start=1):
        page = doc.metadata.get("page")
        page_text = f"page {page+1}" if isinstance(page, int) else "unknown page"
        context_parts.append(f"[{idx} | {page_text}]\n{doc.page_content}")

    recent_history = history[-6:] if history else []
    history_lines = []

    print(recent_history)

    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")

    print(history_lines)
    context_text = "\n\n".join(context_parts) if context_parts else "No context found."
    history_text = "\n".join(history_lines) if history_lines else "No prior chat history."

    return ("You are a QA assistant. Answer ONLY using the provided context.\n"
            "When answering, cite sources using Number\n."
            "Answer briefly in plain language.\n"
            "Use chat history only to understand the question, not as a source of information.\n\n"
            f"Chat history:\n{history_text}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n"
    )

def upload_docx(docx_file):
    """Called when user uploads a DOCX."""

    if docx_file is None:
        return "No file uploaded.", []

    db,name = load_and_index(docx_file.name)
    print(name)
    print(vectorstores)
    vectorstores[name] = db

    return "DOCX indexed.", [] ,name

def ask_question(question, history, collection_name):
    global vectorstores

    history = history or []

    if not question:
        return history

    if collection_name not in vectorstores:
        return history + [
            {"role": "assistant", "content": "No document selected."}
        ]

    db = vectorstores[collection_name]

    docs = db.as_retriever(search_kwargs={"k": 4}).invoke(question)

    prompt = build_prompt(question, docs, history)

    if prompt is None:
        return history + [
            {"role": "assistant", "content": "No document selected."}
        ]

    llm_n = get_llm()

    result = llm_n.invoke(prompt) if hasattr(llm_n, "invoke") else llm_n(prompt)

    if hasattr(result, "content"):
        answer = result.content
    elif isinstance(result, list) and len(result) > 0:
        answer = result[0].get("generated_text",str(result))
    else:
        answer = str(result)

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    return history


with gr.Blocks(title="Chat with Your DOCX") as demo:
    gr.Markdown("## Chat with Your DOCX,\nUpload a DOCX and ask questions.")

    collection_state = gr.State()

    with gr.Row():
        docx_input = gr.File(label="Upload DOCX", file_types=[".docx"],height=100)
        status = gr.Textbox(label="Status", interactive=False)

    chatbot = gr.Chatbot(label="Conversation", height=300)
    question_input = gr.Textbox(placeholder="Ask a question about your DOCX...", label="Question")

    docx_input.change(fn=upload_docx, inputs=docx_input, outputs=[status, chatbot ,collection_state])
    question_input.submit(fn=ask_question, inputs=[question_input, chatbot, collection_state], outputs=chatbot)


if __name__ == "__main__":
    demo.launch()
