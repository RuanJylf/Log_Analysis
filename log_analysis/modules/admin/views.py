import os
import re

from flask import render_template, session, request, url_for, redirect, current_app, g, jsonify

from log_analysis import user_login, db
from log_analysis.models import User, AccessLog, ErrorLog, Site, Remind
from log_analysis.utils.response_code import RET
from . import admin_blu
from ...utils.common import read_logs, crontab_task


@admin_blu.route("/", methods=["GET", "POST"])
def admin():
    """
    默认首页登录页
    """
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        if not all([password, username]):
            return render_template("admin/login.html", errmsg="请输入完整信息!")

        try:
            user = User.query.filter(User.user_name == username).first()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/login.html", errmsg="数据库查询错误!")

        if not user:
            return render_template("admin/login.html", errmsg="用户不存在!")

        if not user.check_passowrd(password):
            return render_template("admin/login.html", errmsg="密码错误!")

        session["user_id"] = user.user_id
        session["user_name"] = user.user_name
        session["is_admin"] = user.is_admin

        return redirect(url_for("admin.index"))
    else:
        return render_template("admin/login.html")


@admin_blu.route("/login", methods=["GET", "POST"])
def login():
    """
    用户登录页面显示以及登录:
    get:
    1.如果用户已经登陆，直接跳转到后台首页
    post:
    1.接收参数用户名称和密码
    2.通过用户名称找到密码，校验密码是否正确，以及参数的完整性
    3.校验通过后需要保存用户登陆状态
    4.并且跳转到后台首页
    """
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        if not all([password, username]):
            return render_template("admin/login.html", errmsg="请输入完整信息!")

        try:
            user = User.query.filter(User.user_name == username).first()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/login.html", errmsg="数据库查询错误!")

        if not user:
            return render_template("admin/login.html", errmsg="用户不存在!")

        if not user.check_passowrd(password):
            return render_template("admin/login.html", errmsg="密码错误!")

        session["user_id"] = user.user_id
        session["user_name"] = user.user_name
        session["is_admin"] = user.is_admin

        return redirect(url_for("admin.index"))

    user_id = session.get("user_id", None)
    is_admin = session.get("is_admin", False)
    if user_id and is_admin:
        return redirect(url_for("admin.index"))
    else:
        return render_template("admin/login.html")


@admin_blu.route("/index", methods=["GET", "POST"])
@user_login
def index():
    """
    用户登录后显示首页
    """
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        if not all([password, username]):
            return render_template("admin/login.html", errmsg="请输入完整信息!")

        try:
            user = User.query.filter(User.user_name == username).first()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/login.html", errmsg="数据库查询错误!")

        if not user:
            return render_template("admin/login.html", errmsg="用户不存在!")

        if not user.check_passowrd(password):
            return render_template("admin/login.html", errmsg="密码错误!")

        session["user_id"] = user.user_id
        session["user_name"] = user.user_name
        session["is_admin"] = user.is_admin

        return redirect(url_for("admin.index"))

    else:
        user = g.user
        if user:
            return render_template("admin/index.html", user=user.to_dict())
        else:
            return render_template("admin/login.html")


@admin_blu.route("/logout", methods=["GET", "POST"])
def logout():
    """
    退出登陆
    """
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("is_admin", None)

    return redirect(url_for("admin.login"))


@admin_blu.route("/user_edit", methods=["GET", "POST"])
def user_edit():
    """
    用户编辑
    """
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user_list = []
    current_page = 1
    total_page = 1

    filters = []
    if keywords:
        filters.append(User.user_name.contains(keywords))

    try:
        paginate = User.query.filter(*filters) \
            .order_by(User.user_id.asc()) \
            .paginate(page, 20, False)

        user_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_list = []
    for user in user_list:
        user_dict_list.append(user.to_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "user_list": user_dict_list
               }
    return render_template("admin/user_edit.html", data=context)


