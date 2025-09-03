import os
import time
from bilibili_api import login_v2
import qrcode
from app.config import QR_CODE_SAVE_PATH

# 确保二维码保存目录存在
os.makedirs(os.path.dirname(QR_CODE_SAVE_PATH), exist_ok=True)

class BilibiliLogin:
    def __init__(self):
        self.qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
        self.credential = None  # 登录成功后的凭证

    async def generate_qr_code(self) -> str:
        """生成二维码并返回图片路径"""
        await self.qr.generate_qrcode()
        # 获取二维码链接并生成图片
        qr_url = self.qr._QrCodeLogin__qr_link  # 注意：私有属性可能随库版本变化
        qr_image = qrcode.make(qr_url)
        qr_image.save(QR_CODE_SAVE_PATH)
        return QR_CODE_SAVE_PATH

    async def check_login_state(self) -> dict:
        """检查登录状态，返回状态信息"""
        if self.qr.has_done():
            self.credential = self.qr.get_credential()
            return {
                "status": "success",
                "cookies": self.credential.get_cookies()
            }
        else:
            state = await self.qr.check_state()
            return {"status": "pending", "message": state}