import logging
from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.state import RAGState
from app.rag.vector_store import get_retriever

logger = logging.getLogger(__name__)

# Initialize the LLM
def get_llm(api_key: str = None):
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("A valid Gemini API Key must be provided by the user.")
        
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_LLM_MODEL,
        google_api_key=api_key,
        temperature=0
    )

# --- Define structured output models for specific nodes ---

class QueryAnalysisOutput(BaseModel):
    rewritten_query: str = Field(description="The optimized query for vector retrieval.")
    query_type: str = Field(description="One of: conceptual, how-to, troubleshooting, api-reference.")

class GraderOutput(BaseModel):
    is_relevant: str = Field(description="Whether the document is relevant to the question. Must be 'yes' or 'no'.")


# --- Nodes ---

def analyze_query(state: RAGState) -> Dict[str, Any]:
    """
    Analyzes the raw user question, rewrites it for better retrieval, 
    and classifies the query type.
    """
    logger.info("NODE: analyze_query")
    question = state["question"]
    api_key = state.get("api_key")
    llm = get_llm(api_key)
    
    prompt = f"""You are a query analysis expert for a technical documentation retrieval system.
Your task is to take a raw user question and output a rewritten query optimized for vector search (cosine similarity).
Also, classify the query type into one of: 'conceptual', 'how-to', 'troubleshooting', 'api-reference'.

Raw Question: {question}

Output your analysis based on the schema."""

    # Using with_structured_output for guaranteed formatting
    structured_llm = llm.with_structured_output(QueryAnalysisOutput)
    response = structured_llm.invoke(prompt)
    
    return {
        "rewritten_query": response.rewritten_query,
        "query_type": response.query_type
    }

def retrieve_docs(state: RAGState) -> Dict[str, Any]:
    """
    Retrieves documents from the vector store using the rewritten query.
    """
    logger.info("NODE: retrieve_docs")
    rewritten_query = state.get("rewritten_query", state["question"])
    api_key = state.get("api_key")
    
    retriever = get_retriever(api_key)
    docs = retriever.invoke(rewritten_query)
    
    logger.info(f"Retrieved {len(docs)} documents.")
    return {"retrieved_docs": docs}

def grade_documents(state: RAGState) -> Dict[str, Any]:
    """
    Grades retrieved documents for relevance to the original question.
    """
    logger.info("NODE: grade_documents")
    question = state["question"]
    docs = state.get("retrieved_docs", [])
    api_key = state.get("api_key")
    
    llm = get_llm(api_key)
    structured_llm = llm.with_structured_output(GraderOutput)
    
    graded_docs = []
    
    for doc in docs:
        prompt = f"""You are a grader evaluating the relevance of a retrieved document to a user question.
If the document contains keyword(s) or semantic meaning related to the user question, grade it as 'yes'.
Otherwise, grade it as 'no'.

User Question: {question}

Document Content: 
{doc.page_content}
"""
        try:
            res = structured_llm.invoke(prompt)
            if res.is_relevant.lower() == "yes":
                graded_docs.append(doc)
        except Exception as e:
            logger.error(f"Error grading document: {e}")
            # If grading fails, we assume it's relevant to be safe, or skip. Let's skip.
            pass
            
    logger.info(f"Grading complete. {len(graded_docs)} out of {len(docs)} documents deemed relevant.")
    return {"graded_docs": graded_docs}

def rewrite_query(state: RAGState) -> Dict[str, Any]:
    """
    Rewrites the query entirely differently because retrieval failed.
    Increments retry_count.
    """
    logger.info("NODE: rewrite_query")
    question = state["question"]
    retry_count = state.get("retry_count", 0) + 1
    api_key = state.get("api_key")
    
    llm = get_llm(api_key)
    
    prompt = f"""You are an expert at reformulating questions for technical vector search.
The previous search for the following question failed to yield relevant documents.
Think of a completely different way to formulate the search query. Focus on synonyms, broader concepts, or related terms.

Original Question: {question}

Return ONLY the rewritten query text, nothing else."""

    response = llm.invoke(prompt)
    
    query_text = response.content
    if isinstance(query_text, list):
        query_text = "\n".join(query_text)
    
    return {
        "rewritten_query": query_text.strip(),
        "retry_count": retry_count
    }

def generate_answer(state: RAGState) -> Dict[str, Any]:
    """
    Generates the final answer using the relevant documents.
    """
    logger.info("NODE: generate_answer")
    question = state["question"]
    docs = state.get("graded_docs", [])
    
    # If no docs and we somehow reached here (or hit max retries), handle gracefully
    if not docs:
        logger.info("No relevant docs found after retries. Emitting fallback answer.")
        fallback = "I don't have enough information in my knowledge base to answer this question accurately. Please try rephrasing or ask about LangChain, LangGraph, or FastAPI."
        return {
            "generation": fallback,
            "citations": [],
            "answer_found": False
        }
        
    # Prepare context string and citations
    context_parts = []
    citations = []
    
    for i, doc in enumerate(docs):
        # Build citation dict
        source = doc.metadata.get("source", "Unknown Document")
        url = doc.metadata.get("source", "Unknown URL") # Assuming source is URL for web loader
        
        preview = doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
        
        citations.append({
            "document": source,
            "url": url,
            "chunk_preview": preview
        })
        
        context_parts.append(f"--- Document {i+1} ---\nSource: {source}\nContent:\n{doc.page_content}\n")
        
    context_str = "\n".join(context_parts)
    
    api_key = state.get("api_key")
    llm = get_llm(api_key)
    prompt = f"""You are an expert technical assistant for LangGraph, LangChain, and FastAPI.
Answer the user's question clearly and accurately based ONLY on the provided context documents.
If the context does not contain the answer, say "I don't know" - do not hallucinate.
When you use information from a document, mention it naturally (e.g., "According to the LangChain documentation...").

Context Documents:
{context_str}

User Question: {question}

Answer:"""

    response = llm.invoke(prompt)
    
    # Ensure content is a string (Gemma sometimes returns a list of parts)
    generation_text = response.content
    if isinstance(generation_text, list):
        generation_text = "\n".join(generation_text)
    
    return {
        "generation": generation_text,
        "citations": citations,
        "answer_found": True
    }
