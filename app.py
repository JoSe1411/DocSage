import streamlit as st
import os
import tempfile
from src.services.document_service import DocumentService
from src.database import models
from src.services.web_search import get_web_search_tool

st.set_page_config(page_title="PDF Q&A Bot", page_icon="📚", layout="wide")

# Initialize session state
if 'doc_service' not in st.session_state:
    st.session_state.doc_service = DocumentService()
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None

doc_service = st.session_state.doc_service

# Sidebar for chat management
st.sidebar.header("💬 Chat Sessions")

# Create new chat button with custom naming
if st.sidebar.button("➕ New Chat", use_container_width=True):
    # Generate a smart name based on time or context
    from datetime import datetime
    timestamp = datetime.now().strftime("%m/%d %H:%M")
    chat_name = f"Chat {timestamp}"
    
    new_chat = doc_service.create_chat_session(name=chat_name)
    st.session_state.current_chat_id = new_chat['id']
    st.rerun()

# List existing chats with improved error handling
chats = doc_service.get_chat_sessions()
if chats:
    # Create chat options with better display names
    chat_options = {}
    for chat in chats:
        doc_count = chat['document_count']
        msg_count = chat.get('message_count', 0)
        
        # Create display name with icons and info
        if doc_count == 0:
            icon = "📝"
        elif doc_count == 1:
            icon = "📄"
        else:
            icon = "📚"
            
        display_name = f"{icon} {chat['name']}"
        
        # Add document and message counts
        if doc_count > 0 or msg_count > 0:
            info_parts = []
            if doc_count > 0:
                info_parts.append(f"{doc_count} doc{'s' if doc_count != 1 else ''}")
            if msg_count > 0:
                info_parts.append(f"{msg_count} msg{'s' if msg_count != 1 else ''}")
            display_name += f" ({', '.join(info_parts)})"
        
        chat_options[display_name] = chat['id']
    
    # Set default selection with proper bounds checking
    default_index = 0
    if st.session_state.current_chat_id and chats:
        for i, chat in enumerate(chats):
            if chat['id'] == st.session_state.current_chat_id:
                default_index = i
                break
    
    # Ensure default_index is within bounds
    if default_index >= len(chat_options):
        default_index = 0
        st.session_state.current_chat_id = chats[0]['id'] if chats else None
    
    selected_chat_name = st.sidebar.selectbox(
        "Select Chat",
        list(chat_options.keys()),
        index=default_index,
        key="chat_select"
    )
    st.session_state.current_chat_id = chat_options[selected_chat_name]
    
    # Show chat preview if available
    current_chat = next((c for c in chats if c['id'] == st.session_state.current_chat_id), None)
    if current_chat and current_chat.get('preview'):
        st.sidebar.caption(f"💬 {current_chat['preview']}")
    
    # Add chat management options
    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("✏️ Rename", use_container_width=True, key="rename_chat"):
            st.session_state.show_rename_dialog = True
    
    with col2:
        if st.button("🗑️ Delete", use_container_width=True, key="delete_chat"):
            if st.session_state.current_chat_id:
                doc_service.delete_chat_session(st.session_state.current_chat_id)
                st.session_state.current_chat_id = None
                st.success("Chat deleted!")
                st.rerun()
    
    # Rename dialog
    if st.session_state.get('show_rename_dialog', False):
        current_chat = next((c for c in chats if c['id'] == st.session_state.current_chat_id), None)
        if current_chat:
            new_name = st.sidebar.text_input(
                "New chat name:",
                value=current_chat['name'],
                key="rename_input"
            )
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("✅ Save", use_container_width=True):
                    if new_name.strip():
                        doc_service.rename_chat_session(st.session_state.current_chat_id, new_name.strip())
                        st.session_state.show_rename_dialog = False
                        st.success("Chat renamed!")
                        st.rerun()
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_rename_dialog = False
                    st.rerun()
else:
    st.sidebar.info("No chats available. Create a new chat to get started.")
    st.session_state.current_chat_id = None

# Document management section
st.sidebar.header("📄 Document Management")

# Add documents section
st.sidebar.subheader("Add Documents")
uploaded_files = st.sidebar.file_uploader(
    "Upload PDF files",
    type="pdf",
    accept_multiple_files=True,
    help="Select one or more PDF files to add to your chat"
)

