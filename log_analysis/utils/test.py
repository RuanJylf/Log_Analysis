import os

from log_analysis.utils.common import crontab_task, read_logs

# 测试数据
error_count = 10  # 报错次数阈值 默认10次
error_time = 2  # 报错时间间隔 默认2分钟
remind_time = 10  # 提醒时间间隔 默认10分钟
read_time = 1  # 读取时间间隔 默认1分钟
crontab_time = 10  # 定时时间间隔 默认10s
# log_name = "lbcwx.yuns1.cn.log"
log_name = "lbcwx.yuns1.cn.error.log"

directory = "../site_log/"
file_list = [file for file in os.listdir(directory) if file != '.gitkeep']

print(file_list)

# # 正式数据
# error_count = 10  # 报错次数阈值 默认10次
# error_time = 2  # 报错时间间隔 默认2分钟
# remind_time = 10  # 提醒时间间隔 默认10分钟
# read_time = 5  # 读取时间间隔 默认5分钟
# crontab_time = 30  # 定时时间间隔 默认30分钟
# log_name = 'lbcwx.yuns1.cn.log'


if __name__ == '__main__':

    for log_name in file_list:
        read_logs(log_name, error_count, error_time, remind_time, read_time)

        crontab_task(crontab_time, read_logs, log_name, error_count, error_time, remind_time, read_time)
