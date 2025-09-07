"""
Query Planning and Decomposition Module
"""
import json
from typing import Dict, List
from langchain.llms import OpenAI # type: ignore
from langchain.prompts import PromptTemplate # type: ignore

class QueryPlanner:
    def __init__(self):
        self.llm = OpenAI(temperature=0.3)
        
        self.planning_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
            You are a research planning AI. Given a user query, create a comprehensive research plan.
            
            Query: {query}
            
            Create a research plan with the following structure:
            1. Identify key research areas
            2. Break down into specific searchable tasks
            3. Determine what data sources to use (web, stocks, knowledge base)
            4. Plan the sequence of research steps
            
            Return a JSON structure with:
            - "main_topics": List of main research areas
            - "tasks": List of specific research tasks with type and query
            - "expected_sources": Types of sources needed
            - "sector_focus": If applicable, which business sector
            
            Make the plan comprehensive but focused. Each task should be specific and actionable.
            """
        )
    
    async def create_research_plan(self, query: str) -> Dict:
        """Create a structured research plan from the user query"""
        
        # Generate research plan using LLM
        chain = self.planning_prompt | self.llm
        plan_text = chain.invoke({"query": query})
        
        try:
            # Parse LLM response (assuming it returns JSON)
            plan = json.loads(plan_text)
        except:
            # Fallback to rule-based planning
            plan = self._fallback_planning(query)
        
        # Enhance plan with specific task details
        enhanced_plan = self._enhance_research_plan(plan, query)
        
        return enhanced_plan
    
    def _fallback_planning(self, query: str) -> Dict:
        """Fallback planning logic when LLM parsing fails"""
        
        # Detect sector/industry keywords
        sector_keywords = {
            'technology': ['tech', 'software', 'AI', 'digital', 'IT'],
            'healthcare': ['health', 'medical', 'pharma', 'biotech'],
            'finance': ['finance', 'banking', 'fintech', 'investment'],
            'energy': ['energy', 'renewable', 'solar', 'wind', 'oil']
        }
        
        detected_sector = None
        query_lower = query.lower()
        
        for sector, keywords in sector_keywords.items():
            if any(keyword.lower() in query_lower for keyword in keywords):
                detected_sector = sector
                break
        
        # Create basic research plan
        plan = {
            "main_topics": [query.split()[:3]],  # First 3 words as main topic
            "tasks": [
                {
                    "type": "web_search",
                    "query": query,
                    "description": f"General web search for: {query}"
                },
                {
                    "type": "rag_query", 
                    "query": query,
                    "description": f"Knowledge base query for: {query}"
                }
            ],
            "expected_sources": ["web", "knowledge_base"],
            "sector_focus": detected_sector
        }
        
        # Add stock analysis if sector detected
        if detected_sector:
            plan["tasks"].append({
                "type": "stock_analysis",
                "sector": detected_sector,
                "description": f"Stock analysis for {detected_sector} sector"
            })
            plan["expected_sources"].append("financial_data")
        
        return plan
    
    def _enhance_research_plan(self, plan: Dict, original_query: str) -> Dict:
        """Enhance the research plan with additional details"""
        
        # Add metadata
        plan["original_query"] = original_query
        plan["plan_created_at"] = "2024-09-07"  # Current date
        plan["estimated_duration"] = len(plan["tasks"]) * 30  # 30 seconds per task
        
        # Add priority scores to tasks
        for i, task in enumerate(plan["tasks"]):
            task["priority"] = len(plan["tasks"]) - i  # Higher number = higher priority
            task["estimated_time"] = 30  # seconds
        
        return plan