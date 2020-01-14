# 放一些常用的工具类
import functools
import os
import re
import time
from datetime import datetime

import pymysql
import schedule
from dingtalkchatbot.chatbot import DingtalkChatbot
from flask import session, current_app, g

# 访问日志正则
access_log_pattern = '''([\d\.]{7,}) - - \[([\w\:\/]+) \+[\d]+\] "([\w]+) (\/[\S]*) ([\S]+)" (\d+) (\d+) "([^"]+)" "([^"]+)"'''
access_pattern = re.compile(access_log_pattern)

# 错误日志正则
error_log_pattern = '''([\d\/]{10} [\d\:]{8}) \[([^ ]+)]\ [^ ]+ [^ ]+ ([\S ]+), [^ ]+ ([\d.]+), [^ ]+ ([\w.]+), [^ ]+ "([^ ]+) ([\S]+) ([\S]+)", [\S ]+ "[\S]+", [\w]{8}: "([\S]+)"'''
error_pattern = re.compile(error_log_pattern)

# pymysql 连接数据库
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mysql', database='log_analysis',
                       charset='utf8')
cursor = conn.cursor()


def crontab_task(crontab_time, task_name, *args):
    """定时任务"""

    # 测试
    schedule.every(crontab_time).seconds.do(task_name, *args)
    # 正式
    # schedule.every(crontab_time).minutes.do(task_name)

    while True:
        # 保持schedule一直运行，然后去查询上面的任务
        schedule.run_pending()


# 初始化读取日志文件初始位置
start_point = 0

# # 日志文件路径
directory = 'F:/Office/Project/Gitee/Log_Analysis/log_analysis/site_log/'


# directory = "../site_log/"
# file_list = [file for file in os.listdir(directory) if file != '.gitkeep']


# 连续读取日志文件
def read_logs(log_name, error_count, error_time, remind_time, read_time):
    """连续读取日志文件, 每次读取一定时长"""

    with open(directory + log_name, 'rb') as f:  # 一定要用'rb'因为seek 是以bytes来计算的

        site_id, site_name, host = get_site_data(log_name)

        result = ping_link(host)
        if result:
            # result=1, 服务器不通

            # 钉钉站点报错提醒
            msg = "站点报错提醒: \n服务器: {} \n服务器连接异常, 请及时处理! ".format(host)
            print(msg)
            # ding_remind(msg)
        else:
            # result=0, 服务器连通
            if 'error' in log_name:
                # 实时读取错误日志
                read_error_log(f, site_id, site_name, error_count, error_time, remind_time, read_time)
            else:
                # 实时读取访问日志
                read_access_log(f, site_id, read_time)


def read_access_log(f, site_id, read_time):
    """实时读取访问日志文件"""

    global start_point  # 使用全局变量，让 start_point 时刻保持在已经输出过的那个字节位
    print("开始位置: {}".format(start_point))
    end_point = f.seek(0, 2)  # 获得文件末尾位置
    f.seek(0, 0)  # 返回文件初始位置
    print("末尾位置: {}".format(end_point))

    if start_point == end_point:
        print("当前日志文件读取结束!")

    f.seek(start_point, 1)  # 移动文件读取指针到指定位置
    time1 = datetime.now()  # 读取日志开始时间

    # 遍历日志文件
    for line in f:
        content = line.decode()
        match = access_pattern.match(content)
        if not match:
            continue

        # 访问日志数据存储数据库
        access_to_mysql(match, site_id)

        time2 = datetime.now()  # 读取日志结束时间
        delta = time2 - time1  # 读取日志时间间隔

        start_point = f.tell()  # 日志文件读取的当前位置

        if delta.seconds > read_time:
            # 若读取时间大于指定读取时间间隔, 停止读取
            print("当前位置: {}".format(start_point))
            break
        else:
            # 若读取时间小于或等于读取时间间隔, 继续读取
            # 若当前位置和末尾位置相同, 则表示日志文件读取结束, 记录当前位置, 跳出循环
            if start_point == end_point:
                print("当前日志文件读取结束!")
                break
            # 若当前位置和末尾位置不同, 则表示日志文件还未读完, 继续循环读取
            else:
                continue


