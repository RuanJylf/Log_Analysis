# 数据库模型类

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from log_analysis import db


class User(db.Model):
    """用户"""
    __tablename__ = "tb_user"

    user_id = db.Column(db.Integer, primary_key=True)  # 用户ID
    user_name = db.Column(db.String(32), unique=True, nullable=False)  # 用户名称
    password_hash = db.Column(db.String(128), nullable=False)  # 加密密码
    is_admin = db.Column(db.Boolean, default=False)  # 是否管理
    phone = db.Column(db.String(32), nullable=True, default='')  # 手机号码
    email = db.Column(db.String(32), nullable=True, default='')  # 邮箱地址
    last_login = db.Column(db.DateTime, default=datetime.now)  # 最后一次登录时间

    @property
    def password(self):
        raise AttributeError("当前属性不可读")

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_passowrd(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        resp_dict = {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "is_admin": self.is_admin,
            "phone": self.phone,
            "email": self.email,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return resp_dict


class Site(db.Model):
    """站点"""
    __tablename__ = "tb_site"

    site_id = db.Column(db.Integer, primary_key=True)  # 站点ID
    site_name = db.Column(db.String(32), unique=True, nullable=False)  # 站点名称
    host = db.Column(db.String(32), nullable=False)  # 主机域名
    access_log = db.Column(db.String(32), nullable=True)  # 访问日志
    error_log = db.Column(db.String(32), nullable=True)  # 错误日志
    link = db.Column(db.String(256), nullable=True)  # 链接网址

    def to_dict(self):
        resp_dict = {
            "site_id": self.site_id,
            "site_name": self.site_name,
            "host": self.host,
            "access_log": self.access_log,
            "error_log": self.error_log,
            "link": self.link,
        }
        return resp_dict


class AccessLog(db.Model):
    """访问日志"""
    __tablename__ = "tb_access_log"

    log_id = db.Column(db.Integer, primary_key=True)  # 日志ID
    ip = db.Column(db.String(32), nullable=False)  # ip地址
    date_time = db.Column(db.DateTime, nullable=False)  # 访问时间
    method = db.Column(db.String(32), nullable=False)  # 访问方法
    url = db.Column(db.String(256), nullable=False)  # 访问接口
    protocol = db.Column(db.String(32), nullable=False)  # 请求协议
    status = db.Column(db.Integer, nullable=False)  # 状态码
    size = db.Column(db.Float, nullable=True)  # 流量
    referrer = db.Column(db.String(256), nullable=True)  # 来源页面
    useragent = db.Column(db.String(512), nullable=False)  # 设备信息

    tb_site = db.relationship("Site", backref='tb_access_log')  # 关联 tb_site 表
    site_id = db.Column(db.Integer, db.ForeignKey("tb_site.site_id"))  # 日志所属站点ID

    def to_dict(self):
        resp_dict = {
            "log_id": self.log_id,
            "ip": self.ip,
            "date_time": self.date_time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": self.method,
            "url": self.url,
            "protocol": self.protocol,
            "status": self.status,
            "size": self.size,
            "referrer": self.referrer,
            "useragent": self.useragent,
            "site_id": self.site_id,
        }
        return resp_dict


class ErrorLog(db.Model):
    """错误日志"""
    __tablename__ = "tb_error_log"

    log_id = db.Column(db.Integer, primary_key=True)  # 日志ID
    date_time = db.Column(db.DateTime, nullable=False)  # 错误时间
    level = db.Column(db.String(32), nullable=False)  # 错误级别
    message = db.Column(db.String(512), nullable=True)  # 错误提示信息
    client = db.Column(db.String(32), nullable=False)  # 客户端地址
    server = db.Column(db.String(32), nullable=False)  # 服务器域名
    method = db.Column(db.String(32), nullable=False)  # 请求方法
    url = db.Column(db.String(256), nullable=False)  # 请求接口
    protocol = db.Column(db.String(32), nullable=False)  # 请求协议
    referrer = db.Column(db.String(256), nullable=True)  # 来源页面

    tb_site = db.relationship("Site", backref='tb_error_log')  # 关联 tb_site 表
    site_id = db.Column(db.Integer, db.ForeignKey("tb_site.site_id"))  # 日志所属站点ID

    def to_dict(self):
        resp_dict = {
            "log_id": self.log_id,
            "date_time": self.date_time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": self.level,
            "message": self.message,
            "client": self.client,
            "server": self.server,
            "method": self.method,
            "url": self.url,
            "protocol": self.protocol,
            "referrer": self.referrer,
            "site_id": self.site_id,
        }
        return resp_dict


class Remind(db.Model):
    """日志提醒"""
    __tablename__ = "tb_remind"

    remind_id = db.Column(db.Integer, primary_key=True)  # 提醒ID
    site_name = db.Column(db.String(32), nullable=False)  # 报错站点
    date_time = db.Column(db.DateTime, nullable=False)  # 报错时间
    server = db.Column(db.String(32), nullable=False)  # 报错服务器
    url = db.Column(db.String(256), nullable=False)  # 报错接口
    message = db.Column(db.String(512), nullable=True)  # 报错信息
    state = db.Column(db.Boolean, default=False)  # 处理状态 0:待处理, 1:已处理

    tb_site = db.relationship("Site", backref='tb_remind')  # 关联 tb_site 表
    site_id = db.Column(db.Integer, db.ForeignKey("tb_site.site_id"))  # 提醒所属站点ID

    def to_dict(self):
        resp_dict = {
            "remind_id": self.remind_id,
            "site_name": self.site_name,
            "date_time": self.date_time.strftime("%Y-%m-%d %H:%M:%S"),
            "server": self.server,
            "url": self.url,
            "message": self.message,
            "state": self.state,
        }
        return resp_dict
