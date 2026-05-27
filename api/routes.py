import os
import shutil
from typing import AsyncIterator, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sse_starlette.sse import EventSourceResponse
from rag.document_loader import DocumentLoader
from rag.rag_service import RAGService
from api.schemas import (
    AuditLogResponse, ChatRequest, ChatResponse, LoginRequest,
    RAGQueryRequest, RAGQueryResponse, RegisterRequest, AuthResponse,
    UploadResponse, UserInfo,
)
from agent.memory_agent import MemoryAgent
from auth import create_access_token, get_current_user, hash_password, require_auth, verify_password
from db import create_user, get_user_by_username, log_audit, query_audit_logs, init_db
from config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

_agent: MemoryAgent | None = None
_loader: DocumentLoader | None = None
_rag: RAGService | None = None

def get_agent() -> MemoryAgent:
    global _agent
    if _agent is None:
        _agent = MemoryAgent()
    return _agent

def get_loader() -> DocumentLoader:
    global _loader
    if _loader is None:
        _loader = DocumentLoader()
    return _loader

def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag

ALLOWED_EXT = {".txt", ".md", ".markdown", ".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}

# ==================== Auth ====================

@router.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    hashed = hash_password(req.password)
    user_id = create_user(req.username, hashed)
    token = create_access_token(user_id, req.username)
    log_audit(user_id=str(user_id), action="register", endpoint="/auth/register", request_summary=req.username)
    return AuthResponse(access_token=token, user_id=user_id, username=req.username)

@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user["id"], user["username"])
    log_audit(user_id=str(user["id"]), action="login", endpoint="/auth/login", request_summary=req.username)
    return AuthResponse(access_token=token, user_id=user["id"], username=user["username"])

@router.get("/auth/me", response_model=UserInfo)
async def me(user: dict = Depends(require_auth)):
    return UserInfo(id=user["id"], username=user["username"], created_at=user["created_at"], is_active=bool(user["is_active"]))

# ==================== Audit ====================

@router.get("/audit/logs")
async def audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(require_auth),
):
    logs = query_audit_logs(user_id=user_id, action=action, limit=limit, offset=offset)
    return {"logs": logs, "total": len(logs)}

# ==================== Chat ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else req.user_id
    try:
        agent = get_agent()
        reply = agent.chat(uid, req.message, req.session_id)
        log_audit(
            user_id=uid, action="chat", endpoint="/chat",
            request_summary=req.message[:200], response_summary=reply[:200],
            ip_address=request.client.host if request.client else "",
        )
        return ChatResponse(reply=reply, session_id=req.session_id)
    except Exception as e:
        logger.error("/chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else req.user_id
    agent = get_agent()
    async def gen():
        for chunk in agent.chat_stream(uid, req.message, req.session_id):
            yield {"event": "token", "data": chunk}
        yield {"event": "done", "data": ""}
    return EventSourceResponse(gen())

# ==================== RAG ====================

@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(req: RAGQueryRequest, request: Request, user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else req.user_id
    try:
        rag = get_rag()
        result = await rag.aquery(question=req.query, user_id=uid, top_k=req.top_k, use_hyde=req.use_hyde)
        log_audit(
            user_id=uid, action="rag_query", endpoint="/rag/query",
            request_summary=req.query[:200], response_summary=result.get("answer", "")[:200],
            ip_address=request.client.host if request.client else "",
        )
        return RAGQueryResponse(**result)
    except Exception as e:
        logger.error("/rag/query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/query/stream")
async def rag_query_stream(req: RAGQueryRequest, user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else req.user_id
    rag = get_rag()
    async def gen():
        async for ev in rag.aquery_stream(question=req.query, user_id=uid, top_k=req.top_k, use_hyde=req.use_hyde):
            yield ev
        yield {"event": "done", "data": ""}
    return EventSourceResponse(gen())

# ==================== 文档管理 ====================

@router.post("/knowledge/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile, user_id: str = "default_user", user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else user_id
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {ext}")
    dest = os.path.join(str(settings.resolved_upload_dir), file.filename)
    try:
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    loader = get_loader()
    result = loader.load_file(dest, user_id=uid)
    if not result["success"]:
        if os.path.exists(dest):
            os.remove(dest)
        raise HTTPException(status_code=500, detail=result.get("error", "加载失败"))
    log_audit(user_id=uid, action="upload", endpoint="/knowledge/upload", request_summary=file.filename)
    return UploadResponse(success=True, filename=result.get("filename", file.filename), chunks=result.get("chunks", 0))

@router.post("/knowledge/upload/multiple")
async def upload_multiple(files: list[UploadFile], user_id: str = "default_user", user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else user_id
    loader = get_loader()
    results = []
    for file in files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXT:
            results.append(UploadResponse(success=False, filename=file.filename or "", error=f"不支持: {ext}"))
            continue
        dest = os.path.join(str(settings.resolved_upload_dir), file.filename)
        try:
            with open(dest, "wb") as f:
                shutil.copyfileobj(file.file, f)
            r = loader.load_file(dest, user_id=uid)
            results.append(UploadResponse(success=r["success"], filename=r.get("filename", file.filename), chunks=r.get("chunks", 0), error=r.get("error")))
        except Exception as e:
            results.append(UploadResponse(success=False, filename=file.filename or "", error=str(e)))
    return {"results": results}

@router.get("/knowledge/list")
async def list_documents(user_id: str = "default_user", user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else user_id
    return {"files": get_loader().list_files(user_id=uid)}

@router.get("/knowledge/search")
async def search_knowledge(query: str, k: int = 5, user_id: Optional[str] = None, user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else user_id
    return {"results": get_loader().search(query, k=k, user_id=uid)}

@router.delete("/knowledge/delete/{filename}")
async def delete_document(filename: str, user_id: str = "default_user", user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else user_id
    if not get_loader().delete_file(filename, user_id=uid):
        raise HTTPException(status_code=404, detail="文件不存在")
    log_audit(user_id=uid, action="delete", endpoint=f"/knowledge/delete/{filename}", request_summary=filename)
    return {"success": True, "message": f"已删除: {filename}"}

@router.delete("/knowledge/clean")
async def clean_documents(user_id: str = "default_user", user: Optional[dict] = Depends(get_current_user)):
    uid = str(user["id"]) if user else user_id
    count = get_loader().delete_all(user_id=uid)
    log_audit(user_id=uid, action="clean", endpoint="/knowledge/clean")
    return {"success": True, "message": f"已删除 {count} chunks"}

@router.get("/health")
async def health():
    return {"status": "ok"}