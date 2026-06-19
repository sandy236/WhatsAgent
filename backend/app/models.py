from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source = Column(String(50), default="file")
    doc_type = Column(String(50), default="text")
    url = Column(String(1024), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), default="New chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    messages = relationship("Message", back_populates="conversation", cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    conversation = relationship("Conversation", back_populates="messages")

class ApiEntry(Base):
    __tablename__ = "apis"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    method = Column(String(16), default="GET")
    headers = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(100), primary_key=True)
    value = Column(String(1024), nullable=False)
