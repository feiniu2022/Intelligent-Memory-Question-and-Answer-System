from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserInfo(BaseModel):
    id: int
    username: str
    created_at: str
    is_active: bool


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="查询问题")
    user_id: str = Field(default="default_user", description="用户标识")
    top_k: int = Field(default=5, ge=1, le=20, description="检索文档数量")
    use_hyde: bool = Field(default=True, description="是否使用 HyDE")


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    query: str
    hyde_query: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    filename: str = ""
    chunks: int = 0
    error: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    user_id: str
    action: str
    endpoint: str
    request_summary: str
    response_summary: str
    ip_address: str
    created_at: str