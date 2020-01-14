function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(function () {
    $(".release_form").submit(function (e) {
        e.preventDefault()
        // 用户删除
        $(this).ajaxSubmit({
            beforeSubmit: function (request) {
                // 在提交之前，对参数进行处理
                for (var i = 0; i < request.length; i++) {
                    var item = request[i]
                    if (item["name"] == "content") {
                        item["value"] = tinyMCE.activeEditor.getContent()
                    }
                }
            },
            url: "/user_delete",
            type: "POST",
            headers: {
                "X-CSRFToken": getCookie('csrf_token')
            },
            success: function (resp) {
                if (resp.errno == "4000") {
                    // 返回上一页
                    alert(resp.errmsg);
                    location.href = document.referrer;
                } else {
                    alert(resp.errmsg);
                }
            }
        })
    })
})

// 点击取消，返回上一页
function cancel() {
    history.go(-1)
}