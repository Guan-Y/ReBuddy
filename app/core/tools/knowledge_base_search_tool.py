"""
Knowledge Base Search Tool for smolagents framework
Supports both summary search and full-text search
"""

from typing import Dict, Any, Optional, List
from smolagents import Tool
from smolagents.models import Model


class KnowledgeBaseSearchTool(Tool):
    """
    Knowledge base search tool that supports both summary and full-text search modes.
    
    This tool allows searching through academic papers stored in the knowledge base.
    It supports three search modes:
    - summary: Search through paper summaries for quick overview
    - detail: Search through full-text chunks for detailed information
    - hybrid: Search through both summaries and full-text chunks (default)
    """
    
    name = "knowledge_base_search"
    description = """
    Search through the academic knowledge base for papers and documents.
    Use this tool when you need to find information about research papers, methodologies, datasets, or any academic content.
    
    The tool supports three search modes:
    - summary: Best for finding papers by topic, getting overviews, and comparing approaches
    - detail: Best for finding specific details, exact quotes, methodology descriptions
    - hybrid: Combines both summary and detail search for comprehensive results
    
    Examples:
    - "Find papers about transformer architecture" (use summary mode)
    - "What is the exact accuracy reported in the paper?" (use detail mode)
    - "Compare different approaches to object detection" (use hybrid mode)
    """
    
    inputs = {
        "query": {
            "description": "The search query in natural language. Be specific and provide context for better results.",
            "type": "string",
        },
        "mode": {
            "description": "Search mode: 'summary' for paper summaries, 'detail' for full-text chunks, 'hybrid' for both (default: 'hybrid')",
            "type": "string",
            "nullable": True,
        },
        "top_k": {
            "description": "Number of results to return (default: 3, max: 10)",
            "type": "integer",
            "nullable": True,
        },
        "user_id": {
            "description": "User ID for personalized search (optional, uses default if not provided)",
            "type": "string",
            "nullable": True,
        },
        "kb_id": {
            "description": "Knowledge base ID to search within (optional, searches all knowledge bases if not provided)",
            "type": "string",
            "nullable": True,
        },
    }
    
    output_type = "string"
    
    def __init__(self, model: Model = None, max_results: int = 10):
        """
        Initialize the knowledge base search tool.
        
        Args:
            model: Optional LLM model for result summarization
            max_results: Maximum number of results to return
        """
        super().__init__()
        self.model = model
        self.max_results = max_results
        
        # Lazy import to avoid circular dependencies
        self._kb_manager = None
        self._initialized = False
    
    def _initialize(self):
        """Initialize knowledge base manager"""
        if self._initialized:
            return
        
        try:
            from app.core.kb_manager import get_kb_manager
            
            # Get default knowledge base manager
            self._kb_manager = get_kb_manager(user_id="default")
            self._initialized = True
            print("✅ KnowledgeBaseSearchTool initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize KnowledgeBaseSearchTool: {e}")
            self._kb_manager = None
            self._initialized = True
    
    def _format_search_results(self, results: Dict[str, List], query: str, mode: str) -> str:
        """
        Format search results into a readable string.
        
        Args:
            results: Search results from knowledge base
            query: Original search query
            mode: Search mode used
            
        Returns:
            Formatted string with search results
        """
        if not results or not results.get('documents') or not results['documents'][0]:
            return f"No results found for query: '{query}' in {mode} mode."
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        ids = results['ids'][0]
        
        mode_name = {
            'summary': 'Summary Search',
            'detail': 'Full-Text Search',
            'hybrid': 'Hybrid Search'
        }.get(mode, 'Search')
        
        output = f"\n{'='*80}\n"
        output += f"📚 {mode_name} Results for: '{query}'\n"
        output += f"{'='*80}\n\n"
        
        for idx, (doc, meta, doc_id) in enumerate(zip(documents, metadatas, ids), 1):
            output += f"## Result {idx}\n\n"
            
            # Add metadata
            if meta:
                if 'title' in meta:
                    output += f"**Title:** {meta['title']}\n\n"
                if 'authors' in meta:
                    output += f"**Authors:** {meta['authors']}\n\n"
                if 'year' in meta:
                    output += f"**Year:** {meta['year']}\n\n"
                if 'venue' in meta:
                    output += f"**Venue:** {meta['venue']}\n\n"
                if 'result_type' in meta:
                    output += f"**Type:** {meta['result_type']}\n\n"
                if 'chunk_index' in meta:
                    output += f"**Chunk Index:** {meta['chunk_index']}\n\n"
            
            # Add content
            output += f"**Content:**\n{doc}\n\n"
            output += f"{'─'*80}\n\n"
        
        return output
    
    def forward(self, 
                query: str, 
                mode: str = "hybrid", 
                top_k: int = 3, 
                user_id: str = None,
                kb_id: str = None) -> str:
        """
        Execute knowledge base search.
        
        Args:
            query: Search query in natural language
            mode: Search mode ('summary', 'detail', or 'hybrid')
            top_k: Number of results to return
            user_id: User ID for personalized search
            kb_id: Knowledge base ID to search within
            
        Returns:
            Formatted search results as string
        """
        # Initialize if needed
        if not self._initialized:
            self._initialize()
        
        # Validate parameters
        if not query or not query.strip():
            return "Error: Query cannot be empty. Please provide a search query."
        
        # Validate mode
        valid_modes = ['summary', 'detail', 'hybrid']
        if mode not in valid_modes:
            mode = 'hybrid'
            print(f"⚠️ Invalid mode '{mode}', using 'hybrid' instead")
        
        # Validate top_k
        if top_k is None:
            top_k = 3
        elif top_k < 1:
            top_k = 1
        elif top_k > self.max_results:
            top_k = self.max_results
            print(f"⚠️ top_k exceeds maximum {self.max_results}, using {self.max_results} instead")
        
        # Check if knowledge base manager is available
        if self._kb_manager is None:
            return "Error: Knowledge base manager not initialized. Please check the configuration."
        
        # Build filters if kb_id is provided
        filters = None
        if kb_id:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                filters = Filter(
                    must=[FieldCondition(key="kb_id", match=MatchValue(value=kb_id))]
                )
            except ImportError:
                # Fallback for ChromaDB
                filters = {"kb_id": kb_id}
        
        try:
            # Execute search
            print(f"🔍 Searching knowledge base: mode={mode}, top_k={top_k}, query='{query}'")
            results = self._kb_manager.search(
                query=query,
                mode=mode,
                top_k=top_k,
                filters=filters
            )
            
            # Format results
            formatted_results = self._format_search_results(results, query, mode)
            
            # If model is provided and results are too long, generate a summary
            if self.model and len(formatted_results) > 4000:
                from smolagents.models import MessageRole
                
                messages = [
                    {
                        "role": MessageRole.SYSTEM,
                        "content": [{
                            "type": "text",
                            "text": "You are a helpful assistant that summarizes search results from an academic knowledge base."
                        }]
                    },
                    {
                        "role": MessageRole.USER,
                        "content": [{
                            "type": "text",
                            "text": f"Here are the search results for the query '{query}':\n\n{formatted_results}\n\n"
                                   f"Please provide a concise summary of these results, highlighting the most relevant information."
                        }]
                    }
                ]
                
                summary = self.model(messages).content
                return f"\n{formatted_results}\n\n---\n\n**Summary:**\n{summary}"
            
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error during knowledge base search: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
        

