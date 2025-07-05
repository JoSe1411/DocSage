import os
import json
from typing import List, Dict
from src.services.pdf_processor import PDFProcessor
from src.services.vector_store import VectorStore
from src.services.qa_service import QAService
from src.database import models
from src.utils.config import Config

class DocumentService:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.vector_store = VectorStore()
        self.qa_service = QAService()

    def process_pdf(self, file_path: str, original_name: str, file_size: int) -> Dict:
        # 1. Store document metadata
        doc = models.create_document(
            filename=os.path.basename(file_path),
            original_name=original_name,
            file_size=file_size
        )
        document_id = doc.id
        # 2. Extract and chunk text
        text = self.pdf_processor.extract_text(file_path)
        chunks = self.pdf_processor.chunk_text(text)
        print(f"[DEBUG] Processed PDF: {original_name}, Chunks created: {len(chunks)}")
        # 3. Embed and store chunks
        texts = [chunk['content'] for chunk in chunks]
        vectors = self.vector_store.embeddings.embed_documents(texts)
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            models.create_chunk(
                document_id=document_id,
                content=chunk['content'],
                chunk_index=i,
                embedding=json.dumps(vector)
            )
        return doc

    def get_multi_document_retriever(self, document_ids: List[str]):
        """Create a retriever that searches across multiple documents"""
        if not document_ids:
            return None
            
        chunks = models.get_chunks_for_documents(document_ids)
        print(f"[DEBUG] Retrieved {len(chunks)} chunks from {len(document_ids)} documents")
        
        if not chunks:
            print("[DEBUG] No chunks found for the specified documents!")
            return None
        
        texts = [chunk.content for chunk in chunks]
        print(f"[DEBUG] Creating FAISS store with {len(texts)} text chunks from multiple documents")
        
        faiss_store = self.vector_store.build_langchain_faiss(texts)
        print(f"[DEBUG] Multi-document FAISS store created successfully")
        
        retriever = faiss_store.as_retriever(search_kwargs={"k": Config.SIMILARITY_TOP_K})
        return retriever

    def create_chat_session(self, name: str = "New Chat") -> Dict:
        """Create a new chat session"""
        chat = models.create_chat_session(name)
        return {"id": chat.id, "name": chat.name}

    def get_chat_sessions(self) -> List[Dict]:
        """Get all chat sessions with enhanced information"""
        sessions = models.list_chat_sessions()
        result = []
        
        for session in sessions:
            # Get document count and messages within the same session context
            document_count = models.get_chat_document_count(session.id)
            messages = models.get_chat_messages(session.id)
            first_message = messages[0] if messages else None
            
            chat_info = {
                "id": session.id,
                "name": session.name,
                "document_count": document_count,
                "created_at": session.createdAt,
                "message_count": len(messages)
            }
            
            # Add preview if available
            if first_message:
                preview = first_message.question[:50] + "..." if len(first_message.question) > 50 else first_message.question
                chat_info["preview"] = preview
            
            result.append(chat_info)
            
        return result

    def add_document_to_chat(self, chat_id: str, document_id: str):
        """Add a document to a chat session"""
        models.add_document_to_chat(chat_id, document_id)
        
        # Auto-rename chat if it's the first document and has default name
        chat = models.get_chat_session(chat_id)
        if chat and len(chat.documents) == 1 and ("New Chat" in chat.name or "Chat " in chat.name):
            document = models.get_document(document_id)
            if document:
                # Generate smart name from document
                smart_name = self._generate_smart_chat_name(document.originalName)
                models.rename_chat_session(chat_id, smart_name)

    def _generate_smart_chat_name(self, filename: str) -> str:
        """Generate a smart chat name based on document filename"""
        # Remove file extension
        name = filename.rsplit('.', 1)[0]
        
        # Clean up common patterns
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Capitalize words
        words = name.split()
        if len(words) > 3:
            # If too long, take first 3 words
            name = ' '.join(words[:3])
        
        # Ensure it's not too long
        if len(name) > 25:
            name = name[:22] + "..."
            
        return name.title()

    def remove_document_from_chat(self, chat_id: str, document_id: str):
        """Remove a document from a chat session"""
        models.remove_document_from_chat(chat_id, document_id)

    def get_chat_documents(self, chat_id: str) -> List[Dict]:
        """Get all documents in a chat session"""
        chat = models.get_chat_session(chat_id)
        if not chat:
            return []
        return [{"id": doc.id, "name": doc.originalName, "size": doc.fileSize} for doc in chat.documents]

    def ask_question(self, chat_id: str, question: str) -> Dict:
        """Ask a question using all documents in the chat as context"""
        try:
            chat = models.get_chat_session(chat_id)
            if not chat or not chat.documents:
                return {"result": "No documents found in this chat. Please add some documents first."}
            
            document_ids = [doc.id for doc in chat.documents]
            retriever = self.get_multi_document_retriever(document_ids)
            
            if retriever is None:
                return {"result": "No document content found. Please ensure documents are properly processed."}
            
            # Get document information for system context
            documents_info = {
                "names": [doc.originalName for doc in chat.documents],
                "count": len(chat.documents),
                "total_size": sum(doc.fileSize for doc in chat.documents)
            }
            
            # Handle system-level questions directly
            if self._is_system_question(question):
                if documents_info["count"] == 1:
                    system_answer = f"Yes, there is 1 PDF document in this chat: '{documents_info['names'][0]}'."
                else:
                    system_answer = f"Yes, there are {documents_info['count']} PDF documents in this chat: {', '.join(documents_info['names'])}."
                
                models.create_chat_message(chat_id, question, system_answer)
                return {"result": system_answer}
            
            # Try direct retrieval first
            try:
                print(f"[DEBUG] Trying direct retrieval for question: {question}")
                docs = retriever.get_relevant_documents(question)
                print(f"[DEBUG] Direct retrieval found {len(docs)} documents")
                
                if docs:
                    context = "\n".join([doc.page_content for doc in docs])
                    print(f"[DEBUG] Context length: {len(context)}")
                    
                    # Use QA chain for direct answer
                    self.qa_service.setup_qa_chain(retriever)
                    direct_result = self.qa_service.get_answer(question, use_web_search=False)
                    print(f"[DEBUG] Direct QA result: {direct_result['result'][:200]}...")
                    
                    # If direct method gives a good answer, use it
                    if direct_result['result'] and "I don't know" not in direct_result['result']:
                        models.create_chat_message(chat_id, question, direct_result['result'])
                        return direct_result
            except Exception as e:
                print(f"[DEBUG] Direct retrieval failed: {e}")
            
            # Use agent-based answer for observation/action
            result = self.qa_service.get_agent_answer(question, retriever, documents_info)
            models.create_chat_message(chat_id, question, result['result'])
            return result
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return {"result": "Sorry, I encountered an error while processing your question. Please try again."}

    def get_chat_history(self, chat_id: str) -> List[Dict]:
        """Get chat message history"""
        messages = models.get_chat_messages(chat_id)
        return [{"question": msg.question, "answer": msg.answer, "timestamp": msg.timestamp} for msg in messages]

    def clear_chat_history(self, chat_id: str):
        """Clear all messages in a chat session"""
        db = next(models.get_db())
        try:
            db.query(models.ChatMessage).filter(models.ChatMessage.chatId == chat_id).delete()
            db.commit()
        finally:
            db.close()

    def delete_chat_session(self, chat_id: str):
        """Delete a chat session"""
        models.delete_chat_session(chat_id)
        
    def rename_chat_session(self, chat_id: str, new_name: str):
        """Rename a chat session"""
        models.rename_chat_session(chat_id, new_name)

    def get_all_documents(self) -> List[Dict]:
        """Get all documents in the system"""
        documents = models.list_documents()
        return [{"id": doc.id, "name": doc.originalName, "size": doc.fileSize, "uploaded": doc.uploadedAt} for doc in documents]

    def remove_document_from_system(self, document_id: str):
        """Remove a document from the entire system"""
        models.delete_document(document_id)

    def _is_system_question(self, question: str) -> bool:
        """Check if the question is about the system/document availability rather than content"""
        system_keywords = [
            "any pdf", "pdf available", "documents available", "files available",
            "what pdf", "which pdf", "pdf loaded", "document loaded",
            "file info", "document info", "system status", "how many documents",
            "what documents", "which documents"
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in system_keywords) 