# AI Research Agent - Complete Implementation
# This is a full implementation of a research agent system

import os
import sys
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict
from dataclasses import dataclass
import streamlit as st

from Research_Agent_Classes import StockDataManager, WebSearchTool, RAGSystem, LLMInterface


# ------------------- Data Classes -------------------
@dataclass
class ResearchQuery:
    query: str
    sector: str
    timestamp: datetime
    depth: str = "comprehensive"


# ------------------- Core Research Agent -------------------
class ResearchAgent:
    """Main Research Agent orchestrating all components"""

    def __init__(self):
        self.stock_manager = StockDataManager()
        self.search_tool = WebSearchTool()
        self.rag_system = RAGSystem()
        self.llm = LLMInterface()

    async def conduct_research(self, research_query: ResearchQuery) -> str:
        """Main research orchestration method"""

        # Step 1: Web Search
        search_results = await self.search_tool.search(
            f"{research_query.query} {research_query.sector}",
            max_results=5,
        )

        # Step 2: Get RAG Context
        context = self.rag_system.get_relevant_context(
            research_query.query, research_query.sector
        )

        # Step 3: Fetch Stock Data (if financial/tech/health sector)
        stock_data: Dict = {}
        if research_query.sector in ["IT", "Finance", "Healthcare"]:
            key_companies = context.get("key_companies", [])[:5]
            if key_companies:
                stock_data = await self.stock_manager.fetch_stock_data(
                    key_companies, research_query.sector
                )

        # Step 4: Generate Research Report
        research_report = await self.llm.generate_research_content(
            research_query.query,
            search_results,
            stock_data,
            context,
        )

        # Step 5: Save Report
        self.save_report(research_query, research_report)

        return research_report

    def save_report(self, query: ResearchQuery, content: str):
        """Save research report to SQLite DB and markdown file"""
        conn = sqlite3.connect(self.stock_manager.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO research_reports (query, sector, content, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                query.query,
                query.sector,
                content,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        # Save as markdown
        filename = f"research_{query.sector}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)


# ------------------- CLI ChatBot -------------------
class ChatBot:
    """Simple CLI chatbot interface"""

    def __init__(self):
        self.agent = ResearchAgent()
        self.sectors = [
            "IT",
            "Healthcare",
            "Finance",
            "Energy",
            "Retail",
            "Manufacturing",
        ]

    def display_welcome(self):
        print("\n" + "=" * 60)
        print("🤖 AI Research Agent")
        print("Advanced Research Assistant with Stock Data & RAG")
        print("=" * 60)
        print("\nAvailable sectors:", ", ".join(self.sectors))
        print("\nExample queries:")
        print("- 'AI trends in IT sector'")
        print("- 'Healthcare technology innovations'")
        print("- 'Fintech disruption in Finance'")
        print("\nType 'quit' to exit")
        print("-" * 60)

    async def process_query(self, user_input: str) -> str:
        """Process user query and determine sector"""

        detected_sector = "General"
        for sector in self.sectors:
            if sector.lower() in user_input.lower():
                detected_sector = sector
                break

        if detected_sector == "General":
            print("\n🤔 Sector not detected. Please specify:")
            for i, sector in enumerate(self.sectors, 1):
                print(f"{i}. {sector}")

            try:
                choice = input("\nEnter sector number (1-6): ").strip()
                sector_idx = int(choice) - 1
                if 0 <= sector_idx < len(self.sectors):
                    detected_sector = self.sectors[sector_idx]
            except (ValueError, IndexError):
                detected_sector = "IT"  # Default

        research_query = ResearchQuery(
            query=user_input,
            sector=detected_sector,
            timestamp=datetime.now(),
        )

        report = await self.agent.conduct_research(research_query)
        return report

    async def run(self):
        """Main chatbot loop"""
        self.display_welcome()

        while True:
            try:
                user_input = input("\n💬 Enter your research query: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Thank you for using AI Research Agent!")
                    break

                if not user_input:
                    continue

                print(f"\n🚀 Processing: {user_input}")
                report = await self.process_query(user_input)

                print("\n" + "=" * 60)
                print("📄 RESEARCH REPORT")
                print("=" * 60)
                print(report)
                print("=" * 60)

                continue_choice = (
                    input("\n❓ Continue with another query? (y/n): ")
                    .strip()
                    .lower()
                )
                if continue_choice not in ["y", "yes"]:
                    break

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again.")


# ------------------- Streamlit Web Interface -------------------
def create_streamlit_app():
    """Create Streamlit web interface"""

    st.title("🤖 AI Research Agent")
    st.markdown("### Advanced Research Assistant with Stock Data & RAG")

    agent = ResearchAgent()

    # Sidebar for configuration
    st.sidebar.header("Configuration")
    selected_sector = st.sidebar.selectbox(
        "Select Sector",
        ["Auto-detect", "IT", "Healthcare", "Finance", "Energy", "Retail", "Manufacturing"],
    )

    research_depth = st.sidebar.selectbox(
        "Research Depth", ["Quick", "Standard", "Comprehensive"]
    )

    # --- Past Reports Sidebar ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📑 Past Reports")

    try:
        conn = sqlite3.connect(agent.stock_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, query, sector, created_at FROM research_reports ORDER BY created_at DESC LIMIT 10"
        )
        past_reports = cursor.fetchall()
        conn.close()

        if past_reports:
            report_options = {
                f"{r[1]} ({r[2]}) - {r[3][:16]}": r[0] for r in past_reports
            }
            selected_report = st.sidebar.selectbox(
                "View Report", ["None"] + list(report_options.keys())
            )

            if selected_report != "None":
                report_id = report_options[selected_report]
                conn = sqlite3.connect(agent.stock_manager.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM research_reports WHERE id=?", (report_id,)
                )
                report_content = cursor.fetchone()[0]
                conn.close()

                st.markdown("## 📄 Past Research Report")
                st.markdown(report_content)
    except Exception as e:
        st.sidebar.error(f"Could not load past reports: {e}")

    # --- Main Research Input ---
    query = st.text_area(
        "Enter your research query:",
        placeholder="e.g., 'AI trends in healthcare sector'",
    )

    if st.button("🔍 Start Research", type="primary"):
        if query:
            with st.spinner("Conducting research... This may take a moment..."):
                try:
                    sector = selected_sector
                    if sector == "Auto-detect":
                        detected = "General"
                        for s in [
                            "IT",
                            "Healthcare",
                            "Finance",
                            "Energy",
                            "Retail",
                            "Manufacturing",
                        ]:
                            if s.lower() in query.lower():
                                detected = s
                                break
                        sector = detected if detected != "General" else "IT"

                    research_query = ResearchQuery(
                        query=query,
                        sector=sector,
                        timestamp=datetime.now(),
                        depth=research_depth.lower(),
                    )

                    report = asyncio.run(agent.conduct_research(research_query))

                    st.success("✅ Research completed!")
                    st.markdown("## 📄 Research Report")
                    st.markdown(report)

                except Exception as e:
                    st.error(f"❌ Error during research: {e}")
        else:
            st.warning("⚠️ Please enter a research query.")


# ------------------- Main Entry -------------------
async def main_cli():
    chatbot = ChatBot()
    await chatbot.run()


if __name__ == "__main__":
    if any("streamlit" in arg for arg in sys.argv):
        create_streamlit_app()
    else:
        asyncio.run(main_cli())