def read_error_log(f, site_id, site_name, error_count, error_time, remind_time, read_time):
    """实时读取错误日志文件"""

    count = 0
    url_temp = ''
    url_dict = {}
    time_temp = datetime.now()
    ding_tag = False

    global start_point  # 使用全局变量，让 start_point 时刻保持在已经输出过的那个字节位
    print("开始位置: {}".format(start_point))
    end_point = f.seek(0, 2)  # 获得文件末尾位置
    f.seek(0, 0)  # 返回文件初始位置
    print("末尾位置: {}".format(end_point))

    if start_point == end_point:
        print("当前日志文件读取结束!")

    f.seek(start_point, 1)  # 移动文件读取指针到指定位置
    time1 = datetime.now()  # 读取日志开始时间

    # 遍历日志文件
    for line in f:
        content = line.decode()
        match = error_pattern.match(content)
        if not match:
            continue

        time2 = datetime.now()  # 读取日志结束时间

        date_time = datetime.strptime(match.group(1), '%Y/%m/%d %H:%M:%S')
        message = match.group(3)
        message = message.replace("\'", "`")
        server = match.group(5)
        url = match.group(7)

        error_to_mysql(match, site_id)

        log_delta = date_time - time_temp  # 错误日志时间差

        if 0 <= log_delta.seconds <= 60 * error_time and url == url_temp:
            # 错误日志时间差内, 相同url报错次数累加
            count += 1

            # 钉钉未预警, 报错次数大于等于报错次数阈值
            if not ding_tag and count >= error_count:
                if url not in url_dict.keys():
                    msg = "站点报错提醒: \n报错站点: {},\n报错时间: {},\n报错服务器: {},\n报错接口: {},\n报错信息: {}".format(
                        site_name, date_time, server, url, message)
                    print(msg)
                    # 钉钉站点报错提醒
                    # ding_remind(msg)

                    # 站点提醒数据存储数据库
                    params = (site_name, date_time, server, url, message, site_id)
                    remind_to_mysql(params)
                    url_dict[url] = date_time
                    ding_tag = True
                elif url in url_dict.keys():
                    ding_delta = date_time - url_dict[url]  # 相同接口预警时间差
                    if ding_delta.seconds > 60 * remind_time:
                        msg = "站点报错提醒: \n报错站点: {},\n报错时间: {},\n报错服务器: {},\n报错接口: {},\n报错信息: {}".format(
                            site_name, date_time, server, url, message)
                        print(msg)
                        # 钉钉站点报错提醒
                        # ding_remind(msg)

                        # 站点提醒数据存储数据库
                        params = (site_name, date_time, server, url, message, site_id)
                        remind_to_mysql(params)
                        url_dict[url] = date_time
                        ding_tag = True

        else:
            # print("重新计数")
            time_temp = date_time
            url_temp = url
            count = 0
            ding_tag = False

        delta = time2 - time1  # 读取日志时间间隔
        start_point = f.tell()  # 日志文件读取的当前位置

        if delta.seconds > read_time:
            # 若读取时间大于指定读取时间间隔, 停止读取
            print("当前位置: {}".format(start_point))
            break
        else:
            # 若读取时间小于或等于读取时间间隔, 继续读取
            # 若当前位置和末尾位置相同, 则表示日志文件读取结束, 记录当前位置, 跳出循环
            if start_point == end_point:
                print("当前日志文件读取结束!")
                break
            # 若当前位置和末尾位置不同, 则表示日志文件还未读完, 继续循环读取
            else:
                continue