@admin_blu.route("/user_add", methods=["GET", "POST"])
def user_add():
    """
    用户添加
    """
    if request.method == "POST":

        is_admin = session.get("is_admin", False)
        if is_admin:
            data = request.form
            user_name = data.get("user_name")
            password = data.get("password")
            is_admin = data.get("is_admin")
            phone = data.get("phone")
            email = data.get("email")

            if not all([user_name, password, phone, email]):
                return jsonify(errno=RET.PARAMERR, errmsg="参数不全!")

            # 初始化站点模型，并设置相关数据
            user = User()
            user.user_name = user_name
            user.password = password

            if is_admin == '1':
                user.is_admin = True
            else:
                user.is_admin = False

            if re.match(r'^1(3\d|4[4-9]|5[0-35-9]|6[67]|7[013-8]|8[0-9]|9[0-9])\d{8}$', phone):
                user.phone = phone
            else:
                return jsonify(errno=RET.PARAMERR, errmsg="手机号码有误!")

            if re.match(r'^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$', email):
                user.email = email
            else:
                return jsonify(errno=RET.PARAMERR, errmsg="邮箱地址有误!")

            # 保存到数据库
            try:
                db.session.add(user)
                db.session.commit()
            except Exception as e:
                current_app.logger.error(e)
                db.session.rollback()
                return jsonify(errno=RET.DBERR, errmsg="保存数据失败!")
            return jsonify(errno=RET.OK, errmsg="添加成功！")
        else:
            return jsonify(errno=RET.ROLEERR, errmsg="用户权限不足!")
    else:
        return render_template("admin/user_add.html")


@admin_blu.route("/user_modify", methods=["GET", "POST"])
def user_modify():
    """
    用户修改
    """
    if request.method == "GET":
        user_id = request.args.get("user_id")
        if not user_id:
            return render_template('admin/user_edit.html', data={"errmsg": "未查询到此用户!"})
        # 通过id查询用户数据
        user = None
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)

        if not user:
            return render_template('admin/user_edit.html', data={"errmsg": "未查询到用户数据!"})
        data = {"user": user.to_dict()}
        return render_template('admin/user_modify.html', data=data)

    is_admin = session.get("is_admin", False)
    if is_admin:
        data = request.form
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        password = data.get("password")
        is_admin = data.get("is_admin")
        phone = data.get("phone")
        email = data.get("email")

        # 判断数据是否有值
        if not all([user_id, user_name]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数不全!")

        user = None
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
        if not user:
            return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据!")

        # 设置相关数据
        user.user_name = user_name

        if password:
            user.password = password

        if is_admin == '1':
            user.is_admin = True
        else:
            user.is_admin = False

        if phone and re.match(r'^1(3\d|4[4-9]|5[0-35-9]|6[67]|7[013-8]|8[0-9]|9[0-9])\d{8}$', phone):
            user.phone = phone
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="手机号码有误!")

        if email and re.match(r'^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$', email):
            user.email = email
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="邮箱地址有误!")

        # 保存到数据库
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="保存数据失败!")
        return jsonify(errno=RET.OK, errmsg="修改成功!")
    else:
        return jsonify(errno=RET.ROLEERR, errmsg="用户权限不足!")


@admin_blu.route("/user_delete", methods=["GET", "POST"])
def user_delete():
    """
    用户删除
    """
    # 获取查询字符串参数
    if request.method == "GET":
        user_id = request.args.get("user_id")
        if not user_id:
            return render_template('admin/user_edit.html', data={"errmsg": "未查询到此用户!"})
        # 通过id查询反馈内容
        user = None
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)

        if not user:
            return render_template('admin/user_edit.html', data={"errmsg": "未查询到用户数据!"})
        data = {"user": user.to_dict()}
        return render_template('admin/user_detele.html', data=data)

    is_admin = session.get("is_admin", False)
    if is_admin:
        data = request.form
        user_id = data.get("user_id")

        # 判断数据是否有值
        if not user_id:
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误!")

        user = None
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
        if not user:
            return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据!")

        try:
            db.session.delete(user)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="删除数据失败!")
        return jsonify(errno=RET.OK, errmsg="删除成功!")
    else:
        return jsonify(errno=RET.ROLEERR, errmsg="用户权限不足!")


