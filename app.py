import asyncio
import json
from collections import defaultdict, deque
from datetime import datetime
import threading
from bilibili_api import live, sync, login_v2, Credential
from bilibili_api.live import LiveDanmaku
import qrcode
from io import BytesIO
import base64
from flask import Flask, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS

# 存储实时数据的全局变量
recent_danmakus = deque(maxlen=100)  # 最近100条弹幕
recent_gifts = deque(maxlen=100)     # 最近100个礼物
user_stats = defaultdict(lambda: {
    "danmaku_count": 0,
    "gift_count": 0,
    "total_coin": 0,
    "last_seen": None
})
gift_stats = defaultdict(int)  # 礼物统计
danmaku_stats = defaultdict(int)  # 弹幕词频统计
hourly_data = defaultdict(lambda: {
    "danmaku_count": 0,
    "gift_count": 0,
    "total_coin": 0
})

# Flask应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中应该使用安全的密钥
CORS(app)

# 全局变量存储直播间监控实例和登录相关
monitor = None
monitor_thread = None
qr_login = None

class LiveRoomMonitor:
    def __init__(self, room_id: int, credential=None):
        self.room_id = room_id
        self.credential = credential
        self.room = LiveDanmaku(room_id, credential=credential)
        self.setup_handlers()

    def setup_handlers(self):
        @self.room.on('DANMU_MSG')
        async def on_danmaku(event):
            data = event['data']
            info = data['info']
            
            username = info[2][1]
            content = info[1]
            uid = info[2][0]
            timestamp = info[0][4]/1000  # 转换为秒
            
            # 更新全局数据
            danmaku_entry = {
                "username": username,
                "content": content,
                "uid": uid,
                "timestamp": timestamp,
                "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            }
            
            recent_danmakus.append(danmaku_entry)
            
            # 更新用户统计
            user_stats[username]["danmaku_count"] += 1
            user_stats[username]["last_seen"] = timestamp
            
            # 更新词频统计（简单处理，按空格分割）
            for word in content.split():
                if len(word) > 1:  # 过滤单字符
                    danmaku_stats[word] += 1
            
            # 更新小时数据
            hour_key = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H")
            hourly_data[hour_key]["danmaku_count"] += 1

        @self.room.on('SEND_GIFT')
        async def on_gift(event):
            data = event['data']
            gift_data = data['data']
            
            username = gift_data['uname']
            gift_name = gift_data['giftName']
            gift_num = gift_data['num']
            uid = gift_data['uid']
            total_coin = gift_data['total_coin']
            timestamp = gift_data['timestamp']
            
            # 更新全局数据
            gift_entry = {
                "username": username,
                "gift_name": gift_name,
                "gift_num": gift_num,
                "total_coin": total_coin,
                "uid": uid,
                "timestamp": timestamp,
                "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            }
            
            recent_gifts.append(gift_entry)
            
            # 更新用户统计
            user_stats[username]["gift_count"] += gift_num
            user_stats[username]["total_coin"] += total_coin
            user_stats[username]["last_seen"] = timestamp
            
            # 更新礼物统计
            gift_stats[gift_name] += gift_num
            
            # 更新小时数据
            hour_key = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H")
            hourly_data[hour_key]["gift_count"] += 1
            hourly_data[hour_key]["total_coin"] += total_coin

    async def start(self):
        print(f"正在连接直播间 {self.room_id}...")
        await self.room.connect()

def get_dashboard_data():
    """获取仪表盘需要的所有数据"""
    # 用户排行榜 (按发送礼物价值排序)
    top_users = sorted(
        user_stats.items(), 
        key=lambda x: x[1]['total_coin'], 
        reverse=True
    )[:20]
    
    # 礼物排行榜
    top_gifts = sorted(
        gift_stats.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:20]
    
    # 弹幕热词
    top_words = sorted(
        danmaku_stats.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:30]
    
    # 小时数据用于折线图
    hours = sorted(hourly_data.keys())[-24:]  # 最近24小时
    chart_data = {
        "hours": hours,
        "danmaku_counts": [hourly_data[h]["danmaku_count"] for h in hours],
        "gift_counts": [hourly_data[h]["gift_count"] for h in hours],
        "coin_values": [hourly_data[h]["total_coin"] for h in hours]
    }
    
    return {
        "recent_danmakus": list(recent_danmakus),
        "recent_gifts": list(recent_gifts),
        "top_users": [{"username": u[0], **u[1]} for u in top_users],
        "top_gifts": [{"gift_name": g[0], "count": g[1]} for g in top_gifts],
        "top_words": [{"word": w[0], "count": w[1]} for w in top_words],
        "chart_data": chart_data,
        "total_stats": {
            "danmaku_count": len(recent_danmakus),
            "gift_count": len(recent_gifts),
            "user_count": len(user_stats),
            "total_coin": sum(u["total_coin"] for u in user_stats.values())
        }
    }

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/login/generate')
def generate_qr():
    global qr_login
    try:
        qr_login = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
        sync(qr_login.generate_qrcode())
        qr_url = qr_login._QrCodeLogin__qr_link
        
        # 生成二维码图片
        qr_image = qrcode.make(qr_url)
        buffered = BytesIO()
        qr_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({"status": "success", "qrcode": img_str})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/login/check')
def check_login():
    global qr_login
    if qr_login is None:
        return jsonify({"status": "error", "message": "未生成二维码"})
    
    try:
        # 检查登录状态
        state = sync(qr_login.check_state())
        
        # 使用 has_done() 方法检查是否完成登录
        if qr_login.has_done():
            # 登录成功，保存凭证到session
            credential = qr_login.get_credential()
            session['credential'] = {
                'sessdata': credential.sessdata,
                'bili_jct': credential.bili_jct,
                'buvid3': credential.buvid3,
                'dedeuserid': credential.dedeuserid
            }
            return jsonify({"status": "success"})
        else:
            # 仍在等待扫码
            return jsonify({"status": "waiting", "state": str(state)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/data')
def get_data():
    """获取实时数据"""
    data = get_dashboard_data()
    return jsonify(data)

@app.route('/api/start/<int:room_id>')
def start_monitor(room_id):
    """启动监控"""
    global monitor, monitor_thread
    
    if monitor is not None:
        return jsonify({"status": "already_running"})
    
    try:
        # 获取登录凭证（如果有的话）
        credential_data = session.get('credential')
        credential = None
        if credential_data:
            credential = Credential(
                sessdata=credential_data['sessdata'],
                bili_jct=credential_data['bili_jct'],
                buvid3=credential_data['buvid3'],
                dedeuserid=credential_data['dedeuserid']
            )
        
        monitor = LiveRoomMonitor(room_id, credential=credential)
        # 在单独的线程中运行异步任务
        monitor_thread = threading.Thread(
            target=lambda: sync(monitor.start()),
            daemon=True
        )
        monitor_thread.start()
        return jsonify({"status": "started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')