def access_to_mysql(match, site_id):
    """访问日志数据存储数据库"""

    ip = match.group(1)
    date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(match.group(2), '%d/%b/%Y:%H:%M:%S'))  # 日期时间统一化
    method = match.group(3)
    url = match.group(4)
    protocol = match.group(5)
    status = int(match.group(6))
    size = round((float(match.group(7)) / 1024), 2)  # 字节单位b转换为kb
    referrer = '' if match.group(8) == '-' else match.group(8)  # 来源页面为空判断存储方式
    useragent = match.group(9)

    try:
        params = (ip, date_time, method, url, protocol, status, size, referrer, useragent, site_id)
        insert_sql = "insert into tb_access_log(ip, date_time, method, url, protocol, status, size, referrer, useragent, site_id) values('%s', '%s', '%s', '%s', '%s', '%d', '%f', '%s', '%s', '%d')" % params
        cursor.execute(insert_sql)
        conn.commit()
        # print("tb_access_log_success")
    except Exception as e:
        conn.rollback()
        print(e)


def error_to_mysql(match, site_id):
    """错误日志数据存储数据库"""

    date_time = datetime.strptime(match.group(1), '%Y/%m/%d %H:%M:%S')  # 日期时间统一化
    level = match.group(2)
    message = match.group(3)
    message = message.replace("\'", "`")  # 防止错误信息字符串与mysql语句冲突, 将"'"转换为"`"
    client = match.group(4)
    server = match.group(5)
    method = match.group(6)
    url = match.group(7)
    protocol = match.group(8)
    referrer = '' if match.group(9) == '-' else match.group(9)  # 来源页面为空判断存储方式

    try:
        params = (date_time, level, message, client, server, method, url, protocol, referrer, site_id)
        insert_sql = "insert into tb_error_log(date_time, level, message, client, server, method, url, protocol, referrer, site_id) values('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%d')" % params
        cursor.execute(insert_sql)
        conn.commit()
        # print("tb_error_log_success")
    except Exception as e:
        conn.rollback()
        # print(message)
        print(e)


def remind_to_mysql(params):
    """站点提醒数据存储数据库"""

    try:
        insert_sql = "insert into tb_remind(site_name, date_time, server, url, message, site_id) values('%s', '%s', '%s', '%s', '%s', '%d')" % params
        cursor.execute(insert_sql)
        conn.commit()
        # print("tb_remind_success")
    except Exception as e:
        conn.rollback()
        print(e)


def get_site_data(log_name):
    """根据日志文件名称, 从数据库获取对应站点链接"""

    site_id, site_name, host = None, None, None
    if 'error' in log_name:
        # 错误日志
        try:
            select_sql = "select site_id, site_name, host from tb_site where error_log='%s'" % log_name
            print(select_sql)
            cursor.execute(select_sql)
            site_id, site_name, host = cursor.fetchone()
        except Exception as e:
            print(e)
    else:
        # 访问日志
        try:
            select_sql = "select site_id, site_name, host from tb_site where access_log='%s'" % log_name
            print(select_sql)
            cursor.execute(select_sql)
            site_id, site_name, host = cursor.fetchone()
        except Exception as e:
            print(e)

    return site_id, site_name, host


def ping_link(link):
    """读取日志文件前, ping服务器判断是否连通, 返回结果"""

    result = os.system("ping {}".format(link))

    return result


def ding_remind(msg):
    """钉钉机器人 站点报错提醒"""

    # WebHook地址
    webhook = 'https://oapi.dingtalk.com/robot/send?access_token=73943f3fe551d4f760dcf827986cd19570ec660505b02a4846c4e8567f9a6a41'

    # 初始化机器人
    ding_robot = DingtalkChatbot(webhook)

    # # Text消息之@所有人
    # ding_robot.send_text(msg=msg, is_at_all=True)

    # Text消息之@指定用户
    at_mobiles = ['15651965920']  # 值班人员手机号码
    ding_robot.send_text(msg=msg, at_mobiles=at_mobiles)


def user_login(f):
    """用户是否登陆校验"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id", None)
        # 必须指定，不指定获取不到user
        user = None
        if user_id:
            try:
                from log_analysis.models import User
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
        g.user = user
        return f(*args, **kwargs)

    return wrapper
