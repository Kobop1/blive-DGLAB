from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.utils.bilibili_login import BilibiliLogin

router = APIRouter(prefix="/login", tags=["登录"])
templates = Jinja2Templates(directory="app/templates")

# 全局登录实例
login_instance = BilibiliLogin()

@router.get("/")
async def login_page(request: Request):
    """返回登录页面，同时生成二维码"""
    qr_path = await login_instance.generate_qr_code()
    # 传递二维码相对路径给模板（前端能访问到）
    return templates.TemplateResponse("login.html", {
        "request": request,
        "qr_image_path": qr_path # 对应static目录下的路径
    })

@router.get("/check")
async def check_login():
    """检查登录状态的接口（供前端轮询）"""
    return await login_instance.check_login_state()