"""FastAPI 服务入口"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routes import router
from config import settings
from db import init_db
from utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("启动服务，初始化数据库...")
    init_db()
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="智能记忆问答 Agent",
    description="RAG + 长期记忆 + 知识库 + 用户认证 + 审计日志",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host=settings.host, port=settings.port, reload=False)