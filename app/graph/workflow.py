from langgraph.graph import StateGraph, END
from app.graph.state import RAGState
from app.graph.nodes import analyze_query, retrieve_docs, grade_documents, rewrite_query, generate_answer
from app.graph.edges import route_after_grading

def create_workflow() -> StateGraph:
    """
    Assembles the nodes and edges into the final RAG StateGraph.
    """
    workflow = StateGraph(RAGState)

    # 1. Add Nodes
    workflow.add_node("analyze_query", analyze_query)
    workflow.add_node("retrieve_docs", retrieve_docs)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_answer", generate_answer)

    # 2. Add Edges (Linear flow)
    # Start -> Analyze -> Retrieve -> Grade
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve_docs")
    workflow.add_edge("retrieve_docs", "grade_documents")

    # 3. Add Conditional Edges (Routing logic after grading)
    workflow.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "fallback_answer": "generate_answer"   # exhausted retries → generate_answer (handles empty docs gracefully)
        }
    )

    # 4. Add Retry Loop Edge
    # If we route to rewrite_query, we must go back to retrieve_docs after
    workflow.add_edge("rewrite_query", "retrieve_docs")

    # 5. Finish
    workflow.add_edge("generate_answer", END)

    # Compile the graph
    app = workflow.compile()
    return app

# Expose a compiled instance for easy importing
graph_app = create_workflow()
