from bilibili_api import Geetest, GeetestType, login_v2, sync


async def main() -> None:
    choice = input("pwd / sms:")
    if not choice in ["pwd", "sms"]:
        return

    gee = Geetest()                                                         # 实例化极验测试类
    await gee.generate_test()                                               # 生成测试
    gee.start_geetest_server()                                              # 在本地部署网页端测试服务
    print(gee.get_geetest_server_url())                                     # 获取本地服务链接
    while not gee.has_done():                                               # 如果测试未完成
        pass                                                                # 就等待
    gee.close_geetest_server()                                              # 关闭部署的网页端测试服务
    print("result:", gee.get_result())

    # 1. 密码登录
    if choice == "pwd":
        username = input("username:")                                       # 手机号/邮箱
        password = input("password:")                                       # 密码
        cred = await login_v2.login_with_password(
            username=username, password=password, geetest=gee               # 调用接口登陆
        )

    # 2. 验证码登录
    if choice == "sms":
        phone = login_v2.PhoneNumber(input("phone:"), "+86")                # 实例化手机号类
        captcha_id = await login_v2.send_sms(phonenumber=phone, geetest=gee)# 发送验证码
        print("captcha_id:", captcha_id)                                    # 顺便获得对应的 captcha_id
        code = input("code: ")
        cred = await login_v2.login_with_sms(
            phonenumber=phone, code=code, captcha_id=captcha_id             # 调用接口登陆
        )

    # 安全验证
    if isinstance(cred, login_v2.LoginCheck):
        # 如法炮制 Geetest
        gee = Geetest()                                                     # 实例化极验测试类
        await gee.generate_test(type_=GeetestType.VERIFY)                   # 生成测试 (注意 type_ 为 GeetestType.VERIFY)
        gee.start_geetest_server()                                          # 在本地部署网页端测试服务
        print(gee.get_geetest_server_url())                                 # 获取本地服务链接
        while not gee.has_done():                                           # 如果测试未完成
            pass                                                            # 就等待
        gee.close_geetest_server()                                          # 关闭部署的网页端测试服务
        print("result:", gee.get_result())
        await cred.send_sms(gee)                                            # 发送验证码
        code = input("code:")
        cred = await cred.complete_check(code)                              # 调用接口登陆

    print("cookies:", cred.get_cookies())                                   # 获得 cookies

if __name__ == "__main__":
    sync(main())