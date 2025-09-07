"""
Core Research Agent Implementation
"""
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime, timedelta

from langchain_openai import OpenAI # type: ignore
from langchain.chains import LLMChain # type: ignore
from langchain.prompts import PromptTemplate # type: ignore
from langchain.agents import initialize_agent, Tool # type: ignore
from langchain.memory import ConversationBufferMemory # type: ignore

from tools.web_search import WebSearchTool
from tools.stock_api import StockDataTool
from tools.rag_system import RAGSystem
from agents.query_planner import QueryPlanner
from agents.report_generator import ReportGenerator

class ResearchAgent:
    def __init__(self):
        self.llm = OpenAI(temperature=0.7, max_tokens=2000)
        self.web_search = WebSearchTool()
        self.stock_tool = StockDataTool()
        self.rag_system = RAGSystem()
        self.query_planner = QueryPlanner()
        self.report_generator = ReportGenerator()
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize agent tools
        self.tools = [
            Tool(
                name="web_search",
                description="Search the web for current information",
                func=self.web_search.search
            ),
            Tool(
                name="stock_data",
                description="Get stock market data and analysis",
                func=self.stock_tool.get_stock_data
            ),
            Tool(
                name="rag_query",
                description="Query knowledge base using RAG",
                func=self.rag_system.query
            )
        ]
        
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent="conversational-react-description",
            memory=self.memory,
            verbose=True
        )
    
    async def conduct_research(self, query: str) -> Dict[str, Any]:
        """
        Main research function that orchestrates the entire research process
        """
        research_start_time = datetime.now()
        
        # Step 1: Plan the research
        research_plan = await self.query_planner.create_research_plan(query)
        
        # Step 2: Execute research tasks
        research_results = []
        sources = []
        
        for task in research_plan['tasks']:
            print(f"  ⚙️  Executing: {task['description']}")
            
            if task['type'] == 'web_search':
                web_results = await self.web_search.search_async(task['query'])
                research_results.extend(web_results)
                sources.extend([r['url'] for r in web_results])
            
            elif task['type'] == 'stock_analysis':
                stock_results = await self.stock_tool.analyze_sector_stocks(task['sector'])
                research_results.append({
                    'type': 'stock_data',
                    'data': stock_results
                })
            
            elif task['type'] == 'rag_query':
                rag_results = await self.rag_system.enhanced_query(task['query'])
                research_results.append({
                    'type': 'knowledge_base',
                    'data': rag_results
                })
        
        # Step 3: Synthesize and generate report
        report_data = {
            'original_query': query,
            'research_plan': research_plan,
            'research_results': research_results,
            'sources': list(set(sources)),
            'research_duration': (datetime.now() - research_start_time).total_seconds()
        }
        
        # Generate comprehensive markdown report
        markdown_report = await self.report_generator.generate_report(report_data)
        
        return {
            'report': markdown_report,
            'sources': sources,
            'data_points': len(research_results),
            'research_plan': research_plan
        }
    
    async def get_stock_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get detailed stock analysis"""
        return await self.stock_tool.get_detailed_analysis(ticker)
    
    def get_research_history(self) -> List[Dict]:
        """Get previous research sessions"""
        # Implementation for research history
        return []