@admin_blu.route("/user_calendar", methods=["GET", "POST"])
def user_calendar():
    """
    用户值班日历
    """
    return render_template("calendar/selectable.html")


@admin_blu.route("/log_overview", methods=["GET", "POST"])
def log_overview():
    """
    日志概览
    """
    keywords = request.args.get("keywords", "lbcwx.yuns1.cn.log")

    error_site, access_site = None, None
    if "error" in keywords:
        try:
            error_site = Site.query.filter(Site.error_log == keywords)
        except Exception as e:
            current_app.logger.error(e)
        if error_site:
            return render_template("admin/error_log_overview.html")
        else:
            return jsonify(errno=RET.NODATA, errmsg="未查询到日志数据!")
    else:
        try:
            access_site = Site.query.filter(Site.access_log == keywords)
        except Exception as e:
            current_app.logger.error(e)
        if access_site:
            return render_template("admin/access_log_overview.html")
        else:
            return jsonify(errno=RET.NODATA, errmsg="未查询到日志数据!")


@admin_blu.route("/log_details", methods=["GET", "POST"])
def log_details():
    """
    日志详情
    """
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")
    log_type = request.args.get("log_type", "access")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    log_list = []
    current_page = 1
    total_page = 1

    if log_type == "access":
        site_name = "lbcwx.yuns1.cn.log"
        filters = []
        if keywords:
            filters.append(AccessLog.url.contains(keywords))

        try:
            paginate = AccessLog.query.filter(*filters) \
                .order_by(AccessLog.log_id.asc()) \
                .paginate(page, 15, False)

            log_list = paginate.items
            current_page = paginate.page
            total_page = paginate.pages
        except Exception as e:
            current_app.logger.error(e)
    else:
        site_name = "lbcwx.yuns1.cn.error.log"
        filters = []
        if keywords:
            filters.append(ErrorLog.url.contains(keywords))

        try:
            paginate = ErrorLog.query.filter(*filters) \
                .order_by(ErrorLog.log_id.asc()) \
                .paginate(page, 15, False)

            log_list = paginate.items
            current_page = paginate.page
            total_page = paginate.pages
        except Exception as e:
            current_app.logger.error(e)

    log_dict_list = []
    for log in log_list:
        log_dict_list.append(log.to_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "log_list": log_dict_list,
               "site_name": site_name,
               "log_type": log_type
               }
    return render_template("admin/log_details.html", data=context)


@admin_blu.route("/site_edit", methods=["GET", "POST"])
def site_edit():
    """
    站点编辑
    """
    # 获取查询字符串参数
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    # 分页显示站点列表数据
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    site_list = []
    current_page = 1
    total_page = 1

    filters = []
    if keywords:
        filters.append(Site.site_name.contains(keywords))

    try:
        paginate = Site.query.filter(*filters) \
            .order_by(Site.site_id.asc()) \
            .paginate(page, 10, False)

        site_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    site_dict_list = []
    for site in site_list:
        site_dict_list.append(site.to_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "site_list": site_dict_list
               }
    return render_template('admin/site_edit.html', data=context)


