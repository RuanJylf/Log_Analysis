# 访问日志逐行读取, 正则切割, 存入数据库

import re
import time

import pymysql

log_pattern = '''([\d\.]{7,}) - - \[([\w\:\/]+) \+[\d]+\] "([\w]+) (\/[\S]*) ([\S]+)" (\d+) (\d+) "([^"]+)" "([^"]+)"'''
pattern = re.compile(log_pattern)

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mysql', database='log_analysis',
                       charset='utf8')
cursor = conn.cursor()

with open('../site_log/lbcwx.yuns1.cn.log', 'rb') as f:
    try:
        select_sql = "select site_id from tb_site where access_log='lbcwx.yuns1.cn.log'"
        cursor.execute(select_sql)
        site_id = cursor.fetchone()[0]
    except Exception as e:
        print(e)

    for line in f:
        content = line.decode()
        match = pattern.match(content)
        if not match:
            continue

        # print(match.group())
        ip = match.group(1)
        date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(match.group(2), '%d/%b/%Y:%H:%M:%S'))
        method = match.group(3)
        url = match.group(4)
        protocol = match.group(5)
        status = int(match.group(6))
        size = round((float(match.group(7)) / 1024), 2)
        referrer = '' if match.group(8) == '-' else match.group(8)
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

conn.close()
