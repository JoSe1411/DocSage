from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
import os
import uuid
from src.utils.config import Config

# Set the SQLAlchemy database URL using the DATABASE_URL environment variable.
# Example for SQLite: export DATABASE_URL="sqlite:///mydb.db"
# Example for PostgreSQL: export DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
# Defaults to SQLite file 'dev.db' if not set.

Base = declarative_base()
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///dev.db")
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Association table for many-to-many relationship between chats and documents
chat_document_association = Table(
    'chat_documents',
    Base.metadata,
    Column('chat_id', String, ForeignKey('chat_sessions.id'), primary_key=True),
    Column('document_id', String, ForeignKey('documents.id'), primary_key=True)
)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    originalName = Column(String, nullable=False)
    fileSize = Column(Integer, nullable=False)
    uploadedAt = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False)
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", secondary=chat_document_association, back_populates="documents")

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    documentId = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunkIndex = Column(Integer, nullable=False)
    embedding = Column(Text)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    document = relationship("Document", back_populates="chunks")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, default="New Chat")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    documents = relationship("Document", secondary=chat_document_association, back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="chat_session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chatId = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    chat_session = relationship("ChatSession", back_populates="messages")

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    print("[DEBUG] Database tables created successfully")
except Exception as e:
    print(f"[ERROR] Failed to create database tables: {e}")
    raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Document CRUD
def create_document(filename: str, original_name: str, file_size: int):
    db = next(get_db())
    try:
        doc = Document(filename=filename, originalName=original_name, fileSize=file_size)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create document: {e}")
        raise

def get_document(document_id: str):
    db = next(get_db())
    try:
        return db.query(Document).filter(Document.id == document_id).first()
    except Exception as e:
        print(f"[ERROR] Failed to get document: {e}")
        raise

def list_documents():
    db = next(get_db())
    try:
        return db.query(Document).all()
    except Exception as e:
        print(f"[ERROR] Failed to list documents: {e}")
        raise

def delete_document(document_id: str):
    db = next(get_db())
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            db.delete(doc)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to delete document: {e}")
        raise

# Chunk CRUD
def create_chunk(document_id: str, content: str, chunk_index: int, embedding: str):
    db = next(get_db())
    try:
        chunk = Chunk(documentId=document_id, content=content, chunkIndex=chunk_index, embedding=embedding)
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return chunk
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create chunk: {e}")
        raise

def get_chunks(document_id: str):
    db = next(get_db())
    try:
        return db.query(Chunk).filter(Chunk.documentId == document_id).order_by(Chunk.chunkIndex.asc()).all()
    except Exception as e:
        print(f"[ERROR] Failed to get chunks: {e}")
        raise

def get_chunks_for_documents(document_ids: list):
    db = next(get_db())
    try:
        return db.query(Chunk).filter(Chunk.documentId.in_(document_ids)).order_by(Chunk.documentId, Chunk.chunkIndex.asc()).all()
    except Exception as e:
        print(f"[ERROR] Failed to get chunks for documents: {e}")
        raise

# Chat Session CRUD
def create_chat_session(name: str = "New Chat"):
    db = next(get_db())
    try:
        chat = ChatSession(name=name)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create chat session: {e}")
        raise

def get_chat_session(chat_id: str):
    db = next(get_db())
    try:
        return db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    except Exception as e:
        print(f"[ERROR] Failed to get chat session: {e}")
        raise

def get_chat_document_count(chat_id: str):
    db = next(get_db())
    try:
        chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        if chat:
            return len(chat.documents)
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to get chat document count: {e}")
        raise

def list_chat_sessions():
    db = next(get_db())
    try:
        return db.query(ChatSession).order_by(ChatSession.createdAt.desc()).all()
    except Exception as e:
        print(f"[ERROR] Failed to list chat sessions: {e}")
        raise

def delete_chat_session(chat_id: str):
    db = next(get_db())
    try:
        chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        if chat:
            db.delete(chat)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to delete chat session: {e}")
        raise

def rename_chat_session(chat_id: str, new_name: str):
    db = next(get_db())
    try:
        chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        if chat:
            chat.name = new_name
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to rename chat session: {e}")
        raise

def add_document_to_chat(chat_id: str, document_id: str):
    db = next(get_db())
    try:
        chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()
        if chat and document and document not in chat.documents:
            chat.documents.append(document)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to add document to chat: {e}")
        raise

def remove_document_from_chat(chat_id: str, document_id: str):
    db = next(get_db())
    try:
        chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()
        if chat and document and document in chat.documents:
            chat.documents.remove(document)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to remove document from chat: {e}")
        raise

# Chat Message CRUD
def create_chat_message(chat_id: str, question: str, answer: str):
    db = next(get_db())
    try:
        message = ChatMessage(chatId=chat_id, question=question, answer=answer)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create chat message: {e}")
        raise

def get_chat_messages(chat_id: str):
    db = next(get_db())
    try:
        return db.query(ChatMessage).filter(ChatMessage.chatId == chat_id).order_by(ChatMessage.timestamp.asc()).all()
    except Exception as e:
        print(f"[ERROR] Failed to get chat messages: {e}")
        raise