@admin_blu.route("/site_add", methods=["GET", "POST"])
def site_add():
    """
    站点添加
    """
    if request.method == "POST":

        data = request.form
        site_name = data.get("site_name")
        host = data.get("host")
        access_log = data.get("access_log")
        error_log = data.get("error_log")
        link = data.get("link")

        if not [site_name, host, link]:
            return jsonify(errno=RET.PARAMERR, errmsg="参数不全!")

        # 初始化站点模型，并设置相关数据
        site = Site()
        site.site_name = site_name
        site.host = host
        site.access_log = access_log
        site.error_log = error_log

        # 正则匹配链接网址
        if re.match(
                r"(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)|([a-zA-Z]+.\w+\.+[a-zA-Z0-9\/_]+)",
                link):
            site.link = link
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="链接网址有误!")

        # 保存到数据库
        try:
            db.session.add(site)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="保存数据失败!")
        return jsonify(errno=RET.OK, errmsg="添加成功！")
    else:
        return render_template("admin/site_add.html")


@admin_blu.route('/site_modify', methods=["GET", "POST"])
def site_modify():
    """
    站点修改
    """
    if request.method == "GET":
        site_id = request.args.get("site_id")
        if not site_id:
            return render_template('admin/site_edit.html', data={"errmsg": "未查询到此站点!"})
        # 通过id查询站点数据
        site = None
        try:
            site = Site.query.get(site_id)
        except Exception as e:
            current_app.logger.error(e)

        if not site:
            return render_template('admin/site_edit.html', data={"errmsg": "未查询到站点数据!"})
        data = {"site": site.to_dict()}
        return render_template('admin/site_modify.html', data=data)

    data = request.form
    site_id = data.get("site_id")
    site_name = data.get("site_name")
    host = data.get("host")
    access_log = data.get("access_log")
    error_log = data.get("error_log")
    link = data.get("link")

    # 判断数据是否有值
    if not all([site_id, site_name, host, link]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全!")

    site = None
    try:
        site = Site.query.get(site_id)
    except Exception as e:
        current_app.logger.error(e)
    if not site:
        return jsonify(errno=RET.NODATA, errmsg="未查询到站点数据!")

    # 设置相关数据
    site.site_name = site_name
    site.host = host
    site.access_log = access_log
    site.error_log = error_log

    # 正则匹配链接网址
    if re.match(
            r"(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)|([a-zA-Z]+.\w+\.+[a-zA-Z0-9\/_]+)",
            link):
        site.link = link
    else:
        return jsonify(errno=RET.PARAMERR, errmsg="链接网址有误!")

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败!")
    return jsonify(errno=RET.OK, errmsg="修改成功!")


@admin_blu.route("/site_delete", methods=["GET", "POST"])
def site_delete():
    """
    站点删除
    """
    # 获取查询字符串参数
    if request.method == "GET":
        site_id = request.args.get("site_id")
        if not site_id:
            return render_template('admin/site_edit.html', data={"errmsg": "未查询到此站点!"})
        # 通过id查询新站点数据
        site = None
        try:
            site = Site.query.get(site_id)
        except Exception as e:
            current_app.logger.error(e)

        if not site:
            return render_template('admin/site_edit.html', data={"errmsg": "未查询到站点数据!"})
        data = {"site": site.to_dict()}
        return render_template('admin/site_delete.html', data=data)

    data = request.form
    site_id = data.get("site_id")

    # 判断数据是否有值
    if not site_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误!")

    site = None
    try:
        site = Site.query.get(site_id)
    except Exception as e:
        current_app.logger.error(e)
    if not site:
        return jsonify(errno=RET.NODATA, errmsg="未查询到站点数据!")

    try:
        db.session.delete(site)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="删除数据失败!")
    return jsonify(errno=RET.OK, errmsg="删除成功!")


@admin_blu.route("/site_remind", methods=["GET", "POST"])
def site_remind():
    """
    站点提醒
    """
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    remind_list = []
    current_page = 1
    total_page = 1

    filters = []
    if keywords:
        filters.append(Remind.site_name.contains(keywords))

    try:
        paginate = Remind.query.filter(*filters) \
            .order_by(Remind.remind_id.asc()) \
            .paginate(page, 10, False)

        remind_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    remind_dict_list = []
    for remind in remind_list:
        remind_dict_list.append(remind.to_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "remind_list": remind_dict_list
               }
    return render_template("admin/site_remind.html", data=context)


