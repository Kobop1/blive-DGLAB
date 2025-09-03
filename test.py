
import time
from bilibili_api import login_v2, sync
import qrcode
import os

async def main() -> None:
    qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
    await qr.generate_qrcode()
    print(qr.get_qrcode_terminal())
    
    # 保存二维码图片到本地目录
    qr_url = qr._QrCodeLogin__qr_link  # 访问私有属性获取二维码链接
    qr_image = qrcode.make(qr_url)
    save_path = os.path.join(os.getcwd(), "bilibili_qr.png")
    qr_image.save(save_path)
    print(f"二维码已保存至: {save_path}")
    
    while not qr.has_done():
        print(await qr.check_state())
        time.sleep(1)
    print(qr.get_credential().get_cookies())

if __name__ == '__main__':
    sync(main())