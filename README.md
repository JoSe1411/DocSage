# DocSage - A PDF Q&A Bot

A powerful AI-powered PDF question-answering application built with Streamlit, Gemini, and FAISS. Upload PDF documents and ask questions to get intelligent answers based on the document content.

## Features

- **Multi-PDF Support**: Upload and process multiple PDF documents
- **Chat Sessions**: Organize conversations by topics with persistent chat history
- **AI-Powered Q&A**: Uses Gemini's GPT models with RAG (Retrieval-Augmented Generation)
- **Vector Search**: FAISS-based semantic search for accurate document retrieval
- **Web Search Integration**: Supplement answers with web search results
- **Document Management**: Add, remove, and organize documents within chat sessions
- **Responsive UI**: Clean, modern interface built with Streamlit

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/pdf-qa-bot.git
   cd pdf-qa-bot
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   DATABASE_URL=sqlite:///./dev.db
   ```

## Usage

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Create a new chat session** using the sidebar

3. **Upload PDF documents** to your chat session

4. **Ask questions** about your documents in the chat interface

## Project Structure

```
pdf-qa-bot/
├── app.py                 # Main Streamlit application
├── cli.py                 # Command-line interface
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── .gitignore            # Git ignore rules
└── src/
    ├── database/
    │   ├── models.py      # SQLAlchemy database models
    │   └── __init__.py
    ├── services/
    │   ├── document_service.py  # Document management
    │   ├── pdf_processor.py     # PDF text extraction
    │   ├── vector_store.py      # FAISS vector operations
    │   ├── qa_service.py        # Q&A with OpenAI
    │   ├── web_search.py        # Web search integration
    │   └── __init__.py
    ├── utils/
    │   ├── config.py        # Configuration management
    │   └── __init__.py
    └── __init__.py
```

## Technologies Used

- **Streamlit**: Web application framework
- **Google AI Studio API**: Language model for Q&A
- **FAISS**: Vector similarity search
- **SQLAlchemy**: Database ORM
- **PyPDF2**: PDF text extraction
- **SQLite**: Local database storage

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Requirements

- Python 3.8+
- Google AI Studio API key
- Internet connection for web search functionality 
