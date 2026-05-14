"""
Lightweight i18n helper.

Usage:
    from utils.i18n import _
    st.button(_("Login"))

Strategy:
  - English (en_US) is the source language — key is returned as-is (zero-cost).
  - Other languages look up TRANSLATIONS[lang]; missing keys fall back to the English source.
  - Active language is read from st.session_state.lang, defaulting to DEFAULT_LANG.
"""

from configs.i18n_config import DEFAULT_LANG
from configs.app_config import APP_DISPLAY

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh_CN": {
        # ── Login ──────────────────────────────────────────────────────────
        "Enter your username to continue":   "请输入用户名以继续",
        "Username":                          "用户名",
        "e.g. alice":                        "例如：alice",
        "Login":                             "登录",

        # ── Sidebar ────────────────────────────────────────────────────────
        "Switch User":                       "切换用户",
        "Language":                          "语言",
        "🧬 methylong Pipeline":             "🧬 methylong 流水线",
        "Supported Pipelines":               "支持的流水线",
        "➕ New Session":                    "➕ 新建会话",
        "Session":                           "会话",
        "Sessions":                          "会话列表",
        "messages":                          "条消息",
        "📁 File Management":                "📁 文件管理",
        "Upload files to current session":   "上传文件到当前会话",
        "files":                             "个文件",
        "🗑 Clear session files":            "🗑 清空当前会话文件",
        "Storage by session":                "各会话占用",
        "current":                           "当前",
        "Uploads":                           "上传文件",
        "Run products":                      "运行产物",
        "🗑 Clean run products":             "🗑 清理运行产物",
        "🗑 Clean all run products":         "🗑 清理全部运行产物",

        # ── Main area ──────────────────────────────────────────────────────
        f"🧬 {APP_DISPLAY} Analytics Platform":   f"🧬 {APP_DISPLAY} 智能分析平台",
        "Loading model...":                  "正在加载模型...",
        "Enter your analysis instruction...": "请输入你的分析指令...",

        # ── Status labels ──────────────────────────────────────────────────
        "🔄 Agent running...":               "🔄 Agent 执行中...",
        "⏸️ Awaiting confirmation":          "⏸️ 等待你的确认",
        "✅ Completed":                      "✅ 执行完成",
        "🔄 Resuming...":                    "🔄 继续执行...",
        "⏸️ Awaiting samplesheet confirmation": "⏸️ 等待样本表确认",

        # ── Review panel ───────────────────────────────────────────────────
        "Pending commands — please confirm": "待执行命令，请确认",
        "Last run failed — commands have been auto-corrected":
                                             "上次执行失败，系统已自动修正命令",
        "View error details":                "查看错误详情",
        "Review the corrected commands below and confirm to re-run:":
                                             "请检查以下修正后的命令，确认无误后重新执行：",
        "Pre-requisite files":               "前置文件",
        "Commands to execute":               "待执行命令",
        "Step":                              "步骤",
        "Command list is empty — check parameter generation":
                                             "命令列表为空，请检查参数生成是否正常",
        "🔧 Revision notes (fill in before submitting)":
                                             "🔧 修改意见（提交修改时填写）",
        "✅ Confirm & Run":                  "✅ 确认执行",
        "⚠️ This will run on the server immediately. Are you sure?":
                                             "⚠️ 命令将立即在服务器执行，确定吗？",
        "▶ Yes, run it":                    "▶ 确定执行",
        "← Let me check again":             "← 我再看看",
        "❌ Cancel":                         "❌ 取消任务",
        "💬 Submit Revision":                "💬 提交修改",
        "Please fill in revision notes first": "请先填写修改意见",
        "🚫 Cancelling...":                  "🚫 正在取消任务...",
        "🔄 Regenerating commands...":       "🔄 正在重新生成命令...",
        "⏳ Submitted — task is running, please wait...":
                                             "⏳ 已提交，任务执行中，请稍候...",
        "✅ Task cancelled":                 "✅ 任务已取消",
        "❌ Execution failed — commands auto-corrected, please re-confirm":
                                             "❌ 执行失败，已自动修正命令，请重新确认",

        # ── General ────────────────────────────────────────────────────────
        "🧠 View thinking process":          "🧠 查看思考过程",
        "**📊 Analyze charts**":             "**📊 分析图表**",
        "Download chart":                    "下载图表",
        "✅ Task completed":                 "✅ 任务处理完成",
    }
}


def _(text: str) -> str:
    """Translate text. en_US returns the key as-is; other languages look up the table."""
    try:
        import streamlit as st
        lang = st.session_state.get("lang", DEFAULT_LANG)
    except Exception:
        lang = DEFAULT_LANG

    if lang == "en_US" or lang not in TRANSLATIONS:
        return text

    return TRANSLATIONS[lang].get(text, text)