if uploaded_files and st.session_state.current_chat_id:
    if st.sidebar.button("📤 Add to Chat", use_container_width=True):
        with st.sidebar:
            with st.spinner("Processing PDFs..."):
                for uploaded_file in uploaded_files:
                    # Save temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    # Process PDF
                    doc = doc_service.process_pdf(
                        file_path=tmp_path,
                        original_name=uploaded_file.name,
                        file_size=uploaded_file.size
                    )
                    
                    # Add to current chat
                    doc_service.add_document_to_chat(st.session_state.current_chat_id, doc.id)
                    
                    # Clean up
                    os.unlink(tmp_path)
                    
            st.success(f"Added {len(uploaded_files)} document(s) to chat!")
            st.rerun()

# Show documents in current chat
if st.session_state.current_chat_id:
    chat_docs = doc_service.get_chat_documents(st.session_state.current_chat_id)
    
    if chat_docs:
        st.sidebar.subheader("Documents in Chat")
        for doc in chat_docs:
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                st.write(f"📄 {doc['name']}")
                st.caption(f"{doc['size']} bytes")
            with col2:
                if st.button("🗑️", key=f"remove_{doc['id']}", help="Remove from chat"):
                    doc_service.remove_document_from_chat(st.session_state.current_chat_id, doc['id'])
                    st.rerun()
    else:
        st.sidebar.info("No documents in this chat. Add some documents above.")
        
    # Additional chat controls
    st.sidebar.markdown("---")
    if st.sidebar.button("🧹 Clear History", use_container_width=True):
        doc_service.clear_chat_history(st.session_state.current_chat_id)
        st.success("Chat history cleared!")
        st.rerun()

# Main chat interface
st.header("💬 PDF Q&A Chat")

if not st.session_state.current_chat_id:
    st.info("👆 Create a new chat session to get started!")
    st.stop()

# Get current chat documents
current_docs = doc_service.get_chat_documents(st.session_state.current_chat_id)
if not current_docs:
    st.warning("📄 No documents in this chat. Add some PDFs from the sidebar to start asking questions!")
    st.stop()

# Show current context
with st.expander("📋 Current Context", expanded=False):
    st.write(f"**Documents in this chat:** {len(current_docs)}")
    for doc in current_docs:
        st.write(f"• {doc['name']} ({doc['size']} bytes)")

# Display chat history
st.subheader("Chat History")
chat_history = doc_service.get_chat_history(st.session_state.current_chat_id)

if chat_history:
    for msg in chat_history:
        st.markdown(f"**Q:** {msg['question']}")
        st.markdown(f"**A:** {msg['answer']}")
        st.markdown("---")
else:
    st.info("No messages yet. Ask a question below to get started!")

# Question input
question = st.text_input("Ask a question about your documents...", key="question_input")
if st.button("🚀 Ask", use_container_width=True) and question:
    with st.spinner("Getting answer..."):
        try:
            result = doc_service.ask_question(st.session_state.current_chat_id, question)
            
            # Display the answer immediately (this will be saved to chat history by ask_question)
            st.markdown(f"**Q:** {question}")
            st.markdown(f"**A:** {result['result']}")
            if result.get('web_result'):
                st.markdown(f"**Web Search Result:** {result['web_result']}")
            
            # Success message
            st.success("✅ Question answered and saved to chat history!")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            if "quota" in str(e).lower() or "429" in str(e):
                st.warning("⚠️ API quota exceeded. Please try again later.")
            elif "database" in str(e).lower():
                st.warning("⚠️ Database error. Please try refreshing the page.")
            else:
                st.warning("⚠️ An unexpected error occurred. Please try again.")

# Web search tool
st.sidebar.header("🌐 Web Search")
web_query = st.sidebar.text_input("Search the web", key="web_search")
if st.sidebar.button("🔍 Search", use_container_width=True) and web_query:
    with st.sidebar:
        with st.spinner("Searching..."):
            search_tool = get_web_search_tool()
            web_result = search_tool.run(web_query)
            st.write("**Result:**")
            st.write(web_result)

# Document management section
st.sidebar.header("🗂️ All Documents")
all_docs = doc_service.get_all_documents()
if all_docs:
    with st.sidebar.expander("Manage Documents", expanded=False):
        for doc in all_docs:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📄 {doc['name']}")
                st.caption(f"{doc['size']} bytes")
            with col2:
                if st.button("🗑️", key=f"delete_system_{doc['id']}", help="Delete from system"):
                    doc_service.remove_document_from_system(doc['id'])
                    st.success(f"Deleted {doc['name']}")
                    st.rerun()
else:
    st.sidebar.info("No documents in system.")
