import json
import os
from zhipuai import ZhipuAI, APIStatusError

flora_api = {}  # 顾名思义,FloraBot的API,载入(若插件已设为禁用则不载入)后会赋值上


def occupying_function(*values):  # 该函数仅用于占位,并没有任何意义
    pass


send_msg = occupying_function
call_api = occupying_function
administrator = []
glm_api_key = ""
glm_session_limit = 0


def init():  # 插件初始化函数,在载入(若插件已设为禁用则不载入)或启用插件时会调用一次,API可能没有那么快更新,可等待,无传入参数
    global send_msg, call_api, administrator, glm_api_key, glm_session_limit, glm_history_msgs, glm_client
    with open(f"{flora_api.get('ThePluginPath')}/Plugin.json", "r", encoding="UTF-8") as open_plugin_config:
        plugin_config = json.loads(open_plugin_config.read())
        glm_api_key = plugin_config.get("ChatGLMApiKey")
        glm_session_limit = plugin_config.get("ChatGLMSessionLimit") * 2
    send_msg = flora_api.get("SendMsg")
    call_api = flora_api.get("CallApi")
    administrator = flora_api.get("Administrator")
    if os.path.isfile(f"{flora_api.get('ThePluginPath')}/ChatGLMHistoryMessages.json"):
        with open(f"{flora_api.get('ThePluginPath')}/ChatGLMHistoryMessages.json", "r", encoding="UTF-8") as open_history_msgs:
            glm_history_msgs = json.loads(open_history_msgs.read())
    glm_client = ZhipuAI(api_key=glm_api_key)
    print("ChatGLM聊天插件 加载成功")


glm_history_msgs = {}
glm_client = ZhipuAI(api_key=glm_api_key)


def chat_glm(msgs: list):  # 调用 ChatGLM 进行聊天的函数
    try:
        msg = glm_client.chat.completions.create(model="glm-4-plus", messages=msgs).choices[0].message.model_dump()
        msg.pop("tool_calls")
        return msg
    except APIStatusError as error:
        return f"Api异常\n状态码: {error.status_code}\n响应内容: {error.response.json()}"


def event(data: dict):  # 事件函数,FloraBot每收到一个事件都会调用这个函数(若插件已设为禁用则不调用),传入原消息JSON参数
    global glm_api_key, glm_client
    send_type = data.get("SendType")
    send_address = data.get("SendAddress")
    ws_client = send_address.get("WebSocketClient")
    ws_server = send_address.get("WebSocketServer")
    send_host = send_address.get("SendHost")
    send_port = send_address.get("SendPort")
    uid = data.get("user_id")  # 事件对象QQ号
    gid = data.get("group_id")  # 事件对象群号
    mid = data.get("message_id")  # 消息ID
    msg = data.get("raw_message")  # 消息内容
    if msg is not None:
        msg = msg.replace("&#91;", "[").replace("&#93;", "]").replace("&amp;", "&").replace("&#44;", ",")  # 消息需要将URL编码替换到正确内容
        if msg.startswith("/GLM "):
            if glm_api_key == "" or glm_api_key is None:
                send_msg(send_type, "异常: ApiKey 为空, 无法调用 ChatGLM\n\n可以去修改插件配置文件进行设置 ApiKey, 也使用以下指令进行设置 ApiKey(警告: ApiKey 是很重要的东西, 请不要在群聊内设置 ApiKey, 发在群聊内可能会被他人恶意利用!!!):\n/GLMApiKey + [空格] + [ApiKey]", uid, gid, None, ws_client, ws_server, send_host, send_port)
            else:
                msg = msg.replace("/GLM ", "", 1)
                if msg == "" or msg.isspace():
                    send_msg(send_type, "内容不能为空", uid, gid, mid, ws_client, ws_server, send_host, send_port)
                else:
                    get_mid = send_msg(send_type, "回答可能需要点时间，请耐心等待...", uid, gid, mid, ws_client, ws_server, send_host, send_port)
                    msgs = []
                    str_uid = str(uid)
                    if str_uid in glm_history_msgs:
                        msgs = glm_history_msgs.get(str_uid)
                    msgs.append({"role": "user", "content": msg})
                    glm_msg = chat_glm(msgs)
                    if type(glm_msg) is str:
                        msgs.pop()
                        if get_mid is not None:
                            # noinspection PyUnresolvedReferences
                            call_api(send_type, "delete_msg", {"message_id": get_mid.get("data").get("message_id")}, ws_client, ws_server, send_host, send_port)
                        send_msg(send_type, f"异常: {glm_msg}", uid, gid, None, ws_client, ws_server, send_host, send_port)
                    else:
                        msgs.append(glm_msg)
                        glm_history_msgs.update({str_uid: msgs})
                        if get_mid is not None:
                            # noinspection PyUnresolvedReferences
                            call_api(send_type, "delete_msg", {"message_id": get_mid.get("data").get("message_id")}, ws_client, ws_server, send_host, send_port)
                        send_msg(send_type, glm_msg.get("content"), uid, gid, mid, ws_client, ws_server, send_host, send_port)
                        if len(msgs) >= glm_session_limit:
                            glm_history_msgs.pop(str_uid)
                            send_msg(send_type, f"我们之间的的对话次数超过了最大值 {glm_session_limit / 2}, 让我们重新开始吧", uid, gid, mid, ws_client, ws_server, send_host, send_port)
                        with open(f"{flora_api.get('ThePluginPath')}/ChatGLMHistoryMessages.json", "w", encoding="UTF-8") as open_history_msgs:
                            open_history_msgs.write(json.dumps(glm_history_msgs, ensure_ascii=False))
        elif msg == "/GLM新的会话":
            glm_history_msgs.pop(str(uid))
            with open(f"{flora_api.get('ThePluginPath')}/ChatGLMHistoryMessages.json", "w", encoding="UTF-8") as open_history_msgs:
                open_history_msgs.write(json.dumps(glm_history_msgs, ensure_ascii=False))
            send_msg(send_type, "已清除聊天记录, 让我们重新开始吧", uid, gid, mid, ws_client, ws_server, send_host, send_port)
        elif msg.startswith("/GLMApiKey "):
            if uid in administrator:
                if gid is not None:
                    send_msg(send_type, "警告: ApiKey 是很重要的东西, 发在群聊内可能会被他人恶意利用, 建议去 智谱AI开放平台 删除该密钥重新创建一个, 然后在私聊使用指令或直接修改插件配置!!!", uid, gid, mid, ws_client, ws_server, send_host, send_port)
                msg = msg.replace("/GLMApiKey ", "", 1)
                if msg == "" or msg.isspace():
                    send_msg(send_type, "异常: ApiKey 为空, ApiKey 设置失败", uid, gid, mid, ws_client, ws_server, send_host, send_port)
                else:
                    glm_api_key = msg
                    with open(f"{flora_api.get('ThePluginPath')}/Plugin.json", "r+", encoding="UTF-8") as open_plugin_config:
                        plugin_config = json.loads(open_plugin_config.read())
                        plugin_config.update({"ChatGLMApiKey": glm_api_key})
                        open_plugin_config.seek(0)
                        open_plugin_config.write(json.dumps(plugin_config, ensure_ascii=False, indent=4))
                        open_plugin_config.truncate()
                    glm_client = ZhipuAI(api_key=glm_api_key)
                    send_msg(send_type, "ApiKey 设置完成", uid, gid, mid, ws_client, ws_server, send_host, send_port)
