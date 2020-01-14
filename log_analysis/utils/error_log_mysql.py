# 错误日志逐行读取, 正则切割, 存入数据库

from dingtalkchatbot.chatbot import DingtalkChatbot

import re
from datetime import datetime

import pymysql


def Ding_Remind(msg):
    """钉钉机器人 站点报错提醒"""
    # WebHook地址
    webhook = 'https://oapi.dingtalk.com/robot/send?access_token=73943f3fe551d4f760dcf827986cd19570ec660505b02a4846c4e8567f9a6a41'

    # 初始化机器人
    ding_remind = DingtalkChatbot(webhook)

    # # Text消息@所有人
    # ding_remind.send_text(msg=msg, is_at_all=True)

    # Text消息之@指定用户
    at_mobiles = ['15651965920']  # 值班人员手机号码
    ding_remind.send_text(msg=msg, at_mobiles=at_mobiles)


log_pattern = '''([\d\/]{10} [\d\:]{8}) \[([^ ]+)]\ [^ ]+ [^ ]+ ([\S ]+), [^ ]+ ([\d.]+), [^ ]+ ([\w.]+), [^ ]+ "([^ ]+) ([\S]+) ([\S]+)", [\S ]+ "[\S]+", [\w]{8}: "([\S]+)"'''
pattern = re.compile(log_pattern)

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mysql', database='log_analysis',
                       charset='utf8')
cursor = conn.cursor()

with open('../site_log/lbcwx.yuns1.cn.error.log', 'rb') as f:
    count = 0
    url_temp = ''
    url_dict = {}
    time_temp = datetime.now()
    ding_tag = False

    try:
        select_sql = "select site_id, site_name from tb_site where error_log='lbcwx.yuns1.cn.error.log'"
        cursor.execute(select_sql)
        site_id, site_name = cursor.fetchone()
    except Exception as e:
        print(e)

    for line in f:
        content = line.decode()
        match = pattern.match(content)
        if not match:
            continue

        # for i in range(1, 10):
        #     print(match.group(i))

        date_time = datetime.strptime(match.group(1), '%Y/%m/%d %H:%M:%S')
        level = match.group(2)

        message = match.group(3)
        message = message.replace("\'", "`")

        client = match.group(4)
        server = match.group(5)
        method = match.group(6)
        url = match.group(7)
        protocol = match.group(8)
        referrer = '' if match.group(9) == '-' else match.group(9)

        try:
            params = (date_time, level, message, client, server, method, url, protocol, referrer, site_id)
            insert_sql = "insert into tb_error_log(date_time, level, message, client, server, method, url, protocol, referrer, site_id) values('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%d')" % params
            cursor.execute(insert_sql)
            conn.commit()
            # print("tb_error_log_success")
        except Exception as e:
            conn.rollback()
            print(message)
            print(e)

        log_delta = date_time - time_temp  # 错误日志时间差

        # 一分钟以内, 相同url报错次数累加
        if 0 <= log_delta.seconds <= 60 and url == url_temp:
            count += 1

            # 钉钉未预警, 报错次数大于等于10, 相同接口报错时间差小于10分钟
            if not ding_tag and count >= 10:
                if url not in url_dict.keys():
                    msg = "站点报错提醒: \n报错站点: {},\n报错时间: {},\n报错服务器: {},\n报错接口: {},\n报错信息: {}".format(site_name,
                                                                                                   date_time,
                                                                                                   server, url,
                                                                                                   message)
                    print(msg)
                    # Ding_Remind(msg)
                    try:
                        params = (site_name, date_time, server, url, message, site_id)
                        insert_sql = "insert into tb_remind(site_name, date_time, server, url, message, site_id) values('%s', '%s', '%s', '%s', '%s', '%d')" % params
                        cursor.execute(insert_sql)
                        conn.commit()
                        # print("tb_remind_success")
                    except Exception as e:
                        conn.rollback()
                        print(e)

                    url_dict[url] = date_time
                    ding_tag = True
                elif url in url_dict.keys():
                    ding_delta = date_time - url_dict[url]  # 相同接口预警时间差
                    if ding_delta.seconds > 300:
                        msg = "站点报错提醒: \n报错站点: {},\n报错时间: {},\n报错服务器: {},\n报错接口: {},\n报错信息: {}".format(
                            site_name, date_time, server, url, message)
                        print(msg)
                        # Ding_Remind(msg)

                        try:
                            params = (site_name, date_time, server, url, message, site_id)
                            insert_sql = "insert into tb_remind(site_name, date_time, server, url, message, site_id) values('%s', '%s', '%s', '%s', '%s', '%d')" % params
                            cursor.execute(insert_sql)
                            conn.commit()
                            # print("tb_remind_success")
                        except Exception as e:
                            conn.rollback()
                            print(e)

                        url_dict[url] = date_time
                        ding_tag = True
        else:
            # print("重新计数")
            time_temp = date_time
            url_temp = url
            count = 0
            ding_tag = False

conn.close()
