"""General tools — search knowledge base."""

from agents import function_tool


@function_tool
def search_knowledge_base(query: str) -> str:
    """Search the TechCorp knowledge base for product information and FAQ answers."""
    # Simulated KB search
    kb = {
        "api": "CloudSync API: REST API available on Business and Enterprise plans. Docs at docs.techcorp.com/api.",
        "mobile": "Mobile App: Available for iOS and Android. Download from App Store or Google Play. Requires Pro plan or above.",
        "integrations": "Integrations: Slack, Google Drive, Dropbox, Microsoft Teams. Business plan includes unlimited integrations.",
        "storage": "Storage Limits: Pro=100GB, Business=1TB, Enterprise=Unlimited.",
        "sla": "SLA: Enterprise plan includes 99.9% uptime guarantee with dedicated support.",
    }
    results = []
    query_lower = query.lower()
    for key, value in kb.items():
        if key in query_lower or any(word in query_lower for word in key.split()):
            results.append(value)
    if not results:
        return f"No knowledge base articles found for '{query}'. Try different keywords."
    return "\n\n".join(results)
