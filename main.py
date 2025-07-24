# main.py
from bilibili_api import login_v2, sync
from flask import Flask, jsonify, render_template, send_file
import qrcode
import io
import base64
import time

app = Flask(__name__, template_folder='templates')
qr_login = None
qr_url_cache = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/qrcode')
async def get_qrcode():
    global qr_login, qr_url_cache
    qr_login = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
    qr_url = await qr_login.generate_qrcode()
    qr_url_cache = qr_url
    
    # 生成二维码图像
    qr_img = qrcode.make(qr_url)
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # 保存图片到内存中，供/qrcode-image路由使用
    app.qr_image_buffer = img_buffer
    
    # 返回base64编码
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    return jsonify({
        'qrcode': f'data:image/png;base64,{img_str}',
        'url': qr_url
    })

@app.route('/qrcode-image')
async def qrcode_image():
    global qr_login, qr_url_cache
    if not qr_login:
        qr_login = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
        qr_url = await qr_login.generate_qrcode()
        qr_url_cache = qr_url
    else:
        qr_url = qr_url_cache
    
    # 生成二维码图像
    qr_img = qrcode.make(qr_url)
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')

@app.route('/api/check_login')
async def check_login():
    global qr_login
    if qr_login:
        state = await qr_login.check_state()
        if qr_login.has_done():
            return jsonify({
                'status': 'success',
                'credential': qr_login.get_credential().get_cookies()
            })
        return jsonify({
            'status': 'waiting',
            'state': str(state)
        })
    return jsonify({'status': 'error', 'message': 'No QR code generated'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)