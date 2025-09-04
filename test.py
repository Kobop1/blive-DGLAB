import time
from bilibili_api import login_v2, sync, live
import qrcode
import os

def format_danmaku_data(event):
    """
    格式化弹幕数据
    """
    data = event['data']
    info = data['info']
    
    # 提取用户信息
    user_info = info[2]
    username = user_info[1]  # 用户名
    uid = user_info[0] if len(user_info) > 0 else 0  # UID
    
    # 提取弹幕内容
    content = info[1]
    
    # 提取粉丝牌信息（如果存在）
    fan_medal = ""
    medal_info = {}
    if len(info) > 3 and info[3]:
        medal_info_raw = info[3]
        medal_name = medal_info_raw[1]  # 粉丝牌名称
        medal_level = medal_info_raw[0]  # 粉丝牌等级
        fan_medal = f" [{medal_name}({medal_level})]"
        medal_info = {
            "name": medal_name,
            "level": medal_level
        }
    
    # 提取用户等级
    user_level = info[4][0] if len(info) > 4 and info[4] else ""
    
    # 提取用户头衔信息（如果存在）
    title_info = ""
    if 'title' in event['data'] and event['data']['title']:
        title_info = event['data']['title']
    
    return {
        "type": "弹幕",
        "uid": uid,
        "username": username,
        "content": content,
        "fan_medal": fan_medal,
        "medal_info": medal_info,
        "user_level": user_level,
        "title_info": title_info,
        "timestamp": info[0][4] if len(info) > 0 and len(info[0]) > 4 else 0,
        "raw_data": event
    }

def format_gift_data(event):
    """
    格式化礼物数据
    """
    data = event['data']
    gift_data = data['data']
    
    # 提取送礼用户信息
    username = gift_data['uname']
    uid = gift_data['uid']  # UID
    
    # 提取礼物信息
    gift_name = gift_data['giftName']
    gift_num = gift_data['num']
    
    # 提取粉丝牌信息（如果存在）
    fan_medal = ""
    medal_info = {}
    if 'medal_info' in gift_data and gift_data['medal_info']:
        medal_info_raw = gift_data['medal_info']
        if medal_info_raw.get('medal_name'):
            medal_name = medal_info_raw['medal_name']
            medal_level = medal_info_raw['medal_level']
            fan_medal = f" [{medal_name}({medal_level})]"
            medal_info = {
                "name": medal_name,
                "level": medal_level
            }
    
    # 提取礼物价值（金瓜子）
    total_coin = gift_data['total_coin']
    
    # 提取是否首次送礼
    is_first = gift_data.get('is_first', False)
    
    # 提取连击信息
    combo_num = 0
    if 'combo_send' in gift_data and gift_data['combo_send']:
        combo_num = gift_data['combo_send'].get('combo_num', 0)
    
    return {
        "type": "礼物",
        "uid": uid,
        "username": username,
        "gift_name": gift_name,
        "gift_num": gift_num,
        "total_coin": total_coin,
        "fan_medal": fan_medal,
        "medal_info": medal_info,
        "is_first": is_first,
        "combo_num": combo_num,
        "timestamp": gift_data.get('timestamp', 0),
        "raw_data": event
    }

def print_formatted_data(formatted_data):
    """
    打印格式化后的数据
    """
    if formatted_data["type"] == "弹幕":
        print(f"[{formatted_data['type']}] [{formatted_data['uid']}] {formatted_data['username']}{formatted_data['fan_medal']}: {formatted_data['content']}")
        # 如果有额外信息，可以按需显示
        if formatted_data['title_info']:
            print(f"  └─ 头衔: {formatted_data['title_info']}")
            
    elif formatted_data["type"] == "礼物":
        print(f"[{formatted_data['type']}] [{formatted_data['uid']}] {formatted_data['username']}{formatted_data['fan_medal']} 赠送 {formatted_data['gift_name']} x{formatted_data['gift_num']} (价值: {formatted_data['total_coin']}金瓜子)")
        # 显示额外信息
        if formatted_data['is_first']:
            print(f"  └─ 首次送礼")
        if formatted_data['combo_num'] > 1:
            print(f"  └─ 连击: {formatted_data['combo_num']}")

async def main() -> None:
    # 生成二维码登录实例
    qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
    await qr.generate_qrcode()
    print(qr.get_qrcode_terminal())
    
    # 保存二维码图片到本地目录
    qr_url = qr._QrCodeLogin__qr_link  # 访问私有属性获取二维码链接
    qr_image = qrcode.make(qr_url)
    save_path = os.path.join(os.getcwd(), "bilibili_qr.png")
    qr_image.save(save_path)
    print(f"二维码已保存至: {save_path}")
    
    # 等待扫码登录完成
    while not qr.has_done():
        print(await qr.check_state())
        time.sleep(1)
    
    # 获取登录后的cookies
    cookies = qr.get_credential().get_cookies()
    print("登录成功，获取到cookies:", cookies)
    
    # 使用获取到的cookies创建直播间弹幕连接
    room = live.LiveDanmaku(1878687045, credential=qr.get_credential())
    
    # 注册弹幕事件处理函数
    @room.on('DANMU_MSG')
    async def on_danmaku(event):
        # 收到弹幕
        formatted_data = format_danmaku_data(event)
        print_formatted_data(formatted_data)
    
    # 注册礼物事件处理函数
    @room.on('SEND_GIFT')
    async def on_gift(event):
        # 收到礼物
        formatted_data = format_gift_data(event)
        print_formatted_data(formatted_data)
    
    # 连接直播间
    print("正在连接直播间...")
    await room.connect()

if __name__ == '__main__':
    sync(main())