if __name__ == "__main__":
    # Example usage

    def test_basic_search():
        """Test basic search functionality"""
        print("=" * 80)
        print("Test 1: Basic Search (Summary Mode)")
        print("=" * 80)
        
        search_tool = KnowledgeBaseSearchTool()
        
        results = search_tool.forward(
            query="transformer architecture",
            mode="summary",
            top_k=3
        )
        
        print(results)
        print("\n")


    def test_detail_search():
        """Test detail search functionality"""
        print("=" * 80)
        print("Test 2: Detail Search")
        print("=" * 80)
        
        search_tool = KnowledgeBaseSearchTool()
        
        results = search_tool.forward(
            query="attention mechanism",
            mode="detail",
            top_k=2
        )
        
        print(results)
        print("\n")


    def test_hybrid_search():
        """Test hybrid search functionality"""
        print("=" * 80)
        print("Test 3: Hybrid Search")
        print("=" * 80)
        
        search_tool = KnowledgeBaseSearchTool()
        
        results = search_tool.forward(
            query="machine learning",
            mode="hybrid",
            top_k=3
        )
        
        print(results)
        print("\n")


    def test_invalid_mode():
        """Test handling of invalid mode"""
        print("=" * 80)
        print("Test 4: Invalid Mode (should fallback to hybrid)")
        print("=" * 80)
        
        search_tool = KnowledgeBaseSearchTool()
        
        results = search_tool.forward(
            query="deep learning",
            mode="invalid_mode",
            top_k=2
        )
        
        print(results)
        print("\n")


    def test_empty_query():
        """Test handling of empty query"""
        print("=" * 80)
        print("Test 5: Empty Query")
        print("=" * 80)
        
        search_tool = KnowledgeBaseSearchTool()
        
        results = search_tool.forward(
            query="",
            mode="summary",
            top_k=3
        )
        
        print(results)
        print("\n")


    def test_large_top_k():
        """Test handling of large top_k value"""
        print("=" * 80)
        print("Test 6: Large top_k (should limit to max_results)")
        print("=" * 80)
        
        search_tool = KnowledgeBaseSearchTool(max_results=5)
        
        results = search_tool.forward(
            query="neural networks",
            mode="summary",
            top_k=20  # Exceeds max_results
        )
        
        print(results)
        print("\n")


    def main():
        """Run all tests"""
        print("\n" + "=" * 80)
        print("KnowledgeBaseSearchTool Test Suite")
        print("=" * 80 + "\n")
        
        tests = [
            ("Basic Search", test_basic_search),
            ("Detail Search", test_detail_search),
            ("Hybrid Search", test_hybrid_search),
            ("Invalid Mode", test_invalid_mode),
            ("Empty Query", test_empty_query),
            ("Large top_k", test_large_top_k),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                test_func()
                passed += 1
            except Exception as e:
                print(f"❌ {test_name} failed: {e}\n")
                failed += 1
        
        print("=" * 80)
        print("Test Summary")
        print("=" * 80)
        print(f"Passed: {passed}/{len(tests)}")
        print(f"Failed: {failed}/{len(tests)}")
        print("=" * 80)

    main()