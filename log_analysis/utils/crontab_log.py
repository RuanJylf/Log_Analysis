import os
import re
import time
from datetime import datetime

import pymysql
import schedule as schedule

log_pattern = '''([\d\/]{10} [\d\:]{8}) \[([^ ]+)]\ [^ ]+ [^ ]+ ([\S ]+), [^ ]+ ([\d.]+), [^ ]+ ([\w.]+), [^ ]+ "([^ ]+) ([\S]+) ([\S]+)", [\S ]+ "[\S]+", [\w]{8}: "([\S]+)"'''
pattern = re.compile(log_pattern)

start_point = 0

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mysql', database='log_analysis',
                       charset='utf8')
cursor = conn.cursor()


# error_count: 报错次数阈值 默认 5次
# error_time: 报错时间间隔 1分钟
# remind_time: 提醒时间间隔 10分钟
# crontab_time: 定时时间间隔 30分钟
# read_time: 读取时间间隔 3分钟


def read_logs():
    with open('../site_log/lbcwx.yuns1.cn.error.log', 'rb') as f:  # 一定要用'rb'因为seek 是以bytes来计算的

        try:
            select_sql = "select host from tb_site where error_log='lbcwx.yuns1.cn.error.log'"
            cursor.execute(select_sql)
            host = cursor.fetchone()[0]
        except Exception as e:
            print(e)

        result = os.system("ping {}".format(host))

        if result:
            print("服务器不通")
        else:
            global start_point  # 使用全局变量，让start_point 时刻保持在已经输出过的那个字节位
            print("开始位置: {}".format(start_point))
            time.sleep(1)
            end_point = f.seek(0, 2)  # 获得文件末尾位置
            f.seek(0, 0)  # 返回文件初始位置
            print("末尾位置: {}".format(end_point))

            if start_point == end_point:
                print("当前日志文件读取结束!")

            f.seek(start_point, 1)  # 移动文件读取指针到指定位置
            time1 = datetime.now()
            for line in f:
                content = line.decode()
                match = pattern.match(content)
                if not match:
                    continue
                print(match.group())
                time2 = datetime.now()

                delta = time2 - time1
                start_point = f.tell()

                if delta.seconds > 3:
                    print("当前位置: {}".format(start_point))
                    break
                # 若读取时间小于等于2s
                else:
                    # 若当前位置和末尾位置相同, 则表示日志文件读取结束, 记录当前位置, 跳出循环
                    if start_point == end_point:
                        print("当前日志文件读取结束!")
                        break
                    # 若当前位置和末尾位置不同, 则表示日志文件还未读完, 继续循环
                    else:
                        continue


# schedule.every(5).minutes.do(read_logs)
schedule.every(5).seconds.do(read_logs)

while True:
    # 保持schedule一直运行，然后去查询上面的任务
    schedule.run_pending()
