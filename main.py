from bilibili_api import login_v2, sync
import time
import asyncio
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import json
import os

# 全局变量用于共享状态
qr = None
qrcode_data = "生成中..."
login_done = False
login_result = {}


# ========== 1. Web 服务处理 ==========
class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global qrcode_data, login_done, login_result

        if self.path == '/':
            # 返回 HTML 页面
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("qrcode.html", "rb") as f:
                self.wfile.write(f.read())

        elif self.path == '/qrcode':
            # 返回二维码文本
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(qrcode_data.encode())

        elif self.path == '/status':
            # 返回登录状态
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if login_done:
                response = {"status": "success", "cookies": login_result.get("cookies")}
            else:
                response = {"status": "pending", "message": "等待扫码..."}
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_error(404, "Not Found")


def run_http_server():
    server_address = ('', 5050)
    httpd = HTTPServer(server_address, WebHandler)
    print("🌐 HTTP 服务运行在 http://localhost:5050")
    httpd.serve_forever()


# ========== 2. 生成二维码并监听状态 ==========
async def generate_qr_and_wait():
    global qr, qrcode_data, login_done, login_result

    try:
        qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
        await qr.generate_qrcode()
        qrcode_data = qr.get_qrcode_terminal()

        while not qr.has_done():
            state = await qr.check_state()
            print(state)
            time.sleep(1)

        login_done = True
        login_result = {
            "cookies": qr.get_credential().get_cookies()
        }
        print("✅ 登录成功，Cookies:", login_result["cookies"])

    except Exception as e:
        print("❌ 发生错误:", str(e))
        qrcode_data = "二维码生成失败，请检查网络或重试"


# ========== 3. 主程序入口 ==========
def main():
    # 启动 Web 服务线程
    server_thread = threading.Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()

    # 异步执行二维码生成和等待
    asyncio.run(generate_qr_and_wait())


if __name__ == '__main__':
    main()