from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from src.services.web_search import get_web_search_tool
from langchain.agents import initialize_agent, AgentType, Tool

class QAService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1
        )
        self.qa_chain = None
        
    def setup_qa_chain(self, retriever):
        """Set up the QA chain with custom prompt"""
        prompt_template = PromptTemplate(
            template="""
            You are an AI assistant helping users with PDF document analysis. 
            
            Use the following pieces of context to answer the question at the end.
            
            IMPORTANT: 
            - If the question is about the document itself (availability, existence, file info), answer based on the fact that you have access to the document content.
            - If the question is about the content within the document, use the provided context to answer.
            - If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.
            
            Context: {context}
            
            Question: {question}
            
            Answer:""",
            input_variables=["context", "question"]
        )
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt_template}
        )
        return self.qa_chain
        
    def get_answer(self, question: str, use_web_search: bool = True) -> dict:
        """Get answer for a question based on document content, with optional web search fallback."""
        if not self.qa_chain:
            raise ValueError("QA chain not set up. Call setup_qa_chain first.")
        result = self.qa_chain({"query": question})
        answer = result.get("result", "")
        # If answer is empty or not confident, use web search as fallback
        web_result = None
        if use_web_search and (not answer or "I don't know" in answer or "not sure" in answer):
            search_tool = get_web_search_tool()
            web_result = search_tool.run(question)
            if web_result:
                answer += f"\n\n---\nWeb Search Result:\n{web_result}"
        return {"result": answer, "web_result": web_result}

    def get_agent_answer(self, question: str, retriever, documents_info=None) -> dict:
        """Use a LangChain agent with PDF retriever and web search tools for observation/action cycles."""
        # System info tool for document-level questions
        def system_info_tool_func(q):
            print(f"[DEBUG] System info tool called with query: {q}")
            if documents_info:
                if documents_info.get('count', 0) == 1:
                    info = f"Currently loaded document: {documents_info['names'][0]}\n"
                    info += f"Total file size: {documents_info.get('total_size', 'Unknown')} bytes\n"
                else:
                    info = f"Currently loaded documents ({documents_info.get('count', 0)}): {', '.join(documents_info.get('names', []))}\n"
                    info += f"Total file size: {documents_info.get('total_size', 'Unknown')} bytes\n"
                info += f"Document type: PDF\n"
                info += f"Status: Processed and indexed\n"
                return info
            return "No document information available."
        
        system_tool = Tool(
            name="SystemInfo",
            func=system_info_tool_func,
            description="Get information about the current documents and system status. Use this for questions about document availability, file info, or system status."
        )
        
        # PDF search tool
        def pdf_search_tool_func(q):
            print(f"[DEBUG] PDF search tool called with query: {q}")
            docs = retriever.get_relevant_documents(q)
            print(f"[DEBUG] Retrieved {len(docs)} documents from retriever")
            if docs:
                content = "\n".join([d.page_content for d in docs])
                print(f"[DEBUG] Retrieved content length: {len(content)}")
                print(f"[DEBUG] First 200 chars: {content[:200]}")
                return content
            else:
                print("[DEBUG] No relevant PDF content found.")
                return "No relevant PDF content found."
        
        pdf_tool = Tool(
            name="PDFSearch",
            func=pdf_search_tool_func,
            description="Search through the content of the uploaded PDF documents. Use this for questions about what's written inside the PDF documents."
        )
        
        # Web search tool
        web_tool = get_web_search_tool()
        tools = [system_tool, pdf_tool, web_tool]
        
        agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        print(f"[DEBUG] Agent initialized with {len(tools)} tools")
        answer = agent.run(question)
        return {"result": answer}