@admin_blu.route("/remind_modify", methods=["GET", "POST"])
def remind_modify():
    """
    修改状态
    """
    if request.method == "GET":
        remind_id = request.args.get("remind_id")
        if not remind_id:
            return render_template('admin/site_remind.html', data={"errmsg": "未查询到此提醒!"})
        # 通过id查询提醒数据
        remind = None
        try:
            remind = Remind.query.get(remind_id)
        except Exception as e:
            current_app.logger.error(e)

        if not remind:
            return render_template('admin/site_remind.html', data={"errmsg": "未查询到提醒数据!"})
        data = {"remind": remind.to_dict()}
        return render_template('admin/remind_modify.html', data=data)

    data = request.form
    remind_id = data.get("remind_id")
    site_name = data.get("site_name")
    date_time = data.get("date_time")
    server = data.get("server")
    url = data.get("url")
    message = data.get("message")
    state = data.get("state")

    # 判断数据是否有值
    if not all([remind_id, site_name, date_time, server, url, message]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全!")

    remind = None
    try:
        remind = Remind.query.get(remind_id)
    except Exception as e:
        current_app.logger.error(e)
    if not remind:
        return jsonify(errno=RET.NODATA, errmsg="未查询到提醒数据!")

    # 设置相关数据
    remind.site_name = site_name
    remind.date_time = date_time
    remind.server = server
    remind.url = url
    remind.message = message
    if state == '1':
        remind.state = True
    else:
        remind.state = False

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败!")
    return jsonify(errno=RET.OK, errmsg="修改成功!")


@admin_blu.route("/remind_delete", methods=["GET", "POST"])
def remind_delete():
    """
    用户删除
    """
    # 获取查询字符串参数
    if request.method == "GET":
        remind_id = request.args.get("remind_id")
        if not remind_id:
            return render_template('admin/site_remind.html', data={"errmsg": "未查询到此提醒!"})
        # 通过id查询提醒内容
        remind = None
        try:
            remind = Remind.query.get(remind_id)
        except Exception as e:
            current_app.logger.error(e)

        if not remind:
            return render_template('admin/site_remind.html', data={"errmsg": "未查询到提醒数据!"})
        data = {"remind": remind.to_dict()}
        return render_template('admin/remind_delete.html', data=data)

    data = request.form
    remind_id = data.get("remind_id")

    # 判断数据是否有值
    if not remind_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误!")

    remind = None
    try:
        remind = Remind.query.get(remind_id)
    except Exception as e:
        current_app.logger.error(e)
    if not remind:
        return jsonify(errno=RET.NODATA, errmsg="未查询到提醒数据!")

    try:
        db.session.delete(remind)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="删除数据失败!")
    return jsonify(errno=RET.OK, errmsg="删除成功!")


@admin_blu.route("/remind_set", methods=["GET", "POST"])
def remind_set():
    """
    提醒设置
    """
    if request.method == "POST":

        data = request.form
        error_count = int(data.get("error_count"))  # 报错次数阈值 默认10次
        error_time = int(data.get("error_time"))  # 报错时间间隔 默认2分钟
        remind_time = int(data.get("remind_time"))  # 提醒时间间隔 默认10分钟
        read_time = int(data.get("read_time"))  # 读取时间间隔 默认5分钟
        crontab_time = int(data.get("crontab_time"))  # 定时时间间隔 默认30分钟

        if not all([error_count, error_time, remind_time, read_time, crontab_time]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数不全!")
        else:

            # log_name = 'lbcwx.yuns1.cn.error.log'
            # read_logs(log_name, error_count, error_time, remind_time, read_time)
            #
            # crontab_task(crontab_time, read_logs, log_name, error_count, error_time, remind_time, read_time)

            return jsonify(errno=RET.OK, errmsg="设置成功！")
    else:
        return render_template("admin/remind_set.html")
