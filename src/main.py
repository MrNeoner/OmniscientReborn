"""
================================================================
 ███╗   ██╗███████╗ ██████╗
 ████╗  ██║██╔════╝██╔═══██╗
 ██╔██╗ ██║█████╗  ██║     ██║
 ██║╚██╗██║██╔══╝  ██║    ██║
 ██║ ╚████║███████╗╚██████╔╝
 ╚═╝  ╚═══╝╚══════╝ ╚═════╝
              [ OMNISCIENT ]
================================================================
 © 2026 mrneoner (@phenolion, @neo_plugin)

 LICENSE / ЛИЦЕНЗИЯ:
 EN: Free for personal use and study. Copying, modifying, or
     reusing code fragments in other releases WITHOUT explicit
     permission from the developer and WITHOUT crediting the
     author is STRICTLY PROHIBITED.

 RU: Использовать и изучать код в личных целях можно свободно.
     ОДНАКО любое копирование, модификация или использование
     фрагментов кода в других релизах БЕЗ разрешения
     разработчика и БЕЗ упоминания авторства —
     СТРОГО ЗАПРЕЩЕНО.
================================================================
"""

import threading
import copy
import hashlib
import hmac
import os
import time
import json
import csv
import base64
from datetime import datetime
from typing import Any, List, Dict
import weakref

from file_utils import get_documents_dir
from base_plugin import BasePlugin, MenuItemData, MenuItemType, HookResult, MethodHook
from ui.settings import Header, Text, Divider, Switch, Custom, Input, Selector
from ui.bulletin import BulletinHelper
from ui.alert import AlertDialogBuilder
from client_utils import send_text, get_last_fragment
from android_utils import run_on_ui_thread

from org.telegram.tgnet import TLRPC
from org.telegram.ui.Components import UItem
from org.telegram.messenger import MessagesController, UserConfig, LocaleController, ApplicationLoader
from java import jclass

from android.content import Context, Intent
from android.net import Uri
from android.app import NotificationManager, NotificationChannel, Notification
from android.os import Build

try:
    from .ui.hero import HeroHeaderUI
    from .ui.sheet import OmniscientContactSheet, OmniscientContactCardWidget, OmniscientEventsSheet
    from .ui.card import OmniscientCardRenderer
    from .ui.welcome import OmniWelcomeUI
    from .timeline import format_duration as tl_format_dur, format_time as tl_format_time, get_day_stats
except Exception:
    try:
        from ui.hero import HeroHeaderUI
        from ui.sheet import OmniscientContactSheet, OmniscientContactCardWidget, OmniscientEventsSheet
        from ui.card import OmniscientCardRenderer
        from ui.welcome import OmniWelcomeUI
        from timeline import format_duration as tl_format_dur, format_time as tl_format_time, get_day_stats
    except Exception:
        HeroHeaderUI = OmniscientContactSheet = OmniscientContactCardWidget = OmniscientEventsSheet = OmniscientCardRenderer = OmniWelcomeUI = None

__id__ = "notifcont"
__name__ = "Omniscient Reborn"
__description__ = "Omniscient Reborn — элитный мониторинг активности, онлайна, чтения сообщений и действий контактов."
__author__ = "@mrneoner & @neo_plugin"
__version__ = "2.0.0-beta"
__min_version__ = "12.5.1"
__icon__ = "Eye/6"

PROFILE_ANCHOR_ROWS = ("mutualRow", "phoneRow", "usernameRow", "userInfoRow")

def get_lang() -> str:
    try:
        loc = LocaleController.getInstance().getCurrentLocale()
        if loc is not None:
            l = str(loc.getLanguage()).lower()
            return "ru" if l in ("ru", "be", "uk") else "en"
    except Exception:
        pass
    try:
        from java.util import Locale
        l = str(Locale.getDefault().getLanguage()).lower()
        if l in ("ru", "be", "uk"):
            return "ru"
    except Exception:
        pass
    return "ru"

def c(val):
    if isinstance(val, int):
        val = val & 0xFFFFFFFF
        if val > 0x7FFFFFFF:
            return val - 0x100000000
        return val
    return 0

LANG = get_lang()
_active_plugin_ref = None

def get_current_lang() -> str:
    global LANG, _active_plugin_ref
    if _active_plugin_ref and _active_plugin_ref():
        p = _active_plugin_ref()
        if hasattr(p, "get_lang_code"):
            try:
                code = p.get_lang_code()
                if code in ("ru", "en"):
                    return code
            except Exception:
                pass
    return LANG

STRINGS = {
    "ru": {
        "show_profile_tracker": "Отображать трекер",
        "show_profile_tracker_desc": "Отображает информацию о последнем визите и статусе контакта непосредственно в профиле.",
        "backup_deleted": "Бэкап успешно удален",
        "manage_backups_title": "Управление бэкапами",
        "open_backup_folder": "Управление бэкапами",
        "open_folder_title": "Выберите приложение",
        "restore_auto_backup": "Восстановить настройки",
        "restore_auto_backup_title": "Выберите бэкап",
        "no_auto_backups": "Автобэкапы не найдены",
        "backup_header": "Резервное копирование",
        "export_backup": "Экспорт настроек",
        "import_backup": "Импорт настроек",
        "import_confirm_title": "Восстановление",
        "import_confirm_msg": "Найдено {u} контактов.\nПродолжить восстановление?",
        "import_success_msg": "Контакты успешно восстановлены",
        "import_fail": "Ошибка чтения файла или данные повреждены.",
        "add_remove": "Отслеживать активность",
        "click_to_track_short": "Мониторинг активности и сессий",
        "easter_warning_title": "Предупреждение!",
        "easter_warning_1": "Лучше не нажимай.",
        "easter_warning_2": "Хватит нажимать!",
        "easter_final_title": "Мяьшлчпл...",
        "easter_final_msg": "Жщивсв ёжю ы ек ъмйёщеэщ!..",
        "not_private": "Действие доступно только в личных чатах",
        "notify_in_app": "Уведомления в приложении",
        "hyperbridge_beta_warning": "⚠️ Режим HyperBridge (только на Xiaomi HyperOS 3+) и Система уведомлений могут работать некорректно из-за различных особенностей клиента.",
        "removed": "Уведомления отключены",
        "added": "Уведомления включены",
        "online": "В сети",
        "offline": "Не в сети",
        "micro_session": "Был в сети пару секунд",
        "read": "Прочитал сообщение",
        "read_multiple": "Прочитал несколько сообщений",
        "sleep_pattern_format": "Обычно засыпает в {time} на {dur}",
        "co_online_count": "Совпадали в сети {count} раз",
        "changed_name": "Изменил имя:",
        "empty_history": "Нет истории событий",
        "clear": "Очистить историю",
        "export": "Поделиться историей",
        "logs_cleared": "История успешно очищена",
        "master_observation_header": "Настройки событий",
        "master_observation": "Общий выключатель",
        "track_observation": "Типы событий",
        "track_online": "Статус сети",
        "track_read": "Прочтение сообщений",
        "track_name": "Смена имени",
        "track_messages_header": "События сообщений",
        "track_deleted": "Удаленные сообщения",
        "track_edited": "Измененные сообщения",
        "track_ttl": "Самоудаляющиеся сообщения",
        "track_block": "Скрытый статус",
        "master_notifications_header": "Управление уведомлениями",
        "master_notifications": "Общий выключатель",
        "track_notifications": "Категории уведомлений",
        "notify_system": "Системные уведомления",
        "notify_hyperbridge": "Режим HyperBridge",
        "notify_online": "Уведомлять о сети",
        "notify_offline": "Уведомлять о выходе",
        "notify_read": "Уведомлять о прочтении",
        "notify_name": "Уведомлять о смене имени",
        "notify_deleted": "Уведомлять об удалении",
        "notify_edited": "Уведомлять об изменении",
        "notify_ttl": "Уведомлять о медиа",
        "notify_block": "Уведомлять о скрытом статусе",
        "hyperbridge": "Использовать HyperBridge",
        "logs_title": "Настройки истории",
        "max_logs": "Лимит сохраняемых событий",
        "stats_title": "Информация о контактах",
        "stats_empty": "Список контактов пуст",
        "user_stats": "Нажмите для настройки",
        "export_success": "Данные успешно отправлены",
        "export_error": "Ошибка при экспорте",
        "activity_title": "События за {date}",
        "sessions_log": "Журнал сессий:",
        "session_interrupted_note": "\n[!] — сессия прервана перезапуском или крашем плагина, либо нестабильным соединением",
        "other_events": "Другие события:",
        "no_data": "Нет данных",
        "stat_total_time": "Всего онлайн:",
        "stat_reads": "Прочитано сообщений:",
        "stat_peak": "Самый активный час:",
        "stat_sleep": "Сон:",
        "stat_loyalty": "График лояльности:",
        "remove_user": "Удалить из списка",
        "custom_tag": "Пользовательский тег",
        "log_filter": "Сортировка событий",
        "track_typing": "Набор текста",
        "typing": "Набирает сообщение...",
        "tracked_list": "Список контактов",
        "saved_messages": "Избранное",
        "wakelock": "WakeLock",
        "wakelock_desc": "WakeLock позволяет работать плагину в фоне. \nМожет увеличить расход батареи устройства.",
        "auto_clean_days": "Автоочистка истории (дней)",
        "about_dev": "О разработчике",
        "plugin_channel": "Канал плагина",
        "contact_me": "Связь со мной",
        "special_thanks": "Отдельная благодарность",
        "danger_zone": "Опасная зона",
        "factory_reset": "Удалить все данные и настройки",
        "factory_reset_desc": "Полный сброс информации",
        "basic_tracking_params": "Базовые параметры уведомлений",
        "enabled_status": "✅ Включено",
        "disabled_status": "❌ Отключено",
        "view_stats": "Посмотреть события",
        "notifications_toggle": "Уведомления",
        "filter_all": "Все события",
        "filter_network": "Статус сети",
        "filter_messages": "Сообщения",
        "filter_reads": "Прочтения",
        "filter_other": "Профиль и другое",
        "cancel": "Отмена",
        "time_h": "ч",
        "time_m": "м",
        "logs_copied": "Логи успешно скопированы!",
        "spam_trap": "Скрыл статус",
        "time_s": "с",
        "wakelock_enabled": "WakeLock включен",
        "wakelock_disabled": "WakeLock отключен",
        "loyalty_ignore": "Проигнорировано:",
        "media_analysis": "\n📊 Медиа:",
        "stats_empty_hint": "Список контактов пуст.\n\nЧтобы добавить человека, откройте с ним личный чат, перейдите в его профиль (или меню чата ⋮), нажмите «Omniscient Tracker».",
        "media_text_other": "Текст/Другое:",
        "media_photo": "Фото:",
        "media_video": "Видео:",
        "media_voice_round": "ГС и Кружки:",
        "history_empty": "Ничего не найдено",
        "micro_session_1": "{time} ⚡ Быстрая сессия",
        "micro_session_n": "{time} ⚡ Заходил(а) {count} раз (с {start})",
        "histogram": "Гистограмма часов (0-23):\n",
        "morning": "🌅 Утро (06-12):",
        "day": "☀️ День (12-18):",
        "evening": "🌆 Вечер (18-00):",
        "night": "🌙 Ночь (00-06):",
        "analytics_title": "=== ЖУРНАЛ СОБЫТИЙ ===\n",
        "full_history_title": "\n=== ПОЛНАЯ ИСТОРИЯ ===\n",
        "online_status_history": "🟢 {time} - ... (В сети)",
        "came_and_left": "Зашел и вышел, не прочитав сообщение",
        "chat_not_found": "Не удалось найти чат",
        "track_confirm_title": "Включение уведомлений",
        "track_confirm_msg": "Включить расширенные уведомления и историю событий для пользователя {name}?",
        "btn_confirm": "Включить",
        "delete_title": "Удаление",
        "delete_msg": "Удалить пользователя из списка особых контактов? Вся история событий будет удалена.",
        "auto_backup": "Авто-бэкапы",
        "auto_backup_days": "Частота авто-бэкапа (дни)",
        "ok": "ОК",
        "auto_backup_desc": "⚠️ Периодически сохраняет файл настроек в папку Documents/Omniscient в директории клиента.",
        "backup_success": "Авто-бэкап Omniscient успешно сохранен в файл:\n{path}",
        "btn_delete": "Удалить",
        "clear_title": "Очистка данных",
        "clear_msg": "Вы уверены, что хотите безвозвратно удалить всю историю событий этого пользователя?",
        "btn_clear": "Очистить",
        "reset_success": "Все данные и настройки удалены",
        "reset_title": "Удаление данных",
        "reset_msg": "Вы уверены, что хотите удалить ВСЮ историю событий, сбросить настройки плагина и безвозвратно удалить все бэкапы? Это действие необратимо!",
        "btn_delete_all": "Удалить всё",
        "export_chooser": "Поделиться историей",
        "export_err": "Ошибка экспорта: {e}",
        "import_err_explorer": "Не удалось открыть проводник",
        "import_err_open": "Ошибка открытия проводника: {e}",
        "import_err_file": "Не удалось открыть файл",
        "import_err_key": "Ошибка файла или неверный ключ",
        "import_err_db": "Отсутствует база контактов",
        "import_success": "Данные восстановлены!",
        "import_toast_success": "Omniscient: Данные успешно импортированы!",
        "import_err_verify": "Ошибка верификации данных",
        "import_toast_err": "Ошибка: {e}",
        "db_read_err": "Ошибка чтения базы. Ключ шифрования изменён или файл поврежден.",
        "link_copied": "Ссылка скопирована!",
        "share_link_title": "Поделиться ссылкой",
        "copy_link": "Копировать ссылку",
        "share_link": "Поделиться ссылкой",
        "media_type_photo": "[Фото]",
        "csv_export": "Экспорт в CSV",
        "export_csv": "Экспорт в CSV",
        "export_txt": "Экспорт в TXT",
        "export_msg": "Отправить сообщением",
        "media_type_voice": "[Голосовое]",
        "media_type_round": "[Кружок]",
        "media_type_video": "[Видео]",
        "media_type_file": "[Файл]",
        "pin_user": "Закрепить в списке",
        "local_name": "Локальный псевдоним",
        "prediction_offline": "Обычно в это время не в сети. Вероятный заход через ~{hours} ч.",
        "prediction_online": "Обычно в сети в это время.",
        "debug_header": "Отладка",
        "debug_errors_count": "Ошибок за сессию: {count}",
        "debug_copy_subtext": "Нажми, чтобы скопировать логи",
        "profile_tracker_title": "Omniscient Tracker",
        "omni_logs_title": "Журнал Omniscient:",
        "profile_tracker_last_seen": "Последний заход: {time}",
        "backup_error_copied": "Ошибка! Лог скопирован в буфер.",
        "test_auto_backup": "Сделать бэкап сейчас",
        "test_backup_done": "Бэкап создан! Проверьте Избранное.",
        "backup_error": "Ошибка при создании файла автобэкапа.",
        "plugin_restarted": "Сессия прервана",
        "dnd_start": "Начало тихих часов (ЧЧ:ММ)",
        "dnd_end": "Конец тихих часов (ЧЧ:ММ)",
        "export_card": "Инфографика активности (PNG)",
        "active_state": "Активен",
        "paused_state": "Приостановлен",
        "tracked_count_label": "Отслеживаемых контактов: {count}"
    },
    "en": {
        "backup_header": "Backup",
        "export_backup": "Export settings",
        "import_backup": "Import settings",
        "import_confirm_title": "Restore Data",
        "import_confirm_msg": "Found {u} users.\nContinue?",
        "plugin_restarted": "Session interrupted",
        "omni_logs_title": "Omniscient Logs:",
        "import_success_msg": "Contacts successfully restored",
        "import_fail": "Error. File is corrupted or unsupported.",
        "add_remove": "Track Activity",
        "click_to_track_short": "Monitor activity & sessions",
        "not_private": "Action available only in private chats",
        "auto_backup": "Auto-backup",
        "auto_backup_days": "Auto-backup frequency (days)",
        "backup_deleted": "Backup successfully deleted",
        "restore_auto_backup": "Restore auto-backup",
        "restore_auto_backup_title": "Select backup",
        "no_auto_backups": "No auto-backups found",
        "auto_backup_desc": "⚠️ Periodically saves .omni file to Documents/Omniscient folder.",
        "backup_success": "Omniscient auto-backup successfully saved to file:\n{path}",
        "removed": "Notifications disabled",
        "added": "Notifications enabled",
        "online": "Online",
        "offline": "Offline",
        "micro_session": "Was online for a few seconds",
        "read": "Read the message",
        "read_multiple": "Read several messages",
        "changed_name": "Changed name:",
        "empty_history": "No event history",
        "clear": "Clear history",
        "export": "Share history",
        "logs_cleared": "History successfully cleared",
        "easter_warning_title": "Warning",
        "easter_warning_1": "You'd better not click again.",
        "easter_warning_2": "Stop clicking!",
        "easter_final_title": "Oops...",
        "easter_final_msg": "I was too lazy to come up with an easter egg in english. Swap language to Russian and get this menu again.",
        "manage_backups_title": "Manage backups",
        "master_observation_header": "Event control",
        "notify_in_app": "In-app notifications",
        "hyperbridge_beta_warning": "⚠️ HyperBridge mode (only on Xiaomi HyperOS 3+) and the notification system may not function correctly due to various client-specific factors.",
        "master_observation": "Master switch",
        "show_profile_tracker": "Show tracker",
        "show_profile_tracker_desc": "Displays information about the last visit and status of the contact in the profile.",
        "track_observation": "Event types",
        "track_online": "Network status",
        "track_read": "Message reads",
        "track_name": "Name changes",
        "track_messages_header": "Message events",
        "track_deleted": "Deleted messages",
        "track_edited": "Edited messages",
        "track_ttl": "Self-destructing messages",
        "track_block": "Hidden Status",
        "master_notifications_header": "Notifications control",
        "master_notifications": "Master switch",
        "track_notifications": "Notification categories",
        "notify_system": "System notifications",
        "notify_hyperbridge": "HyperBridge mode",
        "csv_export": "Export to CSV",
        "export_csv": "Export to CSV",
        "export_txt": "Export to TXT",
        "export_msg": "Send as message",
        "notify_online": "Notify when online",
        "notify_offline": "Notify when offline",
        "notify_read": "Notify on read",
        "notify_name": "Notify on name change",
        "notify_deleted": "Notify on delete",
        "notify_edited": "Notify on edit",
        "notify_ttl": "Notify on media",
        "notify_block": "Notify on Hidden Status",
        "hyperbridge": "Use HyperBridge",
        "logs_title": "History settings",
        "track_typing": "Typing status",
        "typing": "Typing a message...",
        "sleep_pattern_format": "Usually sleeps at {time} for {dur}",
        "co_online_count": "Co-online matches {count} times",
        "dnd_start": "DND start (HH:MM)",
        "dnd_end": "DND end (HH:MM)",
        "max_logs": "Maximum events limit",
        "stats_title": "Contacts information",
        "stats_empty": "Contacts list is empty",
        "user_stats": "Tap for settings",
        "export_success": "Data successfully sent",
        "export_error": "Error exporting data",
        "activity_title": "Events for {date}",
        "sessions_log": "Sessions log:",
        "session_interrupted_note": "\n[!] — session interrupted by a plugin restart or crash, or an unstable connection",
        "other_events": "Other events:",
        "no_data": "No data",
        "stats_empty_hint": "Contacts list is empty.\n\nTo add a person, open a private chat with them, open profile or 3-dots chat menu and tap 'Omniscient Tracker'.",
        "stat_total_time": "Total time online:",
        "stat_reads": "Messages read:",
        "stat_peak": "Most active hour:",
        "stat_sleep": "Sleep:",
        "stat_loyalty": "Activity Graph:",
        "remove_user": "Remove from list",
        "custom_tag": "Custom Tag",
        "log_filter": "Sort events",
        "tracked_list": "Contacts list",
        "saved_messages": "Saved Messages",
        "wakelock": "WakeLock",
        "wakelock_desc": "WakeLock keeps app running in the background. May increase battery consumption.",
        "open_backup_folder": "Open backups folder",
        "open_folder_title": "Choose application",
        "auto_clean_days": "Auto-clean history (days)",
        "about_dev": "About developer",
        "plugin_channel": "Plugin channel",
        "contact_me": "Contact me",
        "special_thanks": "Special thanks",
        "danger_zone": "Danger zone",
        "factory_reset": "Delete all data and settings",
        "factory_reset_desc": "Full factory reset of the plugin",
        "basic_tracking_params": "Basic notification parameters",
        "ok": "OK",
        "enabled_status": "✅ Enabled",
        "disabled_status": "❌ Disabled",
        "view_stats": "View events",
        "notifications_toggle": "Notifications",
        "filter_all": "All events",
        "filter_network": "Network status",
        "filter_messages": "Messages",
        "filter_reads": "Reads",
        "filter_other": "Profile and other",
        "cancel": "Cancel",
        "time_h": "h",
        "time_m": "m",
        "time_s": "s",
        "wakelock_enabled": "WakeLock enabled",
        "wakelock_disabled": "WakeLock disabled",
        "loyalty_ignore": "Ignored:",
        "media_analysis": "\n📊 Media:",
        "media_text_other": "Text/Other:",
        "media_photo": "Photo:",
        "media_video": "Video:",
        "media_voice_round": "Voice & Round:",
        "history_empty": "Nothing found",
        "micro_session_1": "{time} ⚡ Quick session",
        "micro_session_n": "{time} ⚡ Online {count} times (since {start})",
        "histogram": "Hours histogram (0-23):\n",
        "morning": "🌅 Morning (06-12):",
        "day": "☀️ Day (12-18):",
        "evening": "🌆 Evening (18-00):",
        "night": "🌙 Night (00-06):",
        "analytics_title": "=== EVENT LOG ===\n",
        "full_history_title": "\n=== FULL HISTORY ===\n",
        "online_status_history": "🟢 {time} - ... (Online)",
        "came_and_left": "Came and left without reading",
        "chat_not_found": "Chat not found",
        "track_confirm_title": "Enable notifications",
        "track_confirm_msg": "Enable extended notifications and event history for user {name}?",
        "btn_confirm": "Enable",
        "delete_title": "Deletion",
        "delete_msg": "Remove user from special contacts? All event history will be deleted.",
        "btn_delete": "Delete",
        "clear_title": "Clear data",
        "clear_msg": "Are you sure you want to permanently delete all event history for this user?",
        "btn_clear": "Clear",
        "reset_success": "All data and settings deleted",
        "reset_title": "Delete data",
        "reset_msg": "Are you sure you want to delete ALL history, reset the plugin, and permanently delete all backups? This action is irreversible!",
        "btn_delete_all": "Delete all",
        "export_chooser": "Share history",
        "export_err": "Export error: {e}",
        "import_err_explorer": "Failed to open file explorer",
        "logs_copied": "Logs copied successfully!",
        "spam_trap": "Hidden status",
        "import_err_open": "Error opening explorer: {e}",
        "import_err_file": "Failed to open file",
        "import_err_key": "File error or invalid key",
        "import_err_db": "Missing contacts database",
        "import_success": "Data restored!",
        "import_toast_success": "Omniscient: Database successfully imported!",
        "import_err_verify": "Data verification error",
        "import_toast_err": "Error: {e}",
        "db_read_err": "Database read error. Encryption key changed or file corrupted.",
        "link_copied": "Link copied!",
        "share_link_title": "Share link",
        "copy_link": "Copy link",
        "share_link": "Share link",
        "media_type_photo": "[Photo]",
        "media_type_voice": "[Voice]",
        "media_type_round": "[Round]",
        "media_type_video": "[Video]",
        "media_type_file": "[File]",
        "pin_user": "Pin in list",
        "local_name": "Local Nickname",
        "prediction_offline": "Usually offline at this time. Expected login in ~{hours} h.",
        "prediction_online": "Usually online at this time.",
        "backup_error_copied": "Error! Log copied to clipboard.",
        "debug_header": "Debug",
        "debug_errors_count": "Session errors: {count}",
        "debug_copy_subtext": "Tap to copy logs",
        "profile_tracker_title": "Omniscient Tracker",
        "profile_tracker_last_seen": "Last seen: {time}",
        "test_auto_backup": "Force backup now",
        "test_backup_done": "Test backup created! Check Saved Messages.",
        "backup_error": "Error creating auto-backup file.",
        "export_card": "Activity Infographic (PNG)",
        "active_state": "Active",
        "paused_state": "Paused",
        "tracked_count_label": "Tracked contacts: {count}"
    }
}

def T(key: str) -> str:
    lang = get_current_lang()
    return STRINGS.get(lang, STRINGS.get("en", {})).get(key, key)

class ImportResultHook(MethodHook):
    def __init__(self, plugin):
        super().__init__()
        self._plugin_ref = weakref.ref(plugin)

    def after_hooked_method(self, param):
        try:
            req_code = int(param.args[0])
            if req_code not in (8192, 8193):
                return

            res_code = int(param.args[1])
            if res_code != -1:
                return

            data_intent = param.args[2]
            if not data_intent:
                return

            uri = data_intent.getData()
            if not uri:
                return

            plugin = self._plugin_ref()
            if not plugin:
                return

            if req_code == 8192:
                plugin._handle_import_uri(uri)
            elif req_code == 8193:
                plugin._handle_custom_bg_uri(uri)
        except Exception:
            pass

class OmniProfileUpdateRowsHook:
    def __init__(self, *a, **k): pass
class OmniProfileGetTypeHook:
    def __init__(self, *a, **k): pass
class OmniProfileBindHook:
    def __init__(self, *a, **k): pass

def find_plugin_file(subpath: str) -> str:
    if not subpath:
        return ""
    sub = str(subpath).replace("\\", "/").strip("/")
    candidates = []

    for mod_name in ("main", "__main__", __name__):
        try:
            import sys
            mod = sys.modules.get(mod_name)
            if mod and getattr(mod, "__file__", None):
                curr = os.path.abspath(mod.__file__)
                for _ in range(7):
                    curr = os.path.dirname(curr)
                    candidates.append(os.path.join(curr, sub))
                    candidates.append(os.path.join(curr, "OmniscientReborn", sub))
                    candidates.append(os.path.join(curr, "omniscient_reborn", sub))
        except Exception:
            pass

    try:
        f_val = globals().get("__file__")
        if f_val:
            curr = os.path.abspath(f_val)
            for _ in range(7):
                curr = os.path.dirname(curr)
                candidates.append(os.path.join(curr, sub))
                candidates.append(os.path.join(curr, "OmniscientReborn", sub))
                candidates.append(os.path.join(curr, "omniscient_reborn", sub))
    except Exception:
        pass

    try:
        cwd = os.getcwd()
        candidates.append(os.path.join(cwd, sub))
        candidates.append(os.path.join(cwd, "OmniscientReborn", sub))
        candidates.append(os.path.join(cwd, "omniscient_reborn", sub))
        candidates.append(os.path.join(cwd, "plugins", "omniscient_reborn", sub))
        candidates.append(os.path.join(cwd, "plugins", "ElyxPlugins", "omniscient_reborn", sub))
    except Exception:
        pass

    try:
        from org.telegram.messenger import ApplicationLoader
        fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
        for folder in ("omniscient_reborn", "OmniscientReborn", "Omniscient_Reborn", "notifcont", ""):
            if folder:
                candidates.append(os.path.join(fdir, "plugins", "ElyxPlugins", folder, "OmniscientReborn", sub))
                candidates.append(os.path.join(fdir, "plugins", "ElyxPlugins", folder, sub))
                candidates.append(os.path.join(fdir, "plugins", folder, "OmniscientReborn", sub))
                candidates.append(os.path.join(fdir, "plugins", folder, sub))
                candidates.append(os.path.join(fdir, folder, sub))
            else:
                candidates.append(os.path.join(fdir, sub))
    except Exception:
        pass

    try:
        import sys
        for sp in sys.path:
            candidates.append(os.path.join(sp, sub))
            candidates.append(os.path.join(sp, "OmniscientReborn", sub))
            candidates.append(os.path.join(sp, "omniscient_reborn", sub))
    except Exception:
        pass

    for cand in candidates:
        try:
            if cand and os.path.exists(cand):
                return os.path.abspath(cand)
        except Exception:
            pass

    try:
        from org.telegram.messenger import ApplicationLoader
        fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
        base_name = os.path.basename(sub)
        cache_dir = os.path.join(fdir, "cache", "omniscient_res")
        target = os.path.join(cache_dir, base_name)
        if os.path.exists(target):
            return target

        import zipfile
        plugins_dir = os.path.join(fdir, "plugins")
        if os.path.exists(plugins_dir):
            for root_dir, _, files in os.walk(plugins_dir):
                for fn in files:
                    if fn.endswith((".eaf", ".zip")) and any(k in fn.lower() for k in ("omniscient", "reborn", "notif")):
                        archive = os.path.join(root_dir, fn)
                        try:
                            with zipfile.ZipFile(archive, 'r') as zf:
                                for zname in zf.namelist():
                                    if zname.endswith("/" + base_name) or zname == base_name:
                                        os.makedirs(cache_dir, exist_ok=True)
                                        with open(target, "wb") as out_f:
                                            out_f.write(zf.read(zname))
                                        return target
                        except Exception:
                            pass
    except Exception:
        pass

    return sub

class OmniscientRebornPlugin(BasePlugin):
    is_beta = True

    def _res_path(self, filename: str = "") -> str:
        if not filename:
            try:
                f_val = globals().get("__file__")
                curr = os.path.dirname(os.path.abspath(f_val)) if f_val else ""
                for base in (os.path.dirname(curr) if curr else "", curr, os.path.dirname(os.path.dirname(curr)) if curr else ""):
                    if not base:
                        continue
                    res_dir = os.path.join(base, "res")
                    if os.path.isdir(res_dir):
                        return res_dir
            except Exception:
                pass
            return ""

        for mod_name in ("assets", "elyx.assets"):
            try:
                import sys
                m = sys.modules.get(mod_name)
                if not m:
                    m = __import__(mod_name, fromlist=["*"])
                if m:
                    stem = os.path.splitext(filename)[0]
                    for key in (stem, filename, filename.lower()):
                        obj = getattr(m, key, None)
                        if not obj and hasattr(m, "res"):
                            obj = getattr(m.res, key, None)
                        if not obj and hasattr(m, "assets"):
                            obj = getattr(m.assets, key, None)
                        if obj:
                            for p_attr in ("path_str", "path"):
                                p = getattr(obj, p_attr, None)
                                if p and os.path.exists(str(p)):
                                    return str(p)
                            if hasattr(obj, "java_file"):
                                jf = getattr(obj, "java_file")
                                if jf and hasattr(jf, "getAbsolutePath"):
                                    p = str(jf.getAbsolutePath())
                                    if os.path.exists(p):
                                        return p
            except Exception:
                pass

        for prefix in ("res", "assets", "OmniscientReborn/res", "OmniscientReborn/assets", ""):
            target = os.path.join(prefix, filename) if prefix else filename
            p = find_plugin_file(target)
            if p and os.path.exists(p):
                return p

        return ""

    def _asset_path(self, filename: str = "") -> str:
        return self._res_path(filename)

    def _is_dark_theme(self) -> bool:
        try:
            from org.telegram.ui.ActionBar import Theme
            return Theme.isCurrentThemeDark()
        except Exception:
            return True

    def _get_account(self) -> int:
        try:
            from org.telegram.messenger import UserConfig
            return UserConfig.selectedAccount
        except Exception:
            return 0

    def get_user_avatar_path(self, uid: Any) -> str:
        try:
            from org.telegram.messenger import FileLoader, MessagesController, MessagesStorage, ImageLocation, UserConfig
            Long = jclass("java.lang.Long")
            acc = UserConfig.selectedAccount
            mc = MessagesController.getInstance(acc)
            uid_str = str(uid).strip()
            if not uid_str.lstrip("-").isdigit():
                return ""
            uid_long = Long.parseLong(uid_str)
            user = mc.getUser(uid_long)
            if not user:
                try:
                    user = MessagesStorage.getInstance(acc).getUserSync(uid_long)
                except Exception:
                    pass
            if not user:
                return ""

            locations = []
            if hasattr(user, "photo") and user.photo:
                if hasattr(user.photo, "photo_big") and user.photo.photo_big:
                    locations.append(user.photo.photo_big)
                if hasattr(user.photo, "photo_small") and user.photo.photo_small:
                    locations.append(user.photo.photo_small)
            try:
                l_big = ImageLocation.getForUser(user, ImageLocation.TYPE_BIG)
                if l_big:
                    locations.append(l_big)
                l_small = ImageLocation.getForUser(user, ImageLocation.TYPE_SMALL)
                if l_small:
                    locations.append(l_small)
            except Exception:
                pass

            fl = FileLoader.getInstance(acc)
            for loc in locations:
                for force in (True, False):
                    try:
                        f = fl.getPathToAttach(loc, force)
                        if f and f.exists() and f.length() > 0:
                            return str(f.getAbsolutePath())
                    except Exception:
                        pass

            for loc in locations:
                try:
                    fl.loadFile(loc, "jpg", 1, 1)
                except Exception:
                    pass
            for _ in range(15):
                time.sleep(0.1)
                for loc in locations:
                    for force in (True, False):
                        try:
                            f = fl.getPathToAttach(loc, force)
                            if f and f.exists() and f.length() > 0:
                                return str(f.getAbsolutePath())
                        except Exception:
                            pass
        except Exception as e:
            self._log_error(f"get_user_avatar_path err: {e}")
        return ""

    def sync_contact_names(self, specific_uid: str = None):
        try:
            from org.telegram.messenger import MessagesController
            acc = self._get_account()
            mc = MessagesController.getInstance(acc)
            updated_count = 0
            with self._data_lock:
                target_uids = [str(specific_uid)] if specific_uid else list(self.tracked_users.keys())
                for uid in target_uids:
                    try:
                        u_obj = mc.getUser(int(uid))
                        if u_obj:
                            first = getattr(u_obj, "first_name", "") or ""
                            last = getattr(u_obj, "last_name", "") or ""
                            username = getattr(u_obj, "username", "") or ""
                            full = f"{first} {last}".strip()
                            if full:
                                self.tracked_users[uid]["name"] = full
                                self.tracked_users[uid]["first_name"] = full
                            if username:
                                self.tracked_users[uid]["username"] = username
                            updated_count += 1
                    except Exception:
                        pass
            if updated_count > 0:
                self._save_users_sync()
                self.set_setting("last_contacts_sync", int(time.time()), reload_settings=True)
                BulletinHelper.show_success(f"Имена обновлены ({updated_count})")
            else:
                BulletinHelper.show_info("Изменений в именах не обнаружено")
        except Exception as e:
            self._log_error(f"sync_contact_names err: {e}")
            BulletinHelper.show_error(f"Ошибка синхронизации: {e}")

    def show_contact_sheet(self, uid: str):
        def _do_show():
            try:
                fragment = get_last_fragment()
                if not fragment or not fragment.getParentActivity():
                    return
                ctx = fragment.getParentActivity()
                uid_str = str(uid)
                with self._data_lock:
                    user_data = copy.deepcopy(self.tracked_users.get(uid_str) or self.tracked_users.get(uid) or {})
                if not user_data:
                    return
                user_data["id"] = uid_str
                user_data["name"] = self.get_display_name(uid_str, user_data)
                if OmniscientContactSheet:
                    OmniscientContactSheet.show(
                        plugin=self,
                        ctx=ctx,
                        user_data=user_data,
                        alert_builder_cls=AlertDialogBuilder,
                        on_card_click=lambda: self.export_card(uid_str),
                        on_logs_click=lambda: self.show_user_history(None, uid_str),
                        on_settings_click=lambda: self.prompt_user_settings_menu(uid_str),
                        on_remove_click=lambda: self.remove_user(uid_str)
                    )
                else:
                    self.show_user_history(None, uid_str)
            except Exception as e:
                self._log_error(f"show_contact_sheet err: {e}")

        if run_on_ui_thread:
            run_on_ui_thread(_do_show)
        else:
            _do_show()

    def prompt_user_settings_menu(self, uid: str):
        fragment = get_last_fragment()
        if not fragment or not fragment.getParentActivity():
            return
        ctx = fragment.getParentActivity()
        uid_str = str(uid)
        with self._data_lock:
            data = copy.deepcopy(self.tracked_users.get(uid_str) or {})
        if not data:
            return

        name = self.get_display_name(uid_str, data)
        is_pinned = data.get("is_pinned", False)
        pin_text = "Открепить контакт" if is_pinned else "Закрепить контакт"
        notify_en = data.get("notifications_enabled", True)
        notify_text = "Отключить уведомления" if notify_en else "Включить уведомления"

        builder = AlertDialogBuilder(ctx)
        builder.set_title(f"Опции: {name}")

        items = [
            "Установить тег",
            "Локальное имя",
            pin_text,
            notify_text,
            "Очистить историю событий",
            "Удалить из мониторинга"
        ]

        def callback(d, w):
            if w == 0:
                self.prompt_edit_tag(uid_str)
            elif w == 1:
                self.prompt_edit_local_name(uid_str)
            elif w == 2:
                self.update_user_pin(uid_str, not is_pinned)
                BulletinHelper.show_success("Контакт обновлен")
            elif w == 3:
                self.update_user_notify(uid_str, not notify_en)
                BulletinHelper.show_success("Уведомления обновлены")
            elif w == 4:
                self.clear_logs(uid_str)
            elif w == 5:
                self.remove_user(uid_str)

        builder.set_items(items, callback)
        builder.set_negative_button("Отмена", lambda d, w: None)
        builder.show()

    def prompt_edit_tag(self, uid: str):
        fragment = get_last_fragment()
        if not fragment or not fragment.getParentActivity():
            return
        ctx = fragment.getParentActivity()
        with self._data_lock:
            cur = self.tracked_users.get(uid, {}).get("custom_tag", "")
        builder = AlertDialogBuilder(ctx)
        builder.set_title("Тег контакта")
        try:
            from android.widget import EditText
            et = EditText(ctx)
            et.setText(cur)
            et.setHint("Например: Коллега, VIP")
            builder.set_view(et)
        except Exception:
            et = None
        def on_ok(d, w):
            if et:
                val = str(et.getText()).strip()
                self.update_user_tag(uid, val)
                BulletinHelper.show_success("Тег сохранен")
        builder.set_positive_button("Сохранить", on_ok)
        builder.set_negative_button("Отмена", lambda d, w: None)
        builder.show()

    def prompt_edit_local_name(self, uid: str):
        fragment = get_last_fragment()
        if not fragment or not fragment.getParentActivity():
            return
        ctx = fragment.getParentActivity()
        with self._data_lock:
            cur = self.tracked_users.get(uid, {}).get("local_name", "")
        builder = AlertDialogBuilder(ctx)
        builder.set_title("Локальное имя")
        try:
            from android.widget import EditText
            et = EditText(ctx)
            et.setText(cur)
            et.setHint("Введите имя контакта")
            builder.set_view(et)
        except Exception:
            et = None
        def on_ok(d, w):
            if et:
                val = str(et.getText()).strip()
                self.update_user_local_name(uid, val)
                BulletinHelper.show_success("Имя сохранено")
        builder.set_positive_button("Сохранить", on_ok)
        builder.set_negative_button("Отмена", lambda d, w: None)
        builder.show()

    def handle_add_contact_input(self, val: str):
        if not val:
            return
        raw = str(val).strip()
        if not raw:
            return
        clean = raw.replace("@", "").strip()
        if clean.isdigit():
            uid_int = int(clean)
            self._add_user_by_id(uid_int, f"ID: {uid_int}")
        else:
            self._resolve_and_add_username(clean)

    def prompt_add_user_id(self):
        fragment = get_last_fragment()
        if not fragment or not fragment.getParentActivity():
            return
        ctx = fragment.getParentActivity()

        is_ru = self.get_lang_code() == "ru"
        builder = AlertDialogBuilder(ctx)
        builder.set_title("Добавить контакт" if is_ru else "Add Contact")
        builder.set_message("Введите цифровой User ID или @username пользователя:" if is_ru else "Enter numerical User ID or @username:")

        input_et = None
        try:
            from android.widget import EditText
            from android.graphics.drawable import GradientDrawable
            from org.telegram.messenger import AndroidUtilities
            from org.telegram.ui.ActionBar import Theme
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)
            dark = self._is_dark_theme() if hasattr(self, "_is_dark_theme") else True

            input_et = EditText(ctx)
            input_et.setHint("123456789 или @username" if is_ru else "123456789 or @username")
            text_color = 0xFFFFFFFF if dark else 0xFF0F172A
            hint_color = 0xFF94A3B8 if dark else 0xFF64748B
            if Theme is not None:
                try:
                    text_color = Theme.getColor(Theme.key_dialogText)
                    hint_color = Theme.getColor(Theme.key_dialogTextHint)
                except Exception:
                    pass
            input_et.setTextColor(c(text_color))
            input_et.setHintTextColor(c(hint_color))
            input_et.setTextSize(1, 15.5)
            input_et.setSingleLine(True)
            input_et.setLines(1)

            et_bg = GradientDrawable()
            et_bg.setShape(GradientDrawable.RECTANGLE)
            et_bg.setCornerRadius(float(dp(8)))
            et_bg.setColor(c(0x18FFFFFF if dark else 0x0A000000))
            et_bg.setStroke(dp(1), c(0x3038BDF8 if dark else 0x20000000))
            input_et.setBackground(et_bg)
            input_et.setPadding(dp(12), dp(10), dp(12), dp(10))

            builder.set_view(input_et)
        except Exception as e:
            self._log_error(f"Input view err: {e}")

        def on_add(d, w):
            if not input_et:
                return
            raw = str(input_et.getText()).strip()
            if not raw:
                return
            clean = raw.replace("@", "").strip()
            if clean.isdigit():
                uid_int = int(clean)
                self._add_user_by_id(uid_int, f"ID: {uid_int}")
            else:
                self._resolve_and_add_username(clean)

        builder.set_positive_button("Добавить" if is_ru else "Add", on_add)
        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def _resolve_and_add_username(self, username: str):
        try:
            found_user = None
            mc = MessagesController.getInstance(UserConfig.selectedAccount)
            found_user = mc.getUser(username)
            if not found_user:
                found_user = mc.getUserOrChat(username)

            if found_user and hasattr(found_user, "id"):
                first = getattr(found_user, "first_name", "") or ""
                last = getattr(found_user, "last_name", "") or ""
                full = f"{first} {last}".strip() or f"@{username}"
                self._add_user_by_id(int(found_user.id), full)
                return
        except Exception as e:
            self._log_error(f"Resolve username err: {e}")

        BulletinHelper.show_info(f"Поиск @{username}... Если пользователь не найден в кэше, откройте диалог с ним.")

    def _add_user_by_id(self, uid_int: int, fallback_name: str):
        user_id = str(uid_int)
        name = fallback_name
        try:
            user = MessagesController.getInstance(UserConfig.selectedAccount).getUser(uid_int)
            if user:
                first = getattr(user, "first_name", "") or ""
                last = getattr(user, "last_name", "") or ""
                full = f"{first} {last}".strip()
                if full:
                    name = full
        except Exception:
            pass

        with self._data_lock:
            if user_id in self.tracked_users:
                BulletinHelper.show_error(f"{name} уже в списке")
                return
            self.tracked_users[user_id] = {
                "name": name,
                "history": [],
                "sessions_log": [],
                "last_ts": 0,
                "last_text": "",
                "last_type": "",
                "session_start_ts": 0,
                "first_name": name,
                "activity_hours": [0] * 24,
                "total_online_time": 0,
                "total_reads": 0,
                "notifications_enabled": True,
                "has_unread_out": False,
                "last_out_msg_ts": 0,
                "ignored_online_count": 0,
                "last_read_outbox_ts": 0,
                "loyalty_ignored": 0,
                "loyalty_replied": 0,
                "custom_tag": "",
                "media_stats": {},
                "is_pinned": False,
                "local_name": ""
            }
        self._save_users()
        BulletinHelper.show_success(f"{name} добавлен в мониторинг")

    def show_today_summary_dialog(self):
        fragment = get_last_fragment()
        if not fragment or not fragment.getParentActivity():
            return
        ctx = fragment.getParentActivity()

        with self._data_lock:
            users_copy = list(self.tracked_users.items())

        now_str = datetime.now().strftime("%d.%m.%Y")
        total_online_all = 0
        total_events_all = 0
        active_users = []

        for uid, udata in users_copy:
            tot = udata.get("total_online_time", 0)
            total_online_all += tot
            evs = [e for e in udata.get("history", []) if e.get("date") == now_str]
            total_events_all += len(evs)
            name = self.get_display_name(uid, udata)
            st = "В сети" if udata.get("last_type") == "online" else "Оффлайн"
            dur_str = self.format_duration(tot)
            active_users.append((name, st, dur_str, tot, len(evs)))

        builder = AlertDialogBuilder(ctx)
        builder.set_title("Сводка активности")

        dark = self._is_dark_theme() if hasattr(self, "_is_dark_theme") else True

        try:
            from android.view import Gravity, View
            from android.widget import FrameLayout, LinearLayout, ScrollView, TextView
            from android.graphics.drawable import GradientDrawable
            from android.graphics import Typeface
            from org.telegram.messenger import AndroidUtilities

            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            scroll = ScrollView(ctx)
            scroll.setVerticalScrollBarEnabled(False)
            scroll.setPadding(dp(18), dp(10), dp(18), dp(10))

            root = LinearLayout(ctx)
            root.setOrientation(LinearLayout.VERTICAL)

            d_chip = TextView(ctx)
            d_chip.setText(f"Данные за сегодня • {now_str}")
            d_chip.setTextSize(1, 11.5)
            d_chip.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
            root.addView(d_chip)

            stat_row = LinearLayout(ctx)
            stat_row.setOrientation(LinearLayout.HORIZONTAL)
            sr_lp = LinearLayout.LayoutParams(-1, -2)
            sr_lp.topMargin = dp(10)
            sr_lp.bottomMargin = dp(14)

            cols = [
                ("КОНТРОЛЬ", str(len(users_copy)), c(0xFF38BDF8)),
                ("В СЕТИ", self.format_duration(total_online_all), c(0xFF10B981)),
                ("СОБЫТИЙ", str(total_events_all), c(0xFFF59E0B))
            ]

            for i, (lbl, val, col_text) in enumerate(cols):
                card = LinearLayout(ctx)
                card.setOrientation(LinearLayout.VERTICAL)
                card.setGravity(Gravity.CENTER)
                c_bg = GradientDrawable()
                c_bg.setCornerRadius(float(dp(10)))
                c_bg.setColor(c(0x221E293B if dark else 0x08000000))
                c_bg.setStroke(dp(1), c(0x3038BDF8 if dark else 0x15000000))
                card.setBackground(c_bg)
                card.setPadding(dp(4), dp(8), dp(4), dp(8))

                val_tv = TextView(ctx)
                val_tv.setText(val)
                val_tv.setTextSize(1, 13.5)
                val_tv.setTextColor(col_text)
                try: val_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                card.addView(val_tv)

                lbl_tv = TextView(ctx)
                lbl_tv.setText(lbl)
                lbl_tv.setTextSize(1, 8.5)
                lbl_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                l_lp = LinearLayout.LayoutParams(-2, -2)
                l_lp.topMargin = dp(2)
                card.addView(lbl_tv, l_lp)

                c_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                if i > 0:
                    c_lp.leftMargin = dp(6)
                stat_row.addView(card, c_lp)

            root.addView(stat_row, sr_lp)

            sec_tv = TextView(ctx)
            sec_tv.setText("ТОП ПО ВРЕМЕНИ ОНЛАЙНА")
            sec_tv.setTextSize(1, 11.0)
            sec_tv.setTextColor(c(0xFF38BDF8 if dark else 0xFF0284C7))
            try: sec_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception: pass
            root.addView(sec_tv)

            active_users.sort(key=lambda x: x[3], reverse=True)
            max_online = active_users[0][3] if active_users and active_users[0][3] > 0 else 1

            if not active_users:
                emp_tv = TextView(ctx)
                emp_tv.setText("Нет отслеживаемых контактов")
                emp_tv.setTextSize(1, 12.5)
                emp_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                emp_lp = LinearLayout.LayoutParams(-2, -2)
                emp_lp.topMargin = dp(8)
                root.addView(emp_tv, emp_lp)
            else:
                for rank, (name, st, dur_str, tot, ev_count) in enumerate(active_users[:8], start=1):
                    item_card = LinearLayout(ctx)
                    item_card.setOrientation(LinearLayout.VERTICAL)
                    ic_bg = GradientDrawable()
                    ic_bg.setCornerRadius(float(dp(8)))
                    ic_bg.setColor(c(0x18FFFFFF if dark else 0x06000000))
                    item_card.setBackground(ic_bg)
                    item_card.setPadding(dp(10), dp(7), dp(10), dp(7))

                    row_top = LinearLayout(ctx)
                    row_top.setOrientation(LinearLayout.HORIZONTAL)
                    row_top.setGravity(Gravity.CENTER_VERTICAL)

                    rank_tv = TextView(ctx)
                    rank_tv.setText(f"#{rank}")
                    rank_tv.setTextSize(1, 11.0)
                    rank_tv.setTextColor(c(0xFF38BDF8 if rank <= 3 else (0xFF94A3B8 if dark else 0xFF64748B)))
                    try: rank_tv.setTypeface(Typeface.DEFAULT_BOLD)
                    except Exception: pass
                    row_top.addView(rank_tv, LinearLayout.LayoutParams(-2, -2))

                    name_tv = TextView(ctx)
                    clean_name = name.replace("®", "").strip()
                    name_tv.setText(clean_name)
                    name_tv.setTextSize(1, 12.5)
                    name_tv.setTextColor(c(0xFFF8FAFC if dark else 0xFF0F172A))
                    try: name_tv.setTypeface(Typeface.DEFAULT_BOLD)
                    except Exception: pass
                    n_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                    n_lp.leftMargin = dp(8)
                    n_lp.rightMargin = dp(8)
                    row_top.addView(name_tv, n_lp)

                    dur_tv = TextView(ctx)
                    dur_tv.setText(dur_str)
                    dur_tv.setTextSize(1, 12.0)
                    dur_tv.setTextColor(c(0xFF10B981 if st == "В сети" else (0xFF94A3B8 if dark else 0xFF64748B)))
                    try: dur_tv.setTypeface(Typeface.DEFAULT_BOLD)
                    except Exception: pass
                    row_top.addView(dur_tv, LinearLayout.LayoutParams(-2, -2))

                    item_card.addView(row_top, LinearLayout.LayoutParams(-1, -2))

                    progress_track = FrameLayout(ctx)
                    pt_bg = GradientDrawable()
                    pt_bg.setCornerRadius(float(dp(2)))
                    pt_bg.setColor(c(0x20FFFFFF if dark else 0x10000000))
                    progress_track.setBackground(pt_bg)

                    progress_fill = View(ctx)
                    pf_bg = GradientDrawable()
                    pf_bg.setCornerRadius(float(dp(2)))
                    pf_bg.setColor(c(0xFF38BDF8 if rank <= 3 else 0xFF64748B))
                    progress_fill.setBackground(pf_bg)

                    ratio = max(0.04, min(1.0, float(tot) / float(max_online)))
                    pt_lp = LinearLayout.LayoutParams(-1, dp(3))
                    pt_lp.topMargin = dp(5)
                    progress_track.addView(progress_fill, FrameLayout.LayoutParams(int(dp(200) * ratio), -1))
                    item_card.addView(progress_track, pt_lp)

                    ic_lp = LinearLayout.LayoutParams(-1, -2)
                    ic_lp.topMargin = dp(6)
                    root.addView(item_card, ic_lp)

            scroll.addView(root, FrameLayout.LayoutParams(-1, -2))
            builder.set_view(scroll)
        except Exception as e:
            self._log_error(f"Summary view error: {e}")
            lines = [f"СВОДКА АКТИВНОСТИ ({now_str})", "──────────────────────"]
            lines.append(f"Всего на контроле: {len(users_copy)}")
            lines.append(f"Суммарно в сети: {self.format_duration(total_online_all)}")
            lines.append(f"Событий за сегодня: {total_events_all}")
            for rank, (name, st, dur_str, _, _) in enumerate(active_users[:8], start=1):
                lines.append(f"#{rank} {name}: {dur_str} [{st}]")
            builder.set_message("\n".join(lines))

        builder.set_positive_button("Закрыть", lambda d, w: None)
        builder.show()

    def show_today_summary(self):
        return self.show_today_summary_dialog()

    def _get_my_id(self, account: int = None) -> int:
        try:
            acc = account if account is not None else UserConfig.selectedAccount
            return UserConfig.getInstance(acc).getClientUserId()
        except Exception:
            return UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId()

    def open_tg_link(self, domain: str):
        try:
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(f"tg://resolve?domain={domain}"))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ApplicationLoader.applicationContext.startActivity(intent)
        except Exception as e:
            self._log_error(f"open_tg_link err: {e}")

    def factory_reset(self, view):
        fragment = get_last_fragment()
        if not fragment:
            return

        ctx = fragment.getParentActivity()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title(T("reset_title"))
        builder.set_message(T("reset_msg"))

        def on_confirm(dialog, which):
            with self._data_lock:
                self.tracked_users = {}
            self._save_users_sync()

            if hasattr(self, "users_file") and os.path.exists(self.users_file):
                try:
                    os.remove(self.users_file)
                except OSError as e:
                    self._log_error(f"Remove file err: {e}")

            try:
                backup_dir = os.path.join(get_documents_dir(), "Omniscient")
                if os.path.exists(backup_dir):
                    for f in os.listdir(backup_dir):
                        f_path = os.path.join(backup_dir, f)
                        if os.path.isfile(f_path):
                            os.remove(f_path)
            except Exception as e:
                self._log_error(f"Failed to delete backups: {e}")

            try:
                ctx_app = self._get_app_context()
                if ctx_app:
                    cache_dir = str(ctx_app.getExternalCacheDir().getAbsolutePath())
                    if os.path.exists(cache_dir):
                        for f in os.listdir(cache_dir):
                            if f.startswith("omnianalytics_") or f.startswith("omniscient_logs_"):
                                try:
                                    os.remove(os.path.join(cache_dir, f))
                                except OSError as e:
                                    self._log_error(f"Delete cache err: {e}")
            except Exception as e:
                self._log_error(f"Cache cleanup err: {e}")

            defaults = {
                "master_track": True,
                "track_online": True,
                "track_read": True,
                "track_name": True,
                "track_typing": True,
                "keep_alive_wakelock": False,
                "master_notify": True,
                "notify_system": True,
                "notify_in_app": True,
                "notify_hyperbridge": False,
                "notify_online": True,
                "notify_offline": True,
                "notify_read": True,
                "notify_name": True,
                "max_logs": "400",
                "auto_clean_days": "7",
                "last_clean_ts": 0,
                "auto_backup_enabled": False,
                "auto_backup_days": "7",
                "last_backup_ts": 0
            }

            for k, v in defaults.items():
                setattr(self, k, v)
                self.set_setting(k, v, reload_settings=False)

            self._release_wakelock()
            BulletinHelper.show_success(T("reset_success"))

            if fragment:
                fragment.finishFragment()

        builder.set_positive_button(T("btn_delete_all"), on_confirm)
        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def run_auto_backup(self, force=False, account: int = None):
        if not force and not getattr(self, "auto_backup_enabled", False):
            return

        now_ts = time.time()
        last_backup = getattr(self, "last_backup_ts", 0)

        try:
            days = int(getattr(self, "auto_backup_days", 7))
        except ValueError:
            days = 7

        if not force and (days <= 0 or (now_ts - last_backup <= (days * 86400))):
            return

        self.last_backup_ts = now_ts
        self.set_setting("last_backup_ts", self.last_backup_ts, reload_settings=False)

        def backup_task():
            try:
                backup_data = {
                    "tracked_users": self._get_safe_users(),
                    "settings": {
                        "master_track": getattr(self, "master_track", True),
                        "track_online": getattr(self, "track_online", True),
                        "track_read": getattr(self, "track_read", True),
                        "track_name": getattr(self, "track_name", True)
                    }
                }

                encrypted_payload = self._encrypt_data(backup_data)

                backup_dir = os.path.join(get_documents_dir(), "Omniscient")
                os.makedirs(backup_dir, exist_ok=True)

                file_name = f"autobackup_{int(time.time())}.omni"
                file_path = os.path.join(backup_dir, file_name)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(encrypted_payload)

                try:
                    files = [os.path.join(backup_dir, f_name) for f_name in os.listdir(backup_dir) if f_name.startswith("autobackup_") and f_name.endswith(".omni")]
                    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    if len(files) > 25:
                        for f_to_delete in files[25:]:
                            os.remove(f_to_delete)
                except Exception as e:
                    self._log_error(f"Backup cleanup err: {e}")

                my_id = self._get_my_id(account)
                send_text(my_id, T("backup_success").format(path=file_path))

                self.last_backup_ts = time.time()
                self.set_setting("last_backup_ts", self.last_backup_ts, reload_settings=False)

                if force:
                    BulletinHelper.show_success(T("test_backup_done"))
            except Exception as e:
                err_msg = f"Exception: {str(e)}"
                self._log_error(f"Auto-backup err: {err_msg}")
                if force:
                    BulletinHelper.show_error(T("backup_error"))

        threading.Thread(target=backup_task, daemon=True).start()

    def force_test_backup(self, view):
        self.run_auto_backup(force=True)

    def run_auto_clean(self):
        try:
            days = int(getattr(self, "auto_clean_days", 7))
        except ValueError:
            days = 7

        if days <= 0:
            return

        cutoff_ts = time.time() - (days * 86400)
        changed = False

        with self._data_lock:
            for uid, data in list(self.tracked_users.items()):
                history = data.get("history", [])
                new_history = [e for e in history if e.get("ts", 0) > cutoff_ts]
                if len(new_history) != len(history):
                    data["history"] = new_history
                    changed = True

        if changed:
            self._save_users()

    def _init_storage(self):
        self.data_dir = self._get_data_dir()
        self.users_file = os.path.join(self.data_dir, "tracked_users.json")
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_encryption_key(self, force_fallback=False):
        if not force_fallback and hasattr(self, '_cached_enc_key') and self._cached_enc_key:
            return self._cached_enc_key
        android_id = ""
        if not force_fallback:
            try:
                Settings = jclass("android.provider.Settings")
                ctx = self._get_app_context()
                if not ctx:
                    from org.telegram.messenger import ApplicationLoader
                    ctx = ApplicationLoader.applicationContext if ApplicationLoader else None
                if ctx and hasattr(ctx, "getContentResolver"):
                    android_id = Settings.Secure.getString(ctx.getContentResolver(), Settings.Secure.ANDROID_ID)
            except Exception:
                android_id = ""
        if not android_id:
            android_id = "omni_fallback_secure_key_99"
        salt = b"OmniAnalytics_v2_Salt_8492"
        key = hashlib.pbkdf2_hmac('sha256', android_id.encode('utf-8'), salt, 10000)
        if not force_fallback and android_id != "omni_fallback_secure_key_99":
            self._cached_enc_key = key
        return key

    def _encrypt_data(self, data: dict) -> str:
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            key = self._get_encryption_key(force_fallback=False)
            data_mac = hmac.new(key, json_str.encode('utf-8'), hashlib.sha256).hexdigest()
            payload = f"{data_mac}::{json_str}"
            Cipher = jclass("javax.crypto.Cipher")
            SecretKeySpec = jclass("javax.crypto.spec.SecretKeySpec")
            IvParameterSpec = jclass("javax.crypto.spec.IvParameterSpec")
            Base64_Android = jclass("android.util.Base64")
            String = jclass("java.lang.String")
            secret_key = SecretKeySpec(key, "AES")
            iv_bytes = os.urandom(16)
            iv_spec = IvParameterSpec(iv_bytes)
            cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
            cipher.init(Cipher.ENCRYPT_MODE, secret_key, iv_spec)
            encrypted_bytes = cipher.doFinal(String(payload).getBytes("UTF-8"))
            enc_str = Base64_Android.encodeToString(encrypted_bytes, 2)
            iv_str = base64.b64encode(iv_bytes).decode('utf-8')
            return f"SEC::{iv_str}::{enc_str}"
        except Exception as e:
            self._log_error(f"Encryption err: {e}")
            payload = json.dumps(data, ensure_ascii=False)
            data_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            full_payload = f"{data_hash}::{payload}"
            return "B64:" + base64.b64encode(full_payload.encode('utf-8')).decode('utf-8')

    def _try_decrypt_payload(self, data_str: str, key: bytes) -> dict:
        if not data_str:
            return None
        payload = ""
        if data_str.startswith("B64:"):
            try:
                payload = base64.b64decode(data_str[4:]).decode('utf-8')
            except Exception:
                return None
        elif data_str.startswith("SEC::"):
            try:
                parts = data_str.split("::")
                if len(parts) != 3:
                    return None
                iv_bytes = base64.b64decode(parts[1])
                enc_str = parts[2]
                Cipher = jclass("javax.crypto.Cipher")
                SecretKeySpec = jclass("javax.crypto.spec.SecretKeySpec")
                IvParameterSpec = jclass("javax.crypto.spec.IvParameterSpec")
                Base64_Android = jclass("android.util.Base64")
                String = jclass("java.lang.String")
                secret_key = SecretKeySpec(key, "AES")
                iv_spec = IvParameterSpec(iv_bytes)
                cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
                cipher.init(Cipher.DECRYPT_MODE, secret_key, iv_spec)
                decoded_bytes = Base64_Android.decode(enc_str, 2)
                decrypted_bytes = cipher.doFinal(decoded_bytes)
                payload = str(String(decrypted_bytes, "UTF-8"))
            except Exception:
                return None
        else:
            try:
                Cipher = jclass("javax.crypto.Cipher")
                SecretKeySpec = jclass("javax.crypto.spec.SecretKeySpec")
                IvParameterSpec = jclass("javax.crypto.spec.IvParameterSpec")
                Base64_Android = jclass("android.util.Base64")
                String = jclass("java.lang.String")
                cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
                cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), IvParameterSpec(b"OmniSecureInitIV"))
                decoded_bytes = Base64_Android.decode(data_str, 2)
                decrypted_bytes = cipher.doFinal(decoded_bytes)
                payload = str(String(decrypted_bytes, "UTF-8"))
            except Exception:
                return None
        try:
            if not payload or "::" not in payload:
                return None
            file_mac, json_str = payload.split("::", 1)
            expected_mac = hmac.new(key, json_str.encode('utf-8'), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(file_mac, expected_mac):
                old_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
                if not hmac.compare_digest(file_mac, old_hash):
                    return None
            return json.loads(json_str)
        except Exception:
            return None

    def _decrypt_data(self, data_str: str) -> dict:
        if not data_str:
            return None
        keys = [self._get_encryption_key(force_fallback=False)]
        fb = self._get_encryption_key(force_fallback=True)
        if fb not in keys:
            keys.append(fb)
        for k in keys:
            res = self._try_decrypt_payload(data_str, k)
            if res is not None:
                return res
        return None

    def _get_data_dir(self):
        ctx = self._get_app_context()
        if ctx and hasattr(ctx, "getFilesDir") and ctx.getFilesDir():
            try:
                base_dir = str(ctx.getFilesDir().getAbsolutePath())
                path = os.path.join(base_dir, "omnianalytics_secure")
                os.makedirs(path, exist_ok=True)
                return path
            except Exception:
                pass
        try:
            from org.telegram.messenger import ApplicationLoader
            if ApplicationLoader is not None:
                if ApplicationLoader.applicationContext:
                    base_dir = str(ApplicationLoader.applicationContext.getFilesDir().getAbsolutePath())
                    path = os.path.join(base_dir, "omnianalytics_secure")
                    os.makedirs(path, exist_ok=True)
                    return path
                if hasattr(ApplicationLoader, "getFilesDirFixed"):
                    base_dir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
                    path = os.path.join(base_dir, "omnianalytics_secure")
                    os.makedirs(path, exist_ok=True)
                    return path
        except Exception:
            pass
        return ""

    def _get_safe_users(self) -> dict:
        with self._data_lock:
            try:
                return copy.deepcopy(self.tracked_users)
            except Exception:
                return {}

    def _load_users(self):
        if not self.data_dir:
            self.data_dir = self._get_data_dir()
            if not self.data_dir:
                with self._data_lock:
                    self.tracked_users = {}
                return
            self.users_file = os.path.join(self.data_dir, "tracked_users.json")

        loaded = None

        if os.path.exists(self.users_file) and os.path.getsize(self.users_file) > 5:
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    loaded = self._decrypt_data(content)
            except Exception as e:
                self._log_error(f"Read main users_file err: {e}")

        if loaded is None and os.path.exists(self.data_dir):
            try:
                baks = [
                    os.path.join(self.data_dir, fn)
                    for fn in os.listdir(self.data_dir)
                    if fn.startswith("tracked_users.json.bak_")
                ]
                baks.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                for b_path in baks:
                    try:
                        if os.path.getsize(b_path) < 5:
                            continue
                        with open(b_path, 'r', encoding='utf-8') as f:
                            b_content = f.read().strip()
                        if b_content:
                            dec = self._decrypt_data(b_content)
                            if dec and isinstance(dec, dict) and len(dec) > 0:
                                loaded = dec
                                self._log_error(f"Auto-recovered users from: {b_path}")
                                break
                    except Exception:
                        pass
            except Exception as e:
                self._log_error(f"Bak scan err: {e}")

        if loaded is None:
            try:
                old_data = self.get_setting("tracked_users", {})
                if old_data and isinstance(old_data, dict):
                    loaded = old_data
            except Exception:
                pass

        with self._data_lock:
            if loaded and isinstance(loaded, dict):
                self.tracked_users = loaded
                self._save_users_sync()
            else:
                if not hasattr(self, 'tracked_users') or self.tracked_users is None:
                    self.tracked_users = {}

    def _save_users(self):
        if not self.data_dir:
            return
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            def _write_to_disk():
                data_to_save = self._get_safe_users()
                if data_to_save is None:
                    return
                if len(data_to_save) == 0 and os.path.exists(self.users_file) and os.path.getsize(self.users_file) > 100:
                    if not getattr(self, '_allow_empty_reset', False):
                        return
                try:
                    encrypted_data = self._encrypt_data(data_to_save)
                    tmp_file = self.users_file + ".tmp"
                    with self._file_lock:
                        with open(tmp_file, 'w', encoding='utf-8') as f:
                            f.write(encrypted_data)
                        if os.path.exists(tmp_file):
                            os.replace(tmp_file, self.users_file)
                except Exception as e:
                    self._log_error(f"Save error: {e}")
            self._save_timer = threading.Timer(0.5, _write_to_disk)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _save_users_sync(self):
        if not self.data_dir:
            return
        try:
            data_to_save = self._get_safe_users()
            if data_to_save is None:
                return
            if len(data_to_save) == 0 and os.path.exists(self.users_file) and os.path.getsize(self.users_file) > 100:
                if not getattr(self, '_allow_empty_reset', False):
                    return
            encrypted_data = self._encrypt_data(data_to_save)
            tmp_file = self.users_file + ".tmp"
            with self._file_lock:
                with open(tmp_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted_data)
                if os.path.exists(tmp_file):
                    os.replace(tmp_file, self.users_file)
        except Exception as e:
            self._log_error(f"Sync save error: {e}")

    def _get_app_context(self):
        return ApplicationLoader.applicationContext

    def _acquire_wakelock(self):
        try:
            ctx = self._get_app_context()
            if not ctx:
                return
            pm = ctx.getSystemService(Context.POWER_SERVICE)
            if not getattr(self, 'wake_lock', None):
                PowerManager = jclass("android.os.PowerManager")
                self.wake_lock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Omniscient::KeepAlive")
                self.wake_lock.setReferenceCounted(False)
            if not self.wake_lock.isHeld():
                self.wake_lock.acquire()
        except Exception as e:
            self._log_error(f"WakeLock acquire error: {e}")

    def _release_wakelock(self):
        try:
            if getattr(self, 'wake_lock', None) and self.wake_lock.isHeld():
                self.wake_lock.release()
        except Exception as e:
            self._log_error(f"WakeLock release error: {e}")

    def _init_notification_channel(self):
        try:
            if Build.VERSION.SDK_INT >= Build.VERSION_CODES.O:
                ctx = self._get_app_context()
                if not ctx:
                    return
                nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE)
                ch_id = "omniscient_alerts_channel"
                if nm.getNotificationChannel(ch_id) is None:
                    ch = NotificationChannel(ch_id, "Omniscient Notifications", NotificationManager.IMPORTANCE_HIGH)
                    ch.setShowBadge(True)
                    ch.enableVibration(True)
                    try:
                        ch.enableLights(True)
                    except Exception:
                        pass
                    nm.createNotificationChannel(ch)
        except Exception as e:
            self._log_error(f"Init notification channel err: {e}")

    def send_system_notification(self, title: str, text: str, is_call: bool = False):
        try:

            is_paused = getattr(ApplicationLoader, "mainInterfacePaused", True)
            if not is_paused and getattr(self, "notify_in_app", True):
                try:
                    BulletinHelper.show_info(f"{title}\n{text}")
                except Exception:
                    pass

            if not getattr(self, "notify_system", True):
                return

            ctx = self._get_app_context()
            if not ctx:
                return
            nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE)
            if not nm:
                return
            ch_id = "omniscient_alerts_channel"
            if Build.VERSION.SDK_INT >= Build.VERSION_CODES.O:
                if nm.getNotificationChannel(ch_id) is None:
                    self._init_notification_channel()
                builder = Notification.Builder(ctx, ch_id)
            else:
                builder = Notification.Builder(ctx)
                try:
                    builder.setPriority(Notification.PRIORITY_MAX)
                except Exception:
                    pass

            builder.setContentTitle(title)
            builder.setContentText(text)
            try:
                builder.setDefaults(Notification.DEFAULT_ALL)
            except Exception:
                pass

            try:
                icon_id = ctx.getApplicationInfo().icon
                builder.setSmallIcon(icon_id)
            except Exception:
                pass

            if is_call:
                builder.setCategory(getattr(Notification, "CATEGORY_CALL", "call"))
            else:
                builder.setCategory(getattr(Notification, "CATEGORY_MESSAGE", "msg"))

            builder.setAutoCancel(True)
            try:
                PendingIntent = jclass("android.app.PendingIntent")
                launch_intent = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName())
                if launch_intent:
                    flag_immutable = 67108864 if Build.VERSION.SDK_INT >= 31 else 0
                    pi = PendingIntent.getActivity(ctx, 0, launch_intent, 134217728 | flag_immutable)
                    builder.setContentIntent(pi)
            except Exception:
                pass

            nid = abs(hash(title + text + str(time.time()))) % 100000
            nm.notify(nid, builder.build())
        except Exception as e:
            self._log_error(f"Send notification err: {e}")

    def complete_onboarding(self):
        self.set_setting("onboarding_completed", True, reload_settings=True)
        try:
            current_fragment = get_last_fragment()
            ctx = current_fragment.getParentActivity() if current_fragment else None
            if ctx and OmniWelcomeUI and hasattr(OmniWelcomeUI, "show_quick_start_sheet"):
                OmniWelcomeUI.show_quick_start_sheet(self, ctx)
        except Exception as e:
            self._log_error(f"complete_onboarding err: {e}")

    def reset_onboarding(self):
        self.set_setting("onboarding_completed", False, reload_settings=True)

    def _log_error(self, message: str):
        if not hasattr(self, 'error_logs'):
            self.error_logs = []
        log_str = f"[{time.strftime('%H:%M:%S')}] {message}"
        self.error_logs.append(log_str)
        if len(self.error_logs) > 50:
            self.error_logs.pop(0)

    def _copy_logs(self, *args):
        self.copy_text("\n".join(self.error_logs), T("logs_copied"))

    def _init_profile_hooks(self):
        pass

    def _get_cached_field(self, clazz, name):
        if not hasattr(self, '_field_cache'):
            self._field_cache = {}
        cache_key = f"{clazz.getName()}_{name}"
        if cache_key in self._field_cache:
            return self._field_cache[cache_key]

        current_class = clazz
        while current_class is not None:
            try:
                field = current_class.getDeclaredField(name)
                field.setAccessible(True)
                self._field_cache[cache_key] = field
                return field
            except Exception:
                current_class = current_class.getSuperclass()
        self._field_cache[cache_key] = None
        return None

    def _get_long_field(self, obj, name):
        if obj is None:
            return 0
        field = self._get_cached_field(obj.getClass(), name)
        if field:
            try:
                return field.getLong(obj)
            except Exception as e:
                self._log_error(f"Failed getLong {name}: {e}")
        return 0

    def _get_int_field(self, obj, name):
        if obj is None:
            return -1
        field = self._get_cached_field(obj.getClass(), name)
        if field:
            try:
                return field.getInt(obj)
            except Exception as e:
                self._log_error(f"Failed getInt {name}: {e}")
        return -1

    def _set_int_field(self, obj, name, value):
        if obj is None:
            return
        field = self._get_cached_field(obj.getClass(), name)
        if field:
            try:
                field.setInt(obj, value)
            except Exception as e:
                self._log_error(f"Failed setInt {name}: {e}")

    def _get_activity_from_adapter(self, adapter):
        try:
            field = adapter.getClass().getDeclaredField("this$0")
            field.setAccessible(True)
            return field.get(adapter)
        except Exception:
            return None

    def _shift_rows(self, activity, insert_pos):
        row_count = self._get_int_field(activity, "rowCount")
        if row_count != -1:
            self._set_int_field(activity, "rowCount", row_count + 1)
        try:
            if not hasattr(self, '_cached_integer'):
                self._cached_integer = jclass("java.lang.Integer")
            INTEGER_CLASS = self._cached_integer

            for field in activity.getClass().getDeclaredFields():
                name = field.getName()
                if "Row" not in name and "row" not in name:
                    continue
                if name in ("rowCount", "phoneRow", "mutualRow", "omniRow"):
                    continue

                field_type = field.getType()
                if field_type != INTEGER_CLASS.TYPE and field_type != INTEGER_CLASS:
                    continue

                field.setAccessible(True)
                val_obj = field.get(activity)
                if val_obj is None:
                    continue

                if not hasattr(val_obj, "intValue") and not isinstance(val_obj, int):
                    continue
                val = int(val_obj)

                if val >= insert_pos and val != -1:
                    try:
                        if field_type == INTEGER_CLASS.TYPE:
                            field.setInt(activity, val + 1)
                        else:
                            field.set(activity, INTEGER_CLASS(val + 1))
                    except Exception as e:
                        self._log_error(f"Failed to shift row {name}: {e}")
        except Exception as e:
            self._log_error(f"Row shift err: {e}")

    def _calculate_insert_position(self, activity):
        for name in PROFILE_ANCHOR_ROWS:
            val = self._get_int_field(activity, name)
            if val != -1:
                return val + 1
        info_end = self._get_int_field(activity, "infoEndRow")
        if info_end != -1:
            return info_end + 1
        return -1

    def _init_import_hook(self):
        try:
            JavaClass = jclass("java.lang.Class")
            base_fragment_class = JavaClass.forName("org.telegram.ui.ActionBar.BaseFragment")
            int_type = jclass("java.lang.Integer").TYPE
            intent_class = JavaClass.forName("android.content.Intent")

            m = base_fragment_class.getDeclaredMethod("onActivityResultFragment", int_type, int_type, intent_class)
            m.setAccessible(True)
            self.hook_method(m, ImportResultHook(self))
        except Exception as e:
            self._log_error(f"Init import hook err: {e}")

    def _record_plugin_restart(self) -> bool:
        now_ts = time.time()
        changed = False
        if not hasattr(self, "tracked_users"):
            return False

        with self._data_lock:
            for uid, data in list(self.tracked_users.items()):
                session_start = data.get("session_start_ts", 0)
                if session_start > 0 or data.get("last_type") == "online":
                    if session_start == 0:
                        session_start = data.get("last_ts", 0)

                    data["last_type"] = "offline"
                    data["last_text"] = T("plugin_restarted")
                    data["session_start_ts"] = 0
                    if session_start > 0:
                        duration = now_ts - session_start
                        start_str = datetime.fromtimestamp(session_start).strftime("%H:%M:%S")
                        time_str = datetime.fromtimestamp(now_ts).strftime("%H:%M:%S")
                        dur_str = self.format_duration(duration)
                        sessions = data.setdefault("sessions_log", [])
                        sessions.append(f"🟢 {start_str} - 🔴 {time_str} ({dur_str}) [!]")

                        history = data.setdefault("history", [])
                        history.append({
                            "date": datetime.fromtimestamp(now_ts).strftime("%d.%m.%Y"),
                            "time": time_str,
                            "icon": "🔌",
                            "text": T("plugin_restarted"),
                            "type": "offline",
                            "ts": now_ts
                        })
                    changed = True
        return changed

    def on_plugin_unload(self):
        with self._save_lock:
            if getattr(self, '_save_timer', None):
                self._save_timer.cancel()
        self._release_wakelock()
        if self._record_plugin_restart():
            self._save_users_sync()

    def _get_bool(self, key: str, default: bool) -> bool:
        val = self.get_setting(key, default)
        if isinstance(val, str):
            return val.lower() == "true"
        return bool(val)

    def get_lang_code(self) -> str:
        try:
            pref = str(self.get_setting("app_language", "auto")).lower()
            if pref in ("ru", "en"):
                return pref
        except Exception:
            pass
        return get_lang()

    def on_plugin_load(self):
        global _active_plugin_ref, LANG
        _active_plugin_ref = weakref.ref(self)
        LANG = self.get_lang_code()

        self._file_lock = threading.Lock()
        self._save_lock = threading.Lock()
        self._save_timer = None
        self._data_lock = threading.RLock()
        self._last_maintenance_check = 0
        self.error_logs = []
        self.version_taps = 0
        self.omni_profile_state = {}
        self.__version__ = __version__
        self.__id__ = __id__

        self._init_storage()
        self._load_users()

        if self._record_plugin_restart():
            self._save_users()

        self._init_import_hook()
        self._init_notification_channel()

        self.master_track = self._get_bool("master_track", True)
        self.track_online = self._get_bool("track_online", True)
        self.track_read = self._get_bool("track_read", True)
        self.track_name = self._get_bool("track_name", True)
        self.track_typing = self._get_bool("track_typing", True)

        self.keep_alive_wakelock = self._get_bool("keep_alive_wakelock", False)
        if self.keep_alive_wakelock:
            self._acquire_wakelock()

        self.master_notify = self._get_bool("master_notify", True)
        self.notify_system = self._get_bool("notify_system", True)
        self.notify_in_app = self._get_bool("notify_in_app", True)
        self.notify_hyperbridge = self._get_bool("notify_hyperbridge", False)
        self.notify_online = self._get_bool("notify_online", True)
        self.notify_offline = self._get_bool("notify_offline", True)
        self.notify_read = self._get_bool("notify_read", True)
        self.notify_name = self._get_bool("notify_name", True)
        self.show_profile_tracker = self._get_bool("show_profile_tracker", True)

        self.max_logs = str(self.get_setting("max_logs", "500"))
        self.auto_clean_days = str(self.get_setting("auto_clean_days", "7"))
        self.last_clean_ts = self.get_setting("last_clean_ts", 0)

        self.auto_backup_enabled = self._get_bool("auto_backup_enabled", False)
        self.card_caption_enabled = self._get_bool("card_caption_enabled", True)
        self.card_theme = str(self.get_setting("card_theme", "dark"))
        self.custom_card_bg = str(self.get_setting("custom_card_bg", ""))

        app_lang = str(self.get_setting("app_language", "auto")).lower()
        if app_lang == "ru":
            LANG = "ru"
        elif app_lang == "en":
            LANG = "en"
        else:
            LANG = get_lang()

        if self._get_bool("auto_check_updates", True):
            def _bg_upd_check():
                time.sleep(3)
                try:
                    from loader import OmniGitHubLoader
                    OmniGitHubLoader.check_for_updates(self, None, notify_if_latest=False)
                except Exception:
                    pass
            threading.Thread(target=_bg_upd_check, daemon=True).start()
        self.auto_backup_days = str(self.get_setting("auto_backup_days", "7"))
        self.last_backup_ts = self.get_setting("last_backup_ts", 0)

        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.PROFILE_ACTION_MENU,
                text=T("add_remove"),
                subtext=T("click_to_track_short"),
                on_click=self.toggle_tracking,
                icon="msg_openprofile",
                priority=100
            )
        )

        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.CHAT_ACTION_MENU,
                text=T("add_remove"),
                subtext=T("click_to_track_short"),
                on_click=self.toggle_tracking,
                icon="msg_openprofile",
                priority=100
            )
        )

        self.add_hook("TL_updateUserStatus")
        self.add_hook("TL_updateReadHistoryOutbox")
        self.add_hook("TL_updateUserName")
        self.add_hook("TL_updateNewMessage")
        self.add_hook("TL_updateShortMessage")
        self.add_hook("TL_updateShortChatMessage")
        self.add_hook("TL_updateEditMessage")
        self.add_hook("TL_updateUserTyping")

    def get_message_data(self, msg, update=None):
        try:
            msg_id = getattr(msg, "id", getattr(update, "id", 0))
            is_out = getattr(msg, "out", getattr(update, "out", False))

            uid = ""
            peer = getattr(msg, "peer_id", None)
            if peer and hasattr(peer, "user_id"):
                uid = str(peer.user_id)
            if not uid and hasattr(update, "user_id"):
                uid = str(update.user_id)
            if not uid and hasattr(msg, "from_id") and msg.from_id and hasattr(msg.from_id, "user_id"):
                uid = str(msg.from_id.user_id)

            text = getattr(msg, "message", getattr(update, "message", ""))
            ttl = getattr(msg, "ttl_period", getattr(update, "ttl_period", 0))

            m_type = "text"

            if hasattr(msg, "media") and msg.media is not None:
                cls_name = msg.media.getClass().getSimpleName() if hasattr(msg.media, "getClass") else str(type(msg.media))
                ttl = ttl or getattr(msg.media, "ttl_seconds", 0)

                if "Photo" in cls_name:
                    m_type = "photo"
                    text = text or T("media_type_photo")
                elif "Document" in cls_name:
                    mime = getattr(msg.media.document, "mime_type", "")
                    if "audio/" in mime:
                        m_type = "voice_round"
                        text = text or T("media_type_voice")
                    elif "video/mp4" in mime:
                        is_round = False
                        attrs = getattr(msg.media.document, "attributes", [])

                        try:
                            for i in range(attrs.size() if hasattr(attrs, 'size') else len(attrs)):
                                attr = attrs.get(i) if hasattr(attrs, 'get') else attrs[i]
                                if "Video" in attr.getClass().getSimpleName() and getattr(attr, "round_message", False):
                                    is_round = True
                                    break
                        except Exception as e:
                            self._log_error(f"Media attrs err: {e}")

                        if is_round:
                            m_type = "voice_round"
                            text = text or T("media_type_round")
                        else:
                            m_type = "video"
                            text = text or T("media_type_video")
                    else:
                        m_type = "text"
                        text = text or T("media_type_file")
                else:
                    m_type = "text"
                    text = text or f"[{cls_name.replace('TL_messageMedia', '')}]"

            return msg_id, uid, is_out, text, m_type, ttl
        except Exception as e:
            self._log_error(f"get_message_data error: {e}")
            return 0, "", False, "", "text", 0

    def _notify_action(self, message: str, is_error: bool = False, fragment=None, context: dict = None):
        frag = fragment
        if not frag and context and isinstance(context, dict):
            frag = context.get("fragment")
        if not frag:
            frag = get_last_fragment()

        if BulletinHelper:
            try:
                if is_error:
                    BulletinHelper.show_error(message, fragment=frag)
                else:
                    BulletinHelper.show_success(message, fragment=frag)
            except Exception:
                try:
                    if is_error:
                        BulletinHelper.show_error(message)
                    else:
                        BulletinHelper.show_success(message)
                except Exception:
                    pass

        try:
            from android.widget import Toast
            from org.telegram.messenger import ApplicationLoader
            if ApplicationLoader and ApplicationLoader.applicationContext:
                Toast.makeText(ApplicationLoader.applicationContext, message, Toast.LENGTH_SHORT).show()
        except Exception:
            pass

    def toggle_tracking(self, *args, **kwargs):
        try:
            uid_int = 0
            resolved_name = ""
            frag = None
            account = getattr(UserConfig, "selectedAccount", 0)

            def _to_int(v):
                if v is None:
                    return 0
                if isinstance(v, (int, float)):
                    return int(v)
                try:
                    if hasattr(v, "longValue"):
                        return int(v.longValue())
                    if hasattr(v, "intValue"):
                        return int(v.intValue())
                except Exception:
                    pass
                try:
                    s = str(v).strip()
                    if s.isdigit():
                        return int(s)
                    if s.startswith("-") and s[1:].isdigit():
                        return int(s)
                except Exception:
                    pass
                return 0

            all_items = list(args) + list(kwargs.values())
            for item in all_items:
                if not item:
                    continue
                if isinstance(item, dict):
                    acc = item.get("account")
                    if isinstance(acc, int):
                        account = acc
                    if not frag and item.get("fragment"):
                        frag = item.get("fragment")
                    for k in ("userId", "user_id", "dialog_id", "dialogId", "uid", "id", "peer_id", "chat_id", "chatId"):
                        u = _to_int(item.get(k))
                        if u > 0:
                            uid_int = u
                            break
                    if not uid_int:
                        u_obj = item.get("user") or item.get("currentUser") or item.get("userFull") or item.get("userInfo")
                        if u_obj:
                            u = _to_int(getattr(u_obj, "id", None))
                            if u > 0:
                                uid_int = u
                                first = getattr(u_obj, "first_name", "") or ""
                                last = getattr(u_obj, "last_name", "") or ""
                                resolved_name = f"{first} {last}".strip()
                elif isinstance(item, (int, float)):
                    u = int(item)
                    if u > 0:
                        uid_int = u
                elif hasattr(item, "id") and _to_int(getattr(item, "id", 0)) > 0:
                    uid_int = _to_int(getattr(item, "id", 0))
                    first = getattr(item, "first_name", "") or ""
                    last = getattr(item, "last_name", "") or ""
                    resolved_name = f"{first} {last}".strip()
                elif hasattr(item, "getParentActivity") or hasattr(item, "getArguments") or hasattr(item, "getDialogId"):
                    if not frag:
                        frag = item

                if uid_int > 0:
                    break

            if not frag:
                frag = get_last_fragment()

            candidates = []
            if frag:
                candidates.append(frag)
                try:
                    if hasattr(frag, "parentLayout") and frag.parentLayout:
                        stack = getattr(frag.parentLayout, "fragmentsStack", None)
                        if stack:
                            for f in reversed(list(stack)):
                                if f not in candidates:
                                    candidates.append(f)
                except Exception:
                    pass

            for candidate in candidates:
                if uid_int > 0:
                    break
                try:
                    b_args = getattr(candidate, "arguments", None)
                    if not b_args and hasattr(candidate, "getArguments"):
                        b_args = candidate.getArguments()
                    if b_args:
                        for k in ("userId", "user_id", "dialog_id", "dialogId", "id"):
                            v = b_args.getLong(k, 0) if hasattr(b_args, "getLong") else b_args.get(k)
                            u = _to_int(v)
                            if u > 0:
                                uid_int = u
                                break
                except Exception:
                    pass

                if not uid_int:
                    for meth in ("getDialogId", "getUserId", "getUser_id"):
                        try:
                            fn = getattr(candidate, meth, None)
                            if callable(fn):
                                u = _to_int(fn())
                                if u > 0:
                                    uid_int = u
                                    break
                        except Exception:
                            pass

                if not uid_int:
                    for attr in ("userId", "dialogId", "user_id", "dialog_id"):
                        u = _to_int(getattr(candidate, attr, None))
                        if u > 0:
                            uid_int = u
                            break

                if not uid_int:
                    for u_attr in ("currentUser", "user", "userInfo"):
                        u_obj = getattr(candidate, u_attr, None)
                        if u_obj:
                            u = _to_int(getattr(u_obj, "id", None))
                            if u > 0:
                                uid_int = u
                                first = getattr(u_obj, "first_name", "") or ""
                                last = getattr(u_obj, "last_name", "") or ""
                                resolved_name = f"{first} {last}".strip()
                                break

                if not uid_int:
                    try:
                        cls = candidate.getClass()
                        while cls and cls.getName() != "java.lang.Object":
                            for fname in ("dialog_id", "user_id", "userId", "dialogId", "currentUser", "user"):
                                try:
                                    field = cls.getDeclaredField(fname)
                                    field.setAccessible(True)
                                    val = field.get(candidate)
                                    if val is not None:
                                        if hasattr(val, "id"):
                                            u = _to_int(getattr(val, "id", None))
                                        else:
                                            u = _to_int(val)
                                        if u > 0:
                                            uid_int = u
                                            break
                                except Exception:
                                    pass
                            if uid_int > 0:
                                break
                            cls = cls.getSuperclass()
                    except Exception:
                        pass

            if not uid_int or uid_int <= 0:
                self._notify_action(T("not_private"), is_error=True, fragment=frag)
                return

            user_id = str(uid_int)
            name = resolved_name
            if not name:
                try:
                    mc = MessagesController.getInstance(account)
                    user = None
                    if mc:
                        try:
                            user = mc.getUser(jclass("java.lang.Long")(uid_int))
                        except Exception:
                            pass
                        if not user:
                            try:
                                user = mc.getUser(uid_int)
                            except Exception:
                                pass
                    if user:
                        first = getattr(user, "first_name", "") or ""
                        last = getattr(user, "last_name", "") or ""
                        name = f"{first} {last}".strip()
                except Exception:
                    pass
            if not name:
                name = f"ID: {user_id}"

            with self._data_lock:
                already_tracked = user_id in self.tracked_users

            if already_tracked:
                with self._data_lock:
                    if user_id in self.tracked_users:
                        del self.tracked_users[user_id]
                self._save_users()
                self._notify_action(f"{name} удален из слежки", is_error=False, fragment=frag)
            else:
                with self._data_lock:
                    self.tracked_users[user_id] = {
                        "name": name,
                        "history": [],
                        "sessions_log": [],
                        "last_ts": 0,
                        "last_text": "",
                        "last_type": "",
                        "session_start_ts": 0,
                        "first_name": name,
                        "activity_hours": [0] * 24,
                        "total_online_time": 0,
                        "total_reads": 0,
                        "notifications_enabled": True,
                        "has_unread_out": False,
                        "last_out_msg_ts": 0,
                        "ignored_online_count": 0,
                        "last_read_outbox_ts": 0,
                        "loyalty_ignored": 0,
                        "loyalty_replied": 0,
                        "custom_tag": "",
                        "media_stats": {},
                        "is_pinned": False,
                        "local_name": ""
                    }
                self._save_users()
                self._notify_action(f"{name} добавлен в слежку!", is_error=False, fragment=frag)

            if frag:
                try:
                    if hasattr(frag, "updateRowsIds"):
                        frag.updateRowsIds()
                    adapter = getattr(frag, "listAdapter", None)
                    if adapter and hasattr(adapter, "notifyDataSetChanged"):
                        adapter.notifyDataSetChanged()
                except Exception:
                    pass

        except Exception as e:
            self._log_error(f"toggle_tracking err: {e}")
            try:
                from android.widget import Toast
                from org.telegram.messenger import ApplicationLoader
                Toast.makeText(ApplicationLoader.applicationContext, f"Ошибка: {e}", Toast.LENGTH_SHORT).show()
            except Exception:
                pass

    def get_display_name(self, uid: str, data: dict) -> str:
        local = data.get("local_name", "").strip()
        if local:
            return f"{local} ®"
        return data.get("name", uid)

    def format_duration(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        res = []
        is_ru = self.get_lang_code() == "ru"
        h_str = "ч" if is_ru else "h"
        m_str = "м" if is_ru else "m"
        s_str = "с" if is_ru else "s"
        if h > 0:
            res.append(f"{h}{h_str}")
        if m > 0:
            res.append(f"{m}{m_str}")
        if s > 0 or not res:
            res.append(f"{s}{s_str}")
        return " ".join(res)

    def generate_bar(self, current: int, total: int) -> str:
        if total == 0:
            return "[░░░░░░░░░░]"
        percent = current / total
        blocks = int(percent * 10)
        empty = 10 - blocks
        return f"[{'█' * blocks}{'░' * empty}]"

    def add_history_event(self, user_id: str, event_icon: str, event_text: str, event_type: str, should_notify: bool, event_ts: float = 0):
        with self._data_lock:
            if user_id not in self.tracked_users:
                return
            user_data = self.tracked_users[user_id]
            now = datetime.now()
            now_ts = time.time()
            actual_ts = event_ts if event_ts > 0 else now_ts
            date_str = datetime.fromtimestamp(actual_ts).strftime("%d.%m.%Y")
            time_str = datetime.fromtimestamp(actual_ts).strftime("%H:%M:%S")

            history = user_data.setdefault("history", [])

            if event_type == "online":
                user_data["session_start_ts"] = actual_ts
                last_out = user_data.get("last_out_msg_ts", 0)
                if last_out > 0:
                    user_data["ignored_online_count"] = user_data.get("ignored_online_count", 0) + 1

            if event_type == "offline":
                session_start = user_data.get("session_start_ts", 0)
                if session_start > 0:
                    duration = actual_ts - session_start
                    if duration < 5:
                        if history:
                            history.pop()
                        event_icon = "⚡"
                        event_text = T("micro_session")
                        event_type = "micro_session"
                        should_notify = False
                    else:
                        user_data["total_online_time"] = user_data.get("total_online_time", 0) + duration
                        start_str = datetime.fromtimestamp(session_start).strftime("%H:%M:%S")
                        dur_str = self.format_duration(duration)
                        sessions = user_data.setdefault("sessions_log", [])
                        sessions.append(f"🟢 {start_str} - 🔴 {time_str} ({dur_str})")
                        try:
                            m_len = int(self.max_logs)
                        except ValueError:
                            m_len = 400
                        if len(sessions) > m_len:
                            user_data["sessions_log"] = sessions[-m_len:]
                    user_data["session_start_ts"] = 0

            if event_icon == "🟢" or event_type == "online":
                hour = now.hour
                activity = user_data.setdefault("activity_hours", [0] * 24)
                if len(activity) != 24:
                    activity = [0] * 24
                activity[hour] += 1
                user_data["activity_hours"] = activity

            if event_icon == "✔️":
                user_data["total_reads"] = user_data.get("total_reads", 0) + 1

            user_data["last_ts"] = actual_ts
            user_data["last_text"] = event_text
            user_data["last_type"] = event_type

            history.append({
                "date": date_str,
                "time": time_str,
                "icon": event_icon,
                "text": event_text,
                "type": event_type,
                "ts": actual_ts
            })

            try:
                max_l = int(self.max_logs)
            except ValueError:
                max_l = 400

            if len(history) > max_l:
                user_data["history"] = history[-max_l:]

            user_notifications = user_data.get("notifications_enabled", True)
            tag = user_data.get("custom_tag", "")
            disp_name = self.get_display_name(user_id, user_data)

        self._save_users()

        if self.master_notify and should_notify and user_notifications:
            if getattr(self, "notify_system", True) or getattr(self, "notify_in_app", True):
                tag_str = f" {tag}" if tag else ""
                title = f"{disp_name}{tag_str}"
                sys_text = f"{event_icon} {event_text}"
                is_call = getattr(self, "notify_hyperbridge", False)
                self.send_system_notification(title, sys_text, is_call)

    def on_update_hook(self, update_name: str, account: int, update: Any) -> HookResult:
        if not self.master_track:
            return HookResult()

        now_ts = time.time()

        if now_ts - getattr(self, "_last_maintenance_check", 0) > 600:
            self._last_maintenance_check = now_ts
            if now_ts - getattr(self, "last_clean_ts", 0) > 86400:
                self.last_clean_ts = now_ts
                self.set_setting("last_clean_ts", now_ts, reload_settings=False)
                self.run_auto_clean()

            if getattr(self, "auto_backup_enabled", False):
                try:
                    b_days = int(getattr(self, "auto_backup_days", 7))
                except ValueError:
                    b_days = 7
                if b_days > 0 and now_ts - getattr(self, "last_backup_ts", 0) > (b_days * 86400):
                    self.last_backup_ts = now_ts
                    self.set_setting("last_backup_ts", now_ts, reload_settings=False)
                    self.run_auto_backup(account=account)

        if update_name == "TL_updateUserStatus" and self.track_online:
            user_id = str(getattr(update, "user_id", ""))
            with self._data_lock:
                is_tracked = user_id in self.tracked_users
                last_type = self.tracked_users[user_id].get("last_type", "") if is_tracked else ""
                has_ignored = self.tracked_users[user_id].get("has_unread_out", False) if is_tracked else False

            if is_tracked:
                if isinstance(update.status, TLRPC.TL_userStatusOnline):
                    if last_type != "online":
                        self.add_history_event(user_id, "🟢", T("online"), "online", self.notify_online)
                elif isinstance(update.status, TLRPC.TL_userStatusOffline):
                    if last_type != "offline":
                        if has_ignored:
                            with self._data_lock:
                                if user_id in self.tracked_users:
                                    self.tracked_users[user_id]["loyalty_ignored"] = self.tracked_users[user_id].get("loyalty_ignored", 0) + 1

                        was_online = getattr(update.status, "was_online", int(time.time()))
                        self.add_history_event(user_id, "🔴", T("offline"), "offline", self.notify_offline, was_online)

                        if has_ignored:
                            self.add_history_event(user_id, "🙈", T("came_and_left"), "came_and_left", self.notify_offline)
                elif isinstance(update.status, TLRPC.TL_userStatusEmpty) and getattr(self, "track_block", False):
                    if last_type != "spam_trap":
                        self.add_history_event(user_id, "🚫", T("spam_trap"), "spam_trap", getattr(self, "notify_block", False))

        elif update_name == "TL_updateReadHistoryOutbox":
            peer_id = getattr(update.peer, 'user_id', None) if hasattr(update, 'peer') else None
            if peer_id:
                user_id = str(peer_id)
                with self._data_lock:
                    is_tracked = user_id in self.tracked_users
                    if is_tracked:
                        self.tracked_users[user_id]["last_read_outbox_ts"] = time.time()
                        self.tracked_users[user_id]["last_out_msg_ts"] = 0
                        self.tracked_users[user_id]["has_unread_out"] = False

                if is_tracked:
                    if self.track_read:
                        with self._data_lock:
                            history = self.tracked_users[user_id].get("history", [])
                            for i in range(1, min(4, len(history) + 1)):
                                if history[-i].get("type") == "came_and_left":
                                    history.pop(-i)
                                    self.tracked_users[user_id]["loyalty_ignored"] = max(0, self.tracked_users[user_id].get("loyalty_ignored", 0) - 1)
                                    break

                            last_type = history[-1].get("type") if history else ""
                            is_dup_read = (history and last_type in ["read", "read_multiple"] and (time.time() - history[-1].get("ts", 0)) < 120)
                            if is_dup_read:
                                if last_type != "read_multiple":
                                    history[-1]["text"] = T("read_multiple")
                                    history[-1]["type"] = "read_multiple"

                        if not is_dup_read:
                            self.add_history_event(user_id, "✔️", T("read"), "read", self.notify_read)

                    self._save_users()

        elif update_name == "TL_updateUserName" and self.track_name:
            user_id = str(getattr(update, "user_id", ""))
            with self._data_lock:
                is_tracked = user_id in self.tracked_users
                old_name = self.tracked_users[user_id].get("first_name", "") if is_tracked else ""

            if is_tracked:
                new_first = getattr(update, "first_name", "") or ""
                new_last = getattr(update, "last_name", "") or ""
                new_name = f"{new_first} {new_last}".strip()

                if old_name and new_name and old_name != new_name:
                    self.add_history_event(user_id, "📝", f"{T('changed_name')} {old_name} -> {new_name}", "name_change", self.notify_name)
                with self._data_lock:
                    if user_id in self.tracked_users:
                        self.tracked_users[user_id]["first_name"] = new_name
                self._save_users()

        elif update_name == "TL_updateUserTyping" and getattr(self, "track_typing", True):
            uid_val = getattr(update, "user_id", None)
            if uid_val is None and hasattr(update, "from_id"):
                uid_val = getattr(update.from_id, "user_id", None)
            if uid_val is not None:
                user_id = str(uid_val)
                with self._data_lock:
                    is_tracked = user_id in self.tracked_users
                    if is_tracked:
                        user_data = self.tracked_users[user_id]
                        last_ts = user_data.get("last_ts", 0)
                        last_text = user_data.get("last_text", "")
                        should_log = not (last_text == T("typing") and (now_ts - last_ts) < 15)
                    else:
                        should_log = False

                if should_log:
                    self.add_history_event(user_id, "✍️", T("typing"), "typing", False)

        elif update_name in ["TL_updateNewMessage", "TL_updateShortMessage", "TL_updateShortChatMessage", "TL_updateEditMessage"]:
            msg = getattr(update, "message", update)
            if msg:
                msg_id, uid, is_out, text, m_type, ttl = self.get_message_data(msg, update)
                with self._data_lock:
                    is_tracked = uid in self.tracked_users
                    if is_tracked:
                        last_t = self.tracked_users[uid].get("last_ts", 0)
                        last_txt = self.tracked_users[uid].get("last_text", "")
                        last_read = self.tracked_users[uid].get("last_read_outbox_ts", 0)
                    else:
                        last_t, last_txt, last_read = 0, "", 0

                if is_tracked:
                    if update_name == "TL_updateEditMessage":
                        if not is_out:
                            now_ts_msg = time.time()
                            if last_txt != T("online") and (now_ts_msg - last_t > 300):
                                self.add_history_event(uid, "🟢", T("online"), "online", getattr(self, "notify_online", True))
                        return HookResult()

                    if not is_out:
                        now_ts_msg = time.time()
                        with self._data_lock:
                            if uid in self.tracked_users:
                                self.tracked_users[uid]["last_in_msg_ts"] = now_ts_msg
                                media_stats = self.tracked_users[uid].setdefault("media_stats", {})
                                media_stats[m_type] = media_stats.get(m_type, 0) + 1
                                self.tracked_users[uid]["has_unread_out"] = False

                                history = self.tracked_users[uid].get("history", [])
                                for i in range(1, min(4, len(history) + 1)):
                                    if history[-i].get("type") == "came_and_left":
                                        history.pop(-i)
                                        self.tracked_users[uid]["loyalty_ignored"] = max(0, self.tracked_users[uid].get("loyalty_ignored", 0) - 1)
                                        break

                                if last_read > 0:
                                    if (now_ts_msg - last_read) <= 600:
                                        self.tracked_users[uid]["loyalty_replied"] = self.tracked_users[uid].get("loyalty_replied", 0) + 1
                                    self.tracked_users[uid]["last_read_outbox_ts"] = 0

                        if last_txt != T("online") and (now_ts_msg - last_t > 300):
                            self.add_history_event(uid, "🟢", T("online"), "online", getattr(self, "notify_online", True))
                    else:
                        if update_name != "TL_updateEditMessage":
                            with self._data_lock:
                                if uid in self.tracked_users:
                                    self.tracked_users[uid]["last_out_msg_ts"] = time.time()
                                    self.tracked_users[uid]["has_unread_out"] = True
                    self._save_users()

        return HookResult()

    def get_sleep_pattern(self, user_data) -> str:
        history = user_data.get("history", [])
        gaps = []

        last_offline = 0
        for ev in history:
            ts = ev.get("ts", 0)
            if ts == 0:
                continue

            ev_type = ev.get("type", "")
            if ev_type == "offline":
                last_offline = ts
            elif ev_type == "online":
                if last_offline > 0:
                    gap = ts - last_offline
                    if gap >= 4 * 3600:
                        gaps.append((last_offline, gap))
                    last_offline = 0

        if last_offline > 0:
            current_gap = time.time() - last_offline
            if current_gap >= 4 * 3600:
                gaps.append((last_offline, current_gap))

        if not gaps:
            return T("no_data")
        recent_gaps = gaps[-7:]

        total_shifted = 0
        total_dur = 0
        for start_ts, dur in recent_gaps:
            dt = datetime.fromtimestamp(start_ts)
            secs = dt.hour * 3600 + dt.minute * 60 + dt.second
            shifted = (secs + 43200) % 86400
            total_shifted += shifted
            total_dur += dur

        avg_shifted = total_shifted / len(recent_gaps)
        avg_secs = (avg_shifted - 43200) % 86400

        h = int(avg_secs // 3600)
        m = int((avg_secs % 3600) // 60)
        avg_dur = total_dur / len(recent_gaps)

        return T("sleep_pattern_format").format(time=f"{h:02d}:{m:02d}", dur=self.format_duration(avg_dur))

    def get_online_prediction(self, user_data) -> str:
        activity = user_data.get("activity_hours", [0] * 24)
        total_act = sum(activity)
        if total_act == 0:
            return ""

        now = datetime.now()
        current_hour = now.hour
        avg_val = total_act / 24.0

        if activity[current_hour] >= avg_val:
            return T("prediction_online")

        max_val = max(activity)
        for i in range(1, 13):
            check_hour = (current_hour + i) % 24
            if activity[check_hour] >= max_val * 0.4 or activity[check_hour] > avg_val:
                return T("prediction_offline").format(hours=i)

        return ""

    def export_backup(self, view=None):
        try:
            ctx = self._get_app_context()
            if not ctx:
                return

            cache_dir = str(ctx.getExternalCacheDir().getAbsolutePath())
            out_path = os.path.join(cache_dir, f"omnianalytics_backup_{int(time.time())}.omni")

            backup_data = {
                "tracked_users": self._get_safe_users(),
                "settings": {
                    "master_track": getattr(self, "master_track", True),
                    "track_online": getattr(self, "track_online", True),
                    "track_read": getattr(self, "track_read", True),
                    "track_name": getattr(self, "track_name", True),
                    "track_typing": getattr(self, "track_typing", True),
                    "master_notify": getattr(self, "master_notify", True),
                    "notify_online": getattr(self, "notify_online", True),
                    "notify_offline": getattr(self, "notify_offline", True),
                    "notify_read": getattr(self, "notify_read", True),
                    "notify_name": getattr(self, "notify_name", True)
                }
            }

            encrypted_payload = self._encrypt_data(backup_data)

            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_payload)

            File = jclass("java.io.File")
            FileProvider = jclass("androidx.core.content.FileProvider")

            file_obj = File(out_path)
            uri = FileProvider.getUriForFile(ctx, ctx.getPackageName() + ".provider", file_obj)

            intent = Intent(Intent.ACTION_SEND)
            intent.setType("application/octet-stream")
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            chooser = Intent.createChooser(intent, T("export_chooser"))
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(chooser)

        except Exception as e:
            BulletinHelper.show_error(T("export_err").format(e=e))

    def _apply_imported_data(self, data):
        if not data or not isinstance(data, dict):
            BulletinHelper.show_error(T("import_err_key"))
            return
        if "tracked_users" not in data or not isinstance(data["tracked_users"], dict):
            BulletinHelper.show_error(T("import_err_db"))
            return

        validated_users = {}
        for uid, udata in data["tracked_users"].items():
            if not str(uid).isdigit() or type(udata) is not dict:
                continue
            act_hours = udata.get("activity_hours", [0]*24)
            if not isinstance(act_hours, list) or len(act_hours) != 24:
                act_hours = [0]*24
            validated_users[uid] = {
                "name": str(udata.get("name", uid))[:100],
                "history": udata.get("history", []),
                "sessions_log": udata.get("sessions_log", []),
                "last_ts": float(udata.get("last_ts", 0)),
                "last_text": str(udata.get("last_text", ""))[:200],
                "last_type": str(udata.get("last_type", "")),
                "session_start_ts": float(udata.get("session_start_ts", 0)),
                "first_name": str(udata.get("first_name", uid))[:100],
                "activity_hours": act_hours,
                "total_online_time": float(udata.get("total_online_time", 0)),
                "total_reads": int(udata.get("total_reads", 0)),
                "notifications_enabled": bool(udata.get("notifications_enabled", True)),
                "has_unread_out": bool(udata.get("has_unread_out", False)),
                "last_out_msg_ts": float(udata.get("last_out_msg_ts", 0)),
                "ignored_online_count": int(udata.get("ignored_online_count", 0)),
                "last_read_outbox_ts": float(udata.get("last_read_outbox_ts", 0)),
                "loyalty_ignored": int(udata.get("loyalty_ignored", 0)),
                "loyalty_replied": int(udata.get("loyalty_replied", 0)),
                "custom_tag": str(udata.get("custom_tag", ""))[:50],
                "media_stats": udata.get("media_stats", {}),
                "is_pinned": bool(udata.get("is_pinned", False)),
                "local_name": str(udata.get("local_name", ""))[:100]
            }

        with self._data_lock:
            self.tracked_users = validated_users
        self._save_users_sync()

        if "settings" in data and isinstance(data["settings"], dict):
            for k, v in data["settings"].items():
                if isinstance(k, str) and k in ["master_track", "track_online", "track_read", "track_name", "track_typing", "master_notify", "notify_online", "notify_offline", "notify_read", "notify_name"]:
                    setattr(self, k, bool(v))
                    self.set_setting(k, bool(v), reload_settings=False)

        BulletinHelper.show_success(T("import_success"))
        try:
            from android.widget import Toast
            from org.telegram.messenger import ApplicationLoader
            Toast.makeText(ApplicationLoader.applicationContext, T("import_toast_success"), Toast.LENGTH_SHORT).show()
        except Exception:
            pass

    def _handle_import_uri(self, uri):
        def process_import():
            try:
                ctx = self._get_app_context()
                if not ctx:
                    return
                cr = ctx.getContentResolver()
                stream = cr.openInputStream(uri)
                if not stream:
                    BulletinHelper.show_error(T("import_err_file"))
                    return
                InputStreamReader = jclass("java.io.InputStreamReader")
                BufferedReader = jclass("java.io.BufferedReader")
                StringBuilder = jclass("java.lang.StringBuilder")
                reader = BufferedReader(InputStreamReader(stream, "UTF-8"))
                sb = StringBuilder()
                while True:
                    line = reader.readLine()
                    if line is None:
                        break
                    sb.append(line)
                encrypted_str = sb.toString()
                reader.close()
                stream.close()
                data = self._decrypt_data(encrypted_str)
                run_on_ui_thread(lambda: self._apply_imported_data(data))
            except Exception as e:
                def show_err():
                    BulletinHelper.show_error(T("import_err_verify"))
                    try:
                        from android.widget import Toast
                        from org.telegram.messenger import ApplicationLoader
                        Toast.makeText(ApplicationLoader.applicationContext, T("import_toast_err").format(e=e), Toast.LENGTH_LONG).show()
                    except Exception:
                        pass
                run_on_ui_thread(show_err)
        threading.Thread(target=process_import, daemon=True).start()

    def import_backup(self, view):
        try:
            fragment = get_last_fragment()
            if not fragment:
                BulletinHelper.show_error(T("import_err_explorer"))
                return

            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("*/*")

            fragment.startActivityForResult(intent, 8192)
        except Exception as e:
            BulletinHelper.show_error(T("import_err_open").format(e=e))

    def _on_card_caption_change(self, val):
        b_val = bool(val)
        self.card_caption_enabled = b_val
        self.set_setting("card_caption_enabled", b_val, reload_settings=False)

    def _handle_custom_bg_uri(self, uri):
        def process_bg():
            stream = None
            try:
                ctx = self._get_app_context()
                if not ctx:
                    return
                cr = ctx.getContentResolver()
                stream = cr.openInputStream(uri)
                if not stream:
                    BulletinHelper.show_error("Не удалось открыть изображение" if LANG == "ru" else "Failed to open image")
                    return

                data_dir = getattr(self, "data_dir", "") or self._get_data_dir()
                dest_dir = os.path.join(data_dir, "omniscient_card")
                os.makedirs(dest_dir, exist_ok=True)
                dest_file = os.path.join(dest_dir, "custom_card_bg.png")

                BitmapFactory = jclass("android.graphics.BitmapFactory")
                CompressFormat = jclass("android.graphics.Bitmap$CompressFormat")
                FileOutputStream = jclass("java.io.FileOutputStream")

                bitmap = BitmapFactory.decodeStream(stream)
                if bitmap is not None:
                    fos = FileOutputStream(dest_file)
                    bitmap.compress(CompressFormat.PNG, 100, fos)
                    fos.flush()
                    fos.close()

                    self.custom_card_bg = dest_file

                    def on_done():
                        self.set_setting("custom_card_bg", dest_file, reload_settings=True)
                        BulletinHelper.show_success("Фон инфографики обновлён!" if LANG == "ru" else "Infographic background updated!")
                    run_on_ui_thread(on_done)
                else:
                    def on_dec_err():
                        BulletinHelper.show_error("Не удалось декодировать изображение" if LANG == "ru" else "Failed to decode image")
                    run_on_ui_thread(on_dec_err)
            except Exception as e:
                self._log_error(f"Handle custom bg err: {e}")
                def on_err():
                    BulletinHelper.show_error(f"Ошибка сохранения фона: {e}" if LANG == "ru" else f"Background save error: {e}")
                run_on_ui_thread(on_err)
            finally:
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass
        threading.Thread(target=process_bg, daemon=True).start()

    def pick_custom_card_bg(self):
        try:
            fragment = get_last_fragment()
            if not fragment:
                BulletinHelper.show_error("Не удалось открыть галерею" if LANG == "ru" else "Failed to open gallery")
                return

            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")

            fragment.startActivityForResult(intent, 8193)
        except Exception as e:
            BulletinHelper.show_error(f"Ошибка выбора изображения: {e}" if LANG == "ru" else f"Gallery error: {e}")

    def show_card_bg_dialog(self):
        fragment = get_last_fragment()
        ctx = fragment.getParentActivity() if fragment else self._get_app_context()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title("Фон инфографики" if LANG == "ru" else "Infographic Background")

        items = [
            "Выбрать фото из галереи" if LANG == "ru" else "Pick photo from gallery",
            "Просто сбросить" if LANG == "ru" else "Reset to default"
        ]

        icons_list = []
        try:
            R_drawable = jclass("org.telegram.messenger.R$drawable")
            icon_gallery = getattr(R_drawable, "msg_photo", 0) or getattr(R_drawable, "msg_gallery", 0)
            icon_reset = getattr(R_drawable, "msg_clear", 0) or getattr(R_drawable, "msg_retry", 0) or getattr(R_drawable, "msg_delete", 0)
            if icon_gallery and icon_reset:
                icons_list = [icon_gallery, icon_reset]
        except Exception:
            pass

        def callback(d, which):
            if which == 0:
                self.pick_custom_card_bg()
            elif which == 1:
                self.reset_custom_card_bg()

        if icons_list:
            try:
                builder.set_items(items, callback, icons=icons_list)
            except TypeError:
                builder.set_items(items, callback)
        else:
            builder.set_items(items, callback)

        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def reset_custom_card_bg(self):
        self.custom_card_bg = ""
        self.set_setting("custom_card_bg", "", reload_settings=True)
        data_dir = getattr(self, "data_dir", "") or self._get_data_dir()
        if data_dir:
            dest_dir = os.path.join(data_dir, "omniscient_card")
            if os.path.exists(dest_dir):
                for fn in os.listdir(dest_dir):
                    try:
                        os.remove(os.path.join(dest_dir, fn))
                    except Exception:
                        pass
        BulletinHelper.show_success("Фон сброшен на стандартный" if LANG == "ru" else "Background reset to default")

    def show_card_theme_dialog(self):
        fragment = get_last_fragment()
        ctx = fragment.getParentActivity() if fragment else self._get_app_context()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title("Тема инфографики" if LANG == "ru" else "Infographic Theme")

        items = [
            "Тёмная тема (Dark)" if LANG == "ru" else "Dark Theme",
            "Светлая тема (Light)" if LANG == "ru" else "Light Theme"
        ]

        icons_list = []
        try:
            R_drawable = jclass("org.telegram.messenger.R$drawable")
            icon_dark = getattr(R_drawable, "msg_night", 0) or getattr(R_drawable, "menu_night", 0) or getattr(R_drawable, "msg_theme", 0)
            icon_light = getattr(R_drawable, "msg_day", 0) or getattr(R_drawable, "msg_sun", 0) or getattr(R_drawable, "msg_theme", 0)
            if icon_dark and icon_light:
                icons_list = [icon_dark, icon_light]
        except Exception:
            pass

        def callback(d, which):
            chosen = "dark" if which == 0 else "light"
            self.card_theme = chosen
            self.set_setting("card_theme", chosen, reload_settings=True)
            name = "Тёмная" if chosen == "dark" else "Светлая"
            BulletinHelper.show_success(f"Тема: {name}" if LANG == "ru" else f"Theme: {chosen.title()}")

        if icons_list:
            try:
                builder.set_items(items, callback, icons=icons_list)
            except TypeError:
                builder.set_items(items, callback)
        else:
            builder.set_items(items, callback)

        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def show_language_menu(self, anchor):
        try:
            from android.widget import PopupWindow, LinearLayout, TextView
            from android.view import View, Gravity
            from android.graphics.drawable import GradientDrawable
            from org.telegram.messenger import AndroidUtilities
            from android_utils import OnClickListener

            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            if not anchor:
                self.show_language_dialog()
                return

            ctx = anchor.getContext()
            if not ctx:
                self.show_language_dialog()
                return

            dark = self._is_dark_theme() if hasattr(self, "_is_dark_theme") else True

            root = LinearLayout(ctx)
            root.setOrientation(LinearLayout.VERTICAL)
            root.setPadding(dp(6), dp(6), dp(6), dp(6))

            bg = GradientDrawable()
            bg.setShape(GradientDrawable.RECTANGLE)
            bg.setCornerRadius(float(dp(12)))
            bg.setColor(c(0xFF1E293B if dark else 0xFFFFFFFF))
            bg.setStroke(dp(1), c(0x3538BDF8 if dark else 0x20000000))
            root.setBackground(bg)
            try:
                root.setElevation(float(dp(8)))
            except Exception:
                pass

            popup = PopupWindow(root, dp(140), -2, True)
            try:
                popup.setOutsideTouchable(True)
                popup.setFocusable(True)
            except Exception:
                pass

            options = [
                ("auto", "Авто (Системный)" if self.get_lang_code() == "ru" else "Auto (System)"),
                ("ru", "Русский"),
                ("en", "English")
            ]

            cur_pref = str(self.get_setting("app_language", "auto")).lower()

            for opt_key, opt_label in options:
                tv = TextView(ctx)
                is_selected = (cur_pref == opt_key)
                tv.setText(f"✓  {opt_label}" if is_selected else f"    {opt_label}")
                tv.setTextSize(1, 13.0)
                tv.setTextColor(c(0xFF38BDF8 if is_selected else (0xFFE2E8F0 if dark else 0xFF1E293B)))
                tv.setPadding(dp(10), dp(8), dp(10), dp(8))
                tv.setGravity(Gravity.CENTER_VERTICAL)
                tv.setClickable(True)

                def make_cb(k, lbl):
                    def _cb(v=None):
                        global LANG
                        try:
                            popup.dismiss()
                        except Exception:
                            pass
                        self.set_setting("app_language", k, reload_settings=False)
                        LANG = self.get_lang_code()
                        BulletinHelper.show_success(f"Язык изменён: {lbl}" if LANG == "ru" else f"Language set to: {lbl}")
                        self.set_setting("app_language", k, reload_settings=True)
                    return _cb

                if OnClickListener:
                    tv.setOnClickListener(OnClickListener(make_cb(opt_key, opt_label)))
                root.addView(tv, LinearLayout.LayoutParams(-1, -2))

            try:
                popup.showAsDropDown(anchor, -dp(90), dp(4))
            except Exception:
                self.show_language_dialog()
        except Exception as e:
            self._log_error(f"show_language_menu err: {e}")
            self.show_language_dialog()

    def show_language_dialog(self):
        fragment = get_last_fragment()
        ctx = fragment.getParentActivity() if fragment else self._get_app_context()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        is_ru = self.get_lang_code() == "ru"
        builder.set_title("Язык интерфейса" if is_ru else "Interface Language")

        items = [
            "Авто (Системный)" if is_ru else "Auto (System)",
            "Русский (RU)",
            "English (EN)"
        ]

        icons_list = []
        try:
            R_drawable = jclass("org.telegram.messenger.R$drawable")
            ic_auto = getattr(R_drawable, "msg_language", 0) or getattr(R_drawable, "msg_translate", 0) or getattr(R_drawable, "msg_settings", 0)
            ic_ru = getattr(R_drawable, "msg_translate", 0) or getattr(R_drawable, "msg_language", 0)
            ic_en = getattr(R_drawable, "msg_translate", 0) or getattr(R_drawable, "msg_language", 0)
            if ic_auto and ic_ru and ic_en:
                icons_list = [ic_auto, ic_ru, ic_en]
        except Exception:
            pass

        def callback(d, which):
            global LANG
            if which == 0:
                self.set_setting("app_language", "auto", reload_settings=False)
                LANG = self.get_lang_code()
                lbl = "Авто" if LANG == "ru" else "Auto"
            elif which == 1:
                self.set_setting("app_language", "ru", reload_settings=False)
                LANG = "ru"
                lbl = "Русский"
            else:
                self.set_setting("app_language", "en", reload_settings=False)
                LANG = "en"
                lbl = "English"

            BulletinHelper.show_success(f"Язык изменён: {lbl}" if LANG == "ru" else f"Language set to: {lbl}")
            try:
                self.set_setting("app_language", self.get_setting("app_language", "auto"), reload_settings=True)
            except Exception:
                pass

        if icons_list:
            try:
                builder.set_items(items, callback, icons=icons_list)
            except TypeError:
                builder.set_items(items, callback)
        else:
            builder.set_items(items, callback)

        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def _process_local_import(self, filepath):
        def do_import():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    encrypted_str = f.read()
                data = self._decrypt_data(encrypted_str)
                run_on_ui_thread(lambda: self._apply_imported_data(data))
            except Exception as e:
                self._log_error(f"Local import err: {e}")
                BulletinHelper.show_error(T("import_err_verify"))
        threading.Thread(target=do_import, daemon=True).start()

    def restore_auto_backup(self, view):
        try:
            backup_dir = os.path.join(get_documents_dir(), "Omniscient")
            if not os.path.exists(backup_dir):
                BulletinHelper.show_error(T("no_auto_backups"))
                return

            files = [f for f in os.listdir(backup_dir) if f.startswith("autobackup_") and f.endswith(".omni")]
            if not files:
                BulletinHelper.show_error(T("no_auto_backups"))
                return

            files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)

            current_fragment = get_last_fragment()
            if not current_fragment:
                return
            ctx = current_fragment.getParentActivity()
            if not ctx:
                return

            builder = AlertDialogBuilder(ctx)
            builder.set_title(T("restore_auto_backup_title"))

            display_names = []
            icons_list = []
            icon_file = 0
            try:
                R_drawable = jclass("org.telegram.messenger.R$drawable")
                icon_file = getattr(R_drawable, "msg_files", 0) or getattr(R_drawable, "msg_archive", 0) or getattr(R_drawable, "msg_storage", 0) or getattr(R_drawable, "msg_file", 0)
            except Exception:
                pass

            for f in files:
                f_path = os.path.join(backup_dir, f)
                try:
                    ts = int(f.replace("autobackup_", "").replace(".omni", ""))
                    dt_str = datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
                    size_kb = int(os.path.getsize(f_path) / 1024)
                    display_names.append(f"{dt_str} ({size_kb} KB)")
                except Exception:
                    display_names.append(f)
                if icon_file:
                    icons_list.append(icon_file)

            def callback(d, w):
                target_file = os.path.join(backup_dir, files[w])
                self._process_local_import(target_file)

            if icons_list:
                try:
                    builder.set_items(display_names, callback, icons=icons_list)
                except TypeError:
                    builder.set_items(display_names, callback)
            else:
                builder.set_items(display_names, callback)

            builder.set_negative_button(T("cancel"), lambda d, w: None)
            builder.show()
        except Exception as e:
            self._log_error(f"Restore err: {e}")
            BulletinHelper.show_error(T("import_err_file"))

    def open_backup_folder(self, view):
        try:
            backup_dir = os.path.join(get_documents_dir(), "Omniscient")
            if not os.path.exists(backup_dir):
                BulletinHelper.show_error(T("no_auto_backups"))
                return

            files = [f for f in os.listdir(backup_dir) if f.startswith("autobackup_") and f.endswith(".omni")]
            if not files:
                BulletinHelper.show_error(T("no_auto_backups"))
                return

            files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)

            current_fragment = get_last_fragment()
            if not current_fragment:
                return
            ctx = current_fragment.getParentActivity()
            if not ctx:
                return

            builder = AlertDialogBuilder(ctx)
            builder.set_title(T("manage_backups_title"))

            display_names = []
            icons_list = []
            icon_file = 0
            try:
                R_drawable = jclass("org.telegram.messenger.R$drawable")
                icon_file = getattr(R_drawable, "msg_files", 0) or getattr(R_drawable, "msg_archive", 0) or getattr(R_drawable, "msg_storage", 0) or getattr(R_drawable, "msg_file", 0)
            except Exception:
                pass

            for f in files:
                f_path = os.path.join(backup_dir, f)
                try:
                    ts = int(f.replace("autobackup_", "").replace(".omni", ""))
                    dt_str = datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
                    size_kb = int(os.path.getsize(f_path) / 1024)
                    display_names.append(f"{dt_str} ({size_kb} KB)")
                except Exception:
                    display_names.append(f)
                if icon_file:
                    icons_list.append(icon_file)

            def callback(d, w):
                target_file = os.path.join(backup_dir, files[w])
                self.show_backup_options(target_file, files[w])

            if icons_list:
                try:
                    builder.set_items(display_names, callback, icons=icons_list)
                except TypeError:
                    builder.set_items(display_names, callback)
            else:
                builder.set_items(display_names, callback)

            builder.set_negative_button(T("cancel"), lambda d, w: None)
            builder.show()
        except Exception as e:
            self._log_error(f"Open folder err: {e}")
            BulletinHelper.show_error(T("import_err_file"))

    def show_backup_options(self, filepath, filename):
        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        ctx = current_fragment.getParentActivity()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title(filename)

        items = [T("export_msg"), T("btn_delete")]
        icons_list = []
        try:
            R_drawable = jclass("org.telegram.messenger.R$drawable")
            icon_share = getattr(R_drawable, "msg_share", 0)
            icon_del = getattr(R_drawable, "msg_delete", 0)
            if icon_share and icon_del:
                icons_list = [icon_share, icon_del]
        except Exception:
            pass

        def callback(d, w):
            if w == 0:
                self.share_backup_file(filepath)
            elif w == 1:
                try:
                    os.remove(filepath)
                    BulletinHelper.show_success(T("backup_deleted"))
                except Exception:
                    pass

        if icons_list:
            try:
                builder.set_items(items, callback, icons=icons_list)
            except TypeError:
                builder.set_items(items, callback)
        else:
            builder.set_items(items, callback)

        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def share_backup_file(self, filepath):
        try:
            ctx = self._get_app_context()
            if not ctx:
                return
            File = jclass("java.io.File")
            FileProvider = jclass("androidx.core.content.FileProvider")
            file_obj = File(filepath)
            uri = FileProvider.getUriForFile(ctx, ctx.getPackageName() + ".provider", file_obj)

            intent = Intent(Intent.ACTION_SEND)
            intent.setType("application/octet-stream")
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            chooser = Intent.createChooser(intent, T("export_chooser"))
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(chooser)
        except Exception as e:
            BulletinHelper.show_error(T("export_err").format(e=e))

    def export_card(self, user_id: str, as_document: bool = False):
        with self._data_lock:
            user_data = copy.deepcopy(self.tracked_users.get(user_id))
        if not user_data:
            return

        user_data["id"] = user_id
        user_data["name"] = self.get_display_name(user_id, user_data)

        fragment = get_last_fragment()
        ctx = fragment.getParentActivity() if fragment else self._get_app_context()
        if not ctx:
            return

        progress_dialog = [None]
        try:
            from org.telegram.ui.ActionBar import AlertDialog
            pd = AlertDialog(ctx, 3)
            pd.setMessage("Генерация инфографики...")
            pd.setCanceledOnTouchOutside(False)
            pd.show()
            progress_dialog[0] = pd
        except Exception:
            try:
                BulletinHelper.show_info("Генерация инфографики...")
            except Exception:
                pass

        def _worker():
            try:
                try:
                    user_data["avatar_path"] = self.get_user_avatar_path(str(user_id))
                except Exception:
                    pass

                app_ctx = self._get_app_context() or ctx
                cache_dir = str(app_ctx.getExternalCacheDir().getAbsolutePath())
                ts_str = str(int(time.time()))
                out_path = os.path.join(cache_dir, f"omniscient_card_{user_id}_{ts_str}.png")

                saved_path = None
                if OmniscientCardRenderer:
                    card_theme = str(self.get_setting("card_theme", getattr(self, "card_theme", "dark")))
                    custom_bg = str(self.get_setting("custom_card_bg", getattr(self, "custom_card_bg", "")))
                    bg_file = custom_bg if (custom_bg and os.path.exists(custom_bg)) else None
                    renderer = OmniscientCardRenderer(res_dir=self._res_path(""))
                    saved_path = renderer.render_card(user_data, output_path=out_path, scale=2, theme=card_theme, custom_bg_path=bg_file, lang=self.get_lang_code())

                def _finish():
                    try:
                        if progress_dialog[0]:
                            progress_dialog[0].dismiss()
                    except Exception:
                        pass

                    if saved_path and os.path.exists(saved_path):
                        try:
                            File = jclass("java.io.File")
                            FileProvider = jclass("androidx.core.content.FileProvider")
                            file_obj = File(saved_path)
                            uri = FileProvider.getUriForFile(app_ctx, app_ctx.getPackageName() + ".provider", file_obj)

                            intent = Intent(Intent.ACTION_SEND)
                            intent.setType("application/octet-stream" if as_document else "image/png")
                            intent.putExtra(Intent.EXTRA_STREAM, uri)

                            caption_setting = self.get_setting("card_caption_enabled", getattr(self, "card_caption_enabled", True))
                            if isinstance(caption_setting, str):
                                caption_on = caption_setting.lower() not in ("false", "0", "no")
                            else:
                                caption_on = bool(caption_setting)

                            if caption_on:
                                name = user_data.get("name", "User")
                                uname = user_data.get("username", "")
                                tag = user_data.get("custom_tag", "")
                                stats = get_day_stats(user_data)
                                meta_parts = []
                                if uname:
                                    meta_parts.append(f"@{uname}")
                                meta_parts.append(f"ID: {user_id}")
                                if tag:
                                    meta_parts.append(f"[{tag}]")
                                meta_str = " • ".join(meta_parts)

                                is_ru = self.get_lang_code() == "ru"
                                caption = (
                                    f"📊 Omniscient Reborn • Аналитика активности\n"
                                    f"👤 {name} ({meta_str})\n"
                                    f"⏱ Онлайн: {stats['formatted_total']} • Сессий: {stats['sessions_count']} • Пик: {stats['peak_hour']}\n"
                                    f"⚡ powered by exteraGram"
                                ) if is_ru else (
                                    f"📊 Omniscient Reborn • Activity Analytics\n"
                                    f"👤 {name} ({meta_str})\n"
                                    f"⏱ Online: {stats['formatted_total']} • Sessions: {stats['sessions_count']} • Peak: {stats['peak_hour']}\n"
                                    f"⚡ powered by exteraGram"
                                )
                                intent.putExtra(Intent.EXTRA_TEXT, caption)
                            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

                            chooser = Intent.createChooser(intent, T("export_chooser"))
                            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            app_ctx.startActivity(chooser)
                            BulletinHelper.show_success(T("export_success"))
                        except Exception as e:
                            self._log_error(f"share intent err: {e}")
                            BulletinHelper.show_error(T("export_err").format(e=e))
                    else:
                        BulletinHelper.show_error("Pillow (PIL) не установлен на устройстве" if LANG == "ru" else "Pillow (PIL) not found")

                if run_on_ui_thread:
                    run_on_ui_thread(_finish)
                else:
                    _finish()
            except Exception as e:
                self._log_error(f"export_card err: {e}")
                def _err():
                    try:
                        if progress_dialog[0]:
                            progress_dialog[0].dismiss()
                    except Exception:
                        pass
                    BulletinHelper.show_error(T("export_err").format(e=e))
                if run_on_ui_thread:
                    run_on_ui_thread(_err)
                else:
                    _err()

        threading.Thread(target=_worker, daemon=True).start()

    def show_export_options(self, user_id: str):
        with self._data_lock:
            user_data = self.tracked_users.get(user_id)
        if not user_data:
            return

        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        ctx = current_fragment.getParentActivity()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title(T("export"))

        items = [T("export_csv"), T("export_txt"), T("export_msg"), T("export_card")]
        icons_list = []
        try:
            R_drawable = jclass("org.telegram.messenger.R$drawable")
            icon_csv = getattr(R_drawable, "msg_stats", 0)
            icon_txt = getattr(R_drawable, "msg_archive", 0)
            icon_msg = getattr(R_drawable, "msg_message", 0)
            icon_card = getattr(R_drawable, "msg_photo", 0) or getattr(R_drawable, "msg_gallery", 0)

            if icon_csv and icon_txt and icon_msg and icon_card:
                icons_list = [icon_csv, icon_txt, icon_msg, icon_card]
        except Exception:
            pass

        def callback(d, w):
            if w == 0:
                self.export_csv(user_id)
            elif w == 1:
                self.export_txt(user_id)
            elif w == 2:
                self.send_text_export(user_id)
            elif w == 3:
                self.export_card(user_id)

        if icons_list:
            try:
                builder.set_items(items, callback, icons=icons_list)
            except TypeError:
                builder.set_items(items, callback)
        else:
            builder.set_items(items, callback)

        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def generate_logs_content(self, user_id: str) -> str:
        with self._data_lock:
            user_data = copy.deepcopy(self.tracked_users.get(user_id))
        if not user_data:
            return ""

        tag = user_data.get("custom_tag", "")
        tag_str = f" {tag}" if tag else ""
        content = f"{T('omni_logs_title')} {self.get_display_name(user_id, user_data)}{tag_str}\n\n"

        total_time = user_data.get("total_online_time", 0)
        content += f"⏱ {T('stat_total_time')} {self.format_duration(total_time)}\n"
        content += f"👀 {T('stat_reads')} {user_data.get('total_reads', 0)}\n"
        content += f"💤 {T('stat_sleep')} {self.get_sleep_pattern(user_data)}\n"

        replied = user_data.get("loyalty_replied", 0)
        ignored = user_data.get("loyalty_ignored", 0)
        total_loyalty = replied + ignored
        loyalty_pct = int((ignored / total_loyalty) * 100) if total_loyalty > 0 else 0
        loyalty_bar = self.generate_bar(ignored, total_loyalty) if total_loyalty > 0 else "[░░░░░░░░░░]"

        content += f"📈 {T('stat_loyalty')} {loyalty_bar} {loyalty_pct}% ({T('loyalty_ignore')} {ignored})\n"

        media = user_data.get("media_stats", {})
        total_m = sum(media.values())
        if total_m > 0:
            content += f"{T('media_analysis')}\n"
            txt_count = media.get("text", 0) + media.get("other", 0)
            pho_count = media.get("photo", 0)
            vid_count = media.get("video", 0)
            vr_count = media.get("voice_round", 0) + media.get("round", 0) + media.get("voice", 0) + media.get("audio", 0)

            total_m_calc = max(1, txt_count + pho_count + vid_count + vr_count)

            pct_txt = int((txt_count / total_m_calc) * 100)
            pct_pho = int((pho_count / total_m_calc) * 100)
            pct_vid = int((vid_count / total_m_calc) * 100)
            pct_vr  = int((vr_count / total_m_calc) * 100)

            content += f"{T('media_text_other')} {pct_txt}% | {T('media_photo')} {pct_pho}%\n"
            content += f"{T('media_video')} {pct_vid}% | {T('media_voice_round')} {pct_vr}%\n\n"
        else:
            content += "\n"

        activity = user_data.get("activity_hours", [0] * 24)
        total_act = sum(activity)
        if total_act > 0:
            peak_hour = activity.index(max(activity))
            content += f"🔥 {T('stat_peak')} {peak_hour:02d}:00\n"

            night, morning, day, evening = sum(activity[0:6]), sum(activity[6:12]), sum(activity[12:18]), sum(activity[18:24])

            content += f"{T('morning')} {self.generate_bar(morning, total_act)} {int((morning/total_act)*100)}%\n"
            content += f"{T('day')} {self.generate_bar(day, total_act)} {int((day/total_act)*100)}%\n"
            content += f"{T('evening')} {self.generate_bar(evening, total_act)} {int((evening/total_act)*100)}%\n"
            content += f"{T('night')} {self.generate_bar(night, total_act)} {int((night/total_act)*100)}%\n\n"

            content += T("histogram") + "\n"
            max_val = max(activity)
            for i in range(24):
                bar = self.generate_bar(activity[i], max_val) if max_val > 0 else "▏"
                content += f"{i:02d}:00 | {bar} ({activity[i]})\n"

        sessions = user_data.get("sessions_log", [])
        if sessions:
            content += f"\n{T('sessions_log')}\n"
            for s in sessions:
                content += f"{s}\n"

        content += f"{T('full_history_title')}\n"
        for entry in user_data.get("history", []):
            content += f"[{entry.get('date', '')} {entry.get('time', '')}] {entry.get('icon', '')} {entry.get('text', '')}\n"

        return content

    def export_csv(self, user_id: str):
        with self._data_lock:
            user_data = copy.deepcopy(self.tracked_users.get(user_id))
        if not user_data:
            return

        try:
            ctx = self._get_app_context()
            if not ctx:
                return

            cache_dir = str(ctx.getExternalCacheDir().getAbsolutePath())
            out_path = os.path.join(cache_dir, f"omniscient_logs_{user_id}.csv")

            with open(out_path, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Time", "Type", "Event", "Timestamp"])
                for entry in user_data.get("history", []):
                    writer.writerow([
                        entry.get("date", ""),
                        entry.get("time", ""),
                        entry.get("icon", ""),
                        entry.get("text", ""),
                        entry.get("ts", 0)
                    ])

            File = jclass("java.io.File")
            FileProvider = jclass("androidx.core.content.FileProvider")
            file_obj = File(out_path)
            uri = FileProvider.getUriForFile(ctx, ctx.getPackageName() + ".provider", file_obj)

            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/csv")
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            chooser = Intent.createChooser(intent, T("export_chooser"))
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(chooser)
            BulletinHelper.show_success(T("export_success"))
        except Exception as e:
            BulletinHelper.show_error(T("export_err").format(e=e))

    def export_txt(self, user_id: str):
        with self._data_lock:
            user_data = self.tracked_users.get(user_id)
        if not user_data:
            return

        try:
            ctx = self._get_app_context()
            if not ctx:
                return

            content = self.generate_logs_content(user_id)
            cache_dir = str(ctx.getExternalCacheDir().getAbsolutePath())
            out_path = os.path.join(cache_dir, f"omniscient_logs_{user_id}.txt")

            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(content)

            File = jclass("java.io.File")
            FileProvider = jclass("androidx.core.content.FileProvider")
            file_obj = File(out_path)
            uri = FileProvider.getUriForFile(ctx, ctx.getPackageName() + ".provider", file_obj)

            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            chooser = Intent.createChooser(intent, T("export_chooser"))
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(chooser)
            BulletinHelper.show_success(T("export_success"))
        except Exception as e:
            self._log_error(f"export_txt err: {e}")
            BulletinHelper.show_error(T("export_err").format(e=e))

    def send_text_export(self, user_id: str):
        with self._data_lock:
            user_data = self.tracked_users.get(user_id)
        if not user_data:
            return

        try:
            content = self.generate_logs_content(user_id)
            my_id = self._get_my_id()

            max_len = 4000
            parts = [content[i:i+max_len] for i in range(0, len(content), max_len)]
            for part in parts:
                send_text(my_id, part)

            BulletinHelper.show_success(T("export_success"))
        except Exception as e:
            self._log_error(f"send_text_export err: {e}")
            BulletinHelper.show_error(T("export_err").format(e=e))

    def show_user_history(self, view: Any, user_id: str):
        with self._data_lock:
            user_data = copy.deepcopy(self.tracked_users.get(str(user_id)))
        if not user_data:
            return

        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        activity_context = current_fragment.getParentActivity()
        if not activity_context:
            return

        if OmniscientEventsSheet is not None:
            OmniscientEventsSheet.show(
                self,
                activity_context,
                str(user_id),
                user_data,
                on_export_click=lambda uid=str(user_id): self.show_export_options(uid)
            )
            return

        f_val = self.get_setting(f"filter_{user_id}", 0)
        lines = []
        name = self.get_display_name(user_id, user_data)
        tag = user_data.get("custom_tag", "")
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")

        lines.append(T("activity_title").format(date=date_str))
        lines.append("──────────────────")

        prediction = self.get_online_prediction(user_data)
        if prediction:
            lines.append(f"🔮 {prediction}")
            lines.append("──────────────────")

        total_time = user_data.get("total_online_time", 0)
        lines.append(f"{T('stat_total_time')} {self.format_duration(total_time)}")
        lines.append(f"{T('stat_reads')} {user_data.get('total_reads', 0)}")
        lines.append(f"{T('stat_sleep')} {self.get_sleep_pattern(user_data)}")

        replied = user_data.get("loyalty_replied", 0)
        ignored = user_data.get("loyalty_ignored", 0)
        total_loyalty = replied + ignored
        loyalty_pct = int((ignored / total_loyalty) * 100) if total_loyalty > 0 else 0
        loyalty_bar = self.generate_bar(ignored, total_loyalty) if total_loyalty > 0 else "[░░░░░░░░░░]"
        lines.append(f"{T('stat_loyalty')} {loyalty_bar} {loyalty_pct}% ({T('loyalty_ignore')} {ignored})")

        media = user_data.get("media_stats", {})
        total_m = sum(media.values())
        if total_m > 0:
            lines.append(T("media_analysis"))
            txt_count = media.get("text", 0) + media.get("other", 0)
            pho_count = media.get("photo", 0)
            vid_count = media.get("video", 0)
            vr_count = media.get("voice_round", 0) + media.get("round", 0) + media.get("voice", 0) + media.get("audio", 0)
            total_m_calc = max(1, txt_count + pho_count + vid_count + vr_count)
            pct_txt = int((txt_count / total_m_calc) * 100)
            pct_pho = int((pho_count / total_m_calc) * 100)
            pct_vid = int((vid_count / total_m_calc) * 100)
            pct_vr  = int((vr_count / total_m_calc) * 100)
            lines.append(f"{T('media_text_other')} {pct_txt}% | {T('media_photo')} {pct_pho}%")
            lines.append(f"{T('media_video')} {pct_vid}% | {T('media_voice_round')} {pct_vr}%\n")
        else:
            lines.append("")

        lines.append(T("sessions_log"))
        lines.append("──────────────────")
        sessions = user_data.get("sessions_log", [])
        if user_data.get("last_type") == "online":
            start_str = datetime.fromtimestamp(user_data.get("last_ts", 0)).strftime("%H:%M:%S")
            if f_val in [0, 1]:
                lines.append(T("online_status_history").format(time=start_str))
        is_ru = self.get_lang_code() == "ru"
        try:
            from .ui.sheet import translate_event_text, translate_duration_str
        except Exception:
            try:
                from ui.sheet import translate_event_text, translate_duration_str
            except Exception:
                translate_event_text = lambda t, r: t
                translate_duration_str = lambda d, r: d

        if sessions:
            for s in reversed(sessions[-10:]):
                if f_val in [0, 1]:
                    lines.append(translate_duration_str(s, is_ru))
        elif user_data.get("last_type") != "online":
            if f_val in [0, 1]:
                lines.append(T("empty_history"))

        lines.append(T("session_interrupted_note"))
        lines.append("\n" + T("other_events"))
        lines.append("──────────────────")
        history = user_data.get("history", [])
        filtered_events = [e for e in history if e.get("type") not in ("online", "offline")]

        folded_lines = []
        micro_count = 0
        micro_start = ""

        for e in filtered_events:
            ev_text = translate_event_text(e.get('text', ''), is_ru)
            text = f"{e['time']} {e['icon']} {ev_text}"
            icon = e["icon"]
            if icon == "⚡" or e.get("type") == "micro_session":
                if micro_count == 0:
                    micro_start = e["time"]
                micro_count += 1
                micro_end = e["time"]
            else:
                if micro_count > 0:
                    if micro_count == 1:
                        folded_lines.append(T("micro_session_1").format(time=micro_end))
                    else:
                        folded_lines.append(T("micro_session_n").format(time=micro_end, count=micro_count, start=micro_start))
                    micro_count = 0
                show = False
                if f_val == 0:
                    show = True
                elif f_val == 2 and icon in ["📝"]:
                    show = True
                elif f_val == 3 and icon in ["✔️", "👁"]:
                    show = True
                elif f_val == 4 and icon in ["🚫", "🙈"]:
                    show = True
                if show:
                    folded_lines.append(text)

        if micro_count > 0:
            if micro_count == 1:
                folded_lines.append(T("micro_session_1").format(time=micro_end))
            else:
                folded_lines.append(T("micro_session_n").format(time=micro_end, count=micro_count, start=micro_start))

        if folded_lines:
            for line in reversed(folded_lines[-50:]):
                lines.append(line)
        else:
            if f_val != 1:
                lines.append(T("history_empty"))

        dialog_text = "\n".join(lines)

        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        activity_context = current_fragment.getParentActivity()
        if not activity_context:
            return

        builder = AlertDialogBuilder(activity_context)
        title = f"{name} {tag}" if tag else f"📊 {name}"
        builder.set_title(title)
        builder.set_message(dialog_text[:4000])
        builder.set_positive_button(T("ok"), lambda d, w: None)
        builder.set_neutral_button(T("export"), lambda d, w, uid=user_id: self.show_export_options(uid))
        builder.show()

    def update_wakelock_setting(self, checked: bool):
        if checked:
            fragment = get_last_fragment()
            if fragment and fragment.getParentActivity():
                ctx = fragment.getParentActivity()
                builder = AlertDialogBuilder(ctx)
                is_ru = self.get_lang_code() == "ru"
                title = "Фоновый режим (WakeLock)" if is_ru else "Background Mode (WakeLock)"
                msg = (
                    "WakeLock удерживает процессор активным, чтобы Telegram и плагин продолжали отслеживать активность даже при выключенном экране.\n\n"
                    "⚠️ Внимание:\n"
                    "Непрерывная работа в фоне повышает энергопотребление и может значительно увеличить расход заряда аккумулятора.\n\n"
                    "Включить WakeLock?"
                ) if is_ru else (
                    "WakeLock keeps the CPU active so Telegram and the plugin continue monitoring contact activity even with the screen turned off.\n\n"
                    "⚠️ Warning:\n"
                    "Continuous background execution increases power consumption and may significantly drain battery life.\n\n"
                    "Enable WakeLock?"
                )
                builder.set_title(title)
                builder.set_message(msg)

                confirmed = [False]

                def on_confirm(d, w):
                    confirmed[0] = True
                    self.keep_alive_wakelock = True
                    self._acquire_wakelock()
                    self.set_setting("keep_alive_wakelock", True, reload_settings=False)
                    BulletinHelper.show_success(T("wakelock_enabled"))

                def on_dismiss_or_cancel(*args):
                    if not confirmed[0]:
                        self.keep_alive_wakelock = False
                        self._release_wakelock()
                        self.set_setting("keep_alive_wakelock", False, reload_settings=True)

                builder.set_positive_button(T("btn_confirm"), on_confirm)
                builder.set_negative_button(T("cancel"), on_dismiss_or_cancel)

                for dismiss_meth in ("set_on_dismiss_listener", "setOnDismissListener"):
                    if hasattr(builder, dismiss_meth):
                        try:
                            getattr(builder, dismiss_meth)(on_dismiss_or_cancel)
                        except Exception:
                            pass
                for cancel_meth in ("set_on_cancel_listener", "setOnCancelListener"):
                    if hasattr(builder, cancel_meth):
                        try:
                            getattr(builder, cancel_meth)(on_dismiss_or_cancel)
                        except Exception:
                            pass

                builder.show()
                return

        self.keep_alive_wakelock = False
        self._release_wakelock()
        self.set_setting("keep_alive_wakelock", False, reload_settings=False)
        BulletinHelper.show_success(T("wakelock_disabled"))

    def create_tracking_sub(self) -> List[Any]:
        return [
            Switch(key="track_online", text=T("track_online"), default=self.track_online, icon="msg_openprofile", on_change=lambda c: self.update_setting("track_online", c)),
            Switch(key="track_read", text=T("track_read"), default=self.track_read, icon="msg_message", on_change=lambda c: self.update_setting("track_read", c)),
            Switch(key="track_name", text=T("track_name"), default=self.track_name, icon="msg_edit", on_change=lambda c: self.update_setting("track_name", c)),
            Switch(key="track_typing", text=T("track_typing"), default=getattr(self, "track_typing", True), icon="msg_edit", on_change=lambda c: self.update_setting("track_typing", c)),
            Custom(item=UItem.asShadow(T("basic_tracking_params")))
        ]

    def update_master_track(self, checked: bool):
        self.master_track = checked
        self.set_setting("master_track", self.master_track, reload_settings=False)
        if not checked:
            self.set_setting("saved_track_online", self.track_online)
            self.set_setting("saved_track_read", self.track_read)
            self.set_setting("saved_track_name", self.track_name)
            self.set_setting("saved_track_typing", getattr(self, "track_typing", True))
            self.track_online = False
            self.track_read = False
            self.track_name = False
            self.track_typing = False
        else:
            self.track_online = self._get_bool("saved_track_online", True)
            self.track_read = self._get_bool("saved_track_read", True)
            self.track_name = self._get_bool("saved_track_name", True)
            self.track_typing = self._get_bool("saved_track_typing", True)

        self.set_setting("track_online", self.track_online)
        self.set_setting("track_read", self.track_read)
        self.set_setting("track_name", self.track_name)
        self.set_setting("track_typing", self.track_typing, reload_settings=True)

    def update_master_notify(self, checked: bool):
        self.master_notify = checked
        self.set_setting("master_notify", self.master_notify, reload_settings=False)
        if not checked:
            self.set_setting("saved_notify_online", self.notify_online)
            self.set_setting("saved_notify_offline", self.notify_offline)
            self.set_setting("saved_notify_read", self.notify_read)
            self.set_setting("saved_notify_name", self.notify_name)
            self.notify_online = False
            self.notify_offline = False
            self.notify_read = False
            self.notify_name = False
        else:
            self.notify_online = self._get_bool("saved_notify_online", True)
            self.notify_offline = self._get_bool("saved_notify_offline", True)
            self.notify_read = self._get_bool("saved_notify_read", True)
            self.notify_name = self._get_bool("saved_notify_name", True)

        self.set_setting("notify_online", self.notify_online)
        self.set_setting("notify_offline", self.notify_offline)
        self.set_setting("notify_read", self.notify_read)
        self.set_setting("notify_name", self.notify_name, reload_settings=True)

    def create_notify_sub(self) -> List[Any]:
        return [
            Switch(key="notify_in_app", text=T("notify_in_app"), default=getattr(self, "notify_in_app", True), icon="msg_channel", on_change=lambda c: self.update_setting("notify_in_app", c)),
            Switch(key="notify_system", text=T("notify_system"), default=getattr(self, "notify_system", True), icon="msg_notifications", on_change=lambda c: self.update_setting("notify_system", c)),
            Switch(key="notify_hyperbridge", text=T("notify_hyperbridge"), default=getattr(self, "notify_hyperbridge", False), icon="msg_calls", on_change=lambda c: self.update_setting("notify_hyperbridge", c)),
            Custom(item=UItem.asShadow(T("hyperbridge_beta_warning"))),
            Divider(),
            Switch(key="notify_online", text=T("notify_online"), default=self.notify_online, icon="msg_openprofile", on_change=lambda c: self.update_setting("notify_online", c)),
            Switch(key="notify_offline", text=T("notify_offline"), default=self.notify_offline, icon="msg_leave", on_change=lambda c: self.update_setting("notify_offline", c)),
            Switch(key="notify_read", text=T("notify_read"), default=self.notify_read, icon="msg_message", on_change=lambda c: self.update_setting("notify_read", c)),
            Switch(key="notify_name", text=T("notify_name"), default=self.notify_name, icon="msg_edit", on_change=lambda c: self.update_setting("notify_name", c))
        ]

    def update_user_notify(self, uid: str, checked: bool):
        with self._data_lock:
            if uid in self.tracked_users:
                self.tracked_users[uid]["notifications_enabled"] = checked
        self._save_users()

    def update_user_tag(self, uid: str, value: str):
        with self._data_lock:
            if uid in self.tracked_users:
                self.tracked_users[uid]["custom_tag"] = value
        self._save_users()

    def update_user_pin(self, uid: str, checked: bool):
        with self._data_lock:
            if uid in self.tracked_users:
                self.tracked_users[uid]["is_pinned"] = checked
        self._save_users()

    def update_user_local_name(self, uid: str, value: str):
        with self._data_lock:
            if uid in self.tracked_users:
                self.tracked_users[uid]["local_name"] = value
        self._save_users()

    def clear_logs(self, uid: str):
        with self._data_lock:
            if uid not in self.tracked_users:
                return

        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        ctx = current_fragment.getParentActivity()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title(T("clear_title"))
        builder.set_message(T("clear_msg"))

        def on_confirm(dialog, which):
            with self._data_lock:
                if uid in self.tracked_users:
                    self.tracked_users[uid]["history"] = []
                    self.tracked_users[uid]["sessions_log"] = []
                    self.tracked_users[uid]["activity_hours"] = [0] * 24
                    self.tracked_users[uid]["total_online_time"] = 0
                    self.tracked_users[uid]["total_reads"] = 0
                    self.tracked_users[uid]["loyalty_ignored"] = 0
                    self.tracked_users[uid]["loyalty_replied"] = 0
                    self.tracked_users[uid]["media_stats"] = {}
            self._save_users()
            self.set_setting(f"last_clear_{uid}", int(time.time()), reload_settings=True)
            BulletinHelper.show_success(T("logs_cleared"))

        builder.set_positive_button(T("btn_clear"), on_confirm)
        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def remove_user(self, uid: str):
        with self._data_lock:
            if uid not in self.tracked_users:
                return

        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        ctx = current_fragment.getParentActivity()
        if not ctx:
            return

        builder = AlertDialogBuilder(ctx)
        builder.set_title(T("delete_title"))
        builder.set_message(T("delete_msg"))

        def on_confirm(dialog, which):
            with self._data_lock:
                if uid in self.tracked_users:
                    del self.tracked_users[uid]
            self._save_users_sync()
            BulletinHelper.show_success(T("removed"))
            fragment = get_last_fragment()
            if fragment:
                fragment.finishFragment()

        builder.set_positive_button(T("btn_delete"), on_confirm)
        builder.set_negative_button(T("cancel"), lambda d, w: None)
        builder.show()

    def create_user_settings(self, uid: str) -> List[Any]:
        with self._data_lock:
            data = copy.deepcopy(self.tracked_users.get(uid, {}))
        name = self.get_display_name(uid, data)
        tag = data.get("custom_tag", "")
        data["id"] = uid
        data["name"] = name

        fragment = get_last_fragment()
        ctx = fragment.getParentActivity() if fragment else None
        settings = []

        if ctx and OmniscientContactCardWidget:
            card_view = OmniscientContactCardWidget.create_card_view(
                plugin=self,
                ctx=ctx,
                user_data=data
            )
            if card_view:
                settings.append(Custom(view=card_view))
                settings.append(Divider())

        is_ru = self.get_lang_code() == "ru"

        settings.append(Header(text="Инфографика и экспорт" if is_ru else "Infographics & Export"))
        settings.append(Text(
            text="Инфографика: Фото" if is_ru else "Infographic: Photo",
            subtext="Сгенерировать и отправить" if is_ru else "Generate and send",
            icon="msg_gallery",
            on_click=lambda *a, u=uid: self.export_card(u, as_document=False)
        ))
        settings.append(Text(
            text="Инфографика: Файл без сжатия" if is_ru else "Infographic: Uncompressed File",
            subtext="Отправить как документ в оригинале" if is_ru else "Send as original document",
            icon="msg_gallery",
            on_click=lambda *a, u=uid: self.export_card(u, as_document=True)
        ))
        is_light = str(self.get_setting("card_theme", getattr(self, "card_theme", "dark"))).lower() == "light"
        theme_title = ("Светлая" if is_light else "Тёмная") if is_ru else ("Light" if is_light else "Dark")
        settings.append(Text(
            text="Тема инфографики" if is_ru else "Infographic Theme",
            subtext=(f"Текущая: {theme_title}") if is_ru else (f"Current: {theme_title}"),
            icon="msg_theme",
            on_click=lambda *a: self.show_card_theme_dialog()
        ))
        curr_bg = str(self.get_setting("custom_card_bg", getattr(self, "custom_card_bg", "")))
        has_custom_bg = bool(curr_bg and os.path.exists(curr_bg))
        bg_subtext = ("Пользовательское фото" if has_custom_bg else "Стандартный градиент") if is_ru else ("Custom photo" if has_custom_bg else "Default gradient")
        settings.append(Text(
            text="Фон инфографики" if is_ru else "Infographic Background",
            subtext=(f"Текущий: {bg_subtext}") if is_ru else (f"Current: {bg_subtext}"),
            icon="msg_gallery",
            on_click=lambda *a: self.show_card_bg_dialog()
        ))
        settings.append(Switch(
            key="card_caption_enabled",
            text="Подпись к инфографике" if is_ru else "Infographic Caption",
            subtext="Добавлять текстовую сводку при экспорте" if is_ru else "Add text summary when exporting",
            default=self._get_bool("card_caption_enabled", getattr(self, "card_caption_enabled", True)),
            icon="msg_edit",
            on_change=lambda c: self._on_card_caption_change(c)
        ))
        settings.append(Text(
            text=T("export"),
            icon="msg_share",
            on_click=lambda *a, u=uid: self.show_export_options(u)
        ))
        settings.append(Divider())

        settings.append(Header(text="История и аналитика" if is_ru else "History & Analytics"))
        settings.append(Text(
            text=T("view_stats"),
            icon="msg_stats",
            on_click=lambda *a, u=uid: self.show_user_history(None, u)
        ))
        settings.append(Selector(
            key=f"filter_{uid}",
            text=T("log_filter"),
            default=0,
            items=[T("filter_all"), T("filter_network"), T("filter_messages"), T("filter_reads"), T("filter_other")],
            icon="msg_list",
            on_change=lambda c: self.update_setting(f"filter_{uid}", c, reload=False)
        ))
        settings.append(Divider())

        settings.append(Header(text="Параметры контакта" if is_ru else "Contact Settings"))
        settings.append(Text(
            text="Синхронизировать имя из Telegram" if is_ru else "Sync Name from Telegram",
            subtext="Обновить имя и юзернейм" if is_ru else "Update name and username",
            icon="msg_retry",
            on_click=lambda *a, u=uid: self.sync_contact_names(u)
        ))
        settings.append(Input(
            key=f"local_name_{uid}",
            text=T("local_name"),
            default=data.get("local_name", ""),
            icon="msg_edit",
            on_change=lambda c, u=uid: self.update_user_local_name(u, c)
        ))
        settings.append(Input(
            key=f"tag_{uid}",
            text=T("custom_tag"),
            default=tag,
            icon="msg_edit",
            on_change=lambda c, u=uid: self.update_user_tag(u, c)
        ))
        settings.append(Switch(
            key=f"pin_{uid}",
            text=T("pin_user"),
            default=data.get("is_pinned", False),
            icon="msg_pin",
            on_change=lambda c, u=uid: self.update_user_pin(u, c)
        ))
        settings.append(Switch(
            key=f"notify_{uid}",
            text=T("notifications_toggle"),
            default=data.get("notifications_enabled", True),
            icon="msg_notifications",
            on_change=lambda c, u=uid: self.update_user_notify(u, c)
        ))
        settings.append(Divider())

        settings.append(Header(text="Действия" if is_ru else "Actions"))
        settings.append(Text(
            text=T("clear"),
            icon="msg_clearcache",
            red=True,
            on_click=lambda v, u=uid: self.clear_logs(u)
        ))
        settings.append(Text(
            text=T("remove_user"),
            icon="msg_delete",
            red=True,
            on_click=lambda v, u=uid: self.remove_user(u)
        ))
        return settings

    def create_contacts_menu(self) -> List[Any]:
        settings = []
        is_ru = self.get_lang_code() == "ru"
        with self._data_lock:
            users_snapshot = list(self.tracked_users.items())

        if not users_snapshot:
            settings.append(Custom(item=UItem.asShadow(T("stats_empty_hint"))))
        else:
            settings.append(Text(
                text="Синхронизировать имена контактов" if is_ru else "Sync Contact Names",
                subtext="Обновить имена и юзернеймы всех контактов из Telegram" if is_ru else "Update names and usernames from Telegram",
                icon="msg_retry",
                on_click=lambda *a: self.sync_contact_names()
            ))
            settings.append(Divider())

            sorted_users = sorted(users_snapshot, key=lambda item: item[1].get("is_pinned", False), reverse=True)
            for uid, data in sorted_users:
                name = self.get_display_name(uid, data)
                tag = data.get("custom_tag", "")
                tag_str = f" [{tag}]" if tag else ""
                is_pinned = data.get("is_pinned", False)

                is_online = data.get("last_type") == "online" or data.get("last_status") == "online"
                st_label = ("В сети" if is_online else "Оффлайн") if is_ru else ("Online" if is_online else "Offline")

                tot_sec = int(data.get("total_online_time", 0))
                dur_str = tl_format_dur(tot_sec) if tl_format_dur else (f"{tot_sec // 60}м" if is_ru else f"{tot_sec // 60}m")
                ev_count = len(data.get("history", []))

                sub_info = f"{st_label} • Онлайн: {dur_str} • Событий: {ev_count}" if is_ru else f"{st_label} • Online: {dur_str} • Events: {ev_count}"
                user_icon = "msg_pin" if is_pinned else "msg_openprofile"

                settings.append(Text(
                    text=f"{name}{tag_str}",
                    subtext=sub_info,
                    icon=user_icon,
                    create_sub_fragment=lambda u=uid: self.create_user_settings(u)
                ))
        return settings

    def copy_text(self, text: str, success_msg: str = None):
        try:
            from org.telegram.messenger import AndroidUtilities
            AndroidUtilities.addToClipboard(text)
            BulletinHelper.show_success(success_msg or T("link_copied"))
        except Exception:
            try:
                ctx = self._get_app_context()
                if ctx:
                    cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE)
                    ClipData = jclass("android.content.ClipData")
                    clip = ClipData.newPlainText("Telegram", text)
                    cm.setPrimaryClip(clip)
                    BulletinHelper.show_success(success_msg or T("link_copied"))
            except Exception as e:
                self._log_error(f"Copy text err: {e}")

    def share_link(self, domain: str):
        try:
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_TEXT, f"https://t.me/{domain}")
            chooser = Intent.createChooser(intent, T("share_link_title"))
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ApplicationLoader.applicationContext.startActivity(chooser)
        except Exception as e:
            self._log_error(f"share_link err: {e}")

    def on_link_long_click(self, domain: str) -> bool:
        try:
            fragment = get_last_fragment()
            if not fragment:
                return True
            ctx = fragment.getParentActivity()
            if not ctx:
                return True

            builder = AlertDialogBuilder(ctx)

            icons = None
            try:
                R_drawable = jclass("org.telegram.messenger.R$drawable")
                copy_icon = getattr(R_drawable, "msg_copy", 0)
                share_icon = getattr(R_drawable, "msg_share", 0)

                if copy_icon and share_icon:
                    icons = [copy_icon, share_icon]
            except Exception:
                pass

            def menu_callback(d, w):
                if w == 0:
                    self.copy_text(f"https://t.me/{domain}")
                else:
                    self.share_link(domain)

            if icons:
                try:
                    builder.set_items([T("copy_link"), T("share_link")], menu_callback, icons=icons)
                except TypeError:
                    builder.set_items([T("copy_link"), T("share_link")], menu_callback)
            else:
                builder.set_items([T("copy_link"), T("share_link")], menu_callback)

            builder.show()
        except Exception as e:
            self._log_error(f"on_link_long_click err: {e}")
        return True

    def create_settings(self) -> List[Any]:
        settings = []
        fragment = get_last_fragment()
        ctx = fragment.getParentActivity() if fragment else None

        if not self._get_bool("onboarding_completed", False) and ctx and OmniWelcomeUI:
            welcome_view = OmniWelcomeUI.create_welcome_view(
                plugin=self,
                ctx=ctx,
                on_continue_click=self.complete_onboarding
            )
            if welcome_view:
                settings.append(Custom(view=welcome_view))
                return settings

        with self._data_lock:
            tracked_count = len(self.tracked_users)

        hero_banner = None
        if ctx and HeroHeaderUI:
            try:
                hero_banner = HeroHeaderUI.create_hero_banner(
                    self,
                    ctx,
                    on_add_click=self.prompt_add_user_id,
                    on_export_click=self.export_backup
                )
            except Exception as e:
                self._log_error(f"Settings hero banner err: {e}")

        if hero_banner:
            settings.append(Custom(view=hero_banner))

        is_ru = self.get_lang_code() == "ru"

        settings.append(Header(text="Omniscient Reborn"))
        count_text = f" ({tracked_count})" if tracked_count > 0 else ""
        settings.append(Text(
            text=f"{T('tracked_list')}{count_text}",
            subtext="Управление отслеживаемыми контактами" if is_ru else "Manage tracked contacts",
            icon="msg_contacts",
            create_sub_fragment=self.create_contacts_menu
        ))
        settings.append(Input(
            key="add_contact_input",
            text="Добавить по ID или @username" if is_ru else "Add by ID or @username",
            default="",
            icon="msg_addcontact",
            on_change=self.handle_add_contact_input
        ))
        settings.append(Divider())

        settings.append(Header(text=T("master_observation_header")))
        settings.append(Switch(key="master_track", text=T("master_observation"), default=self.master_track, icon="msg_settings", on_change=self.update_master_track))
        settings.append(Text(text=T("track_observation"), icon="msg_openprofile", create_sub_fragment=self.create_tracking_sub))

        settings.append(Header(text=T("master_notifications_header")))
        settings.append(Switch(key="master_notify", text=T("master_notifications"), default=self.master_notify, icon="msg_notifications", on_change=self.update_master_notify))
        settings.append(Text(text=T("track_notifications"), icon="msg_list", create_sub_fragment=self.create_notify_sub))

        settings.append(Header(text=T("logs_title")))

        settings.append(Switch(key="keep_alive_wakelock", text=T("wakelock"), default=getattr(self, "keep_alive_wakelock", False), icon="msg_link", on_change=self.update_wakelock_setting))
        settings.append(Input(key="max_logs", text=T("max_logs"), default=str(self.max_logs), icon="msg_info", on_change=self.update_max_logs))
        settings.append(Input(key="auto_clean_days", text=T("auto_clean_days"), default=str(getattr(self, "auto_clean_days", "7")), icon="msg_clearcache", on_change=lambda c: self.update_days_setting("auto_clean_days", c, 7)))

        settings.append(Header(text=T("backup_header")))
        settings.append(Switch(key="auto_backup_enabled", text=T("auto_backup"), default=getattr(self, "auto_backup_enabled", False), icon="msg_settings", on_change=lambda c: self.update_setting("auto_backup_enabled", c, reload=False)))
        settings.append(Input(key="auto_backup_days", text=T("auto_backup_days"), default=str(getattr(self, "auto_backup_days", "7")), icon="msg_calendar", on_change=lambda c: self.update_days_setting("auto_backup_days", c, 7)))
        settings.append(Text(text=T("test_auto_backup"), icon="msg_message", on_click=self.force_test_backup))
        settings.append(Custom(item=UItem.asShadow(T("auto_backup_desc"))))
        settings.append(Text(text=T("export_backup"), icon="msg_share", on_click=self.export_backup))
        settings.append(Text(text=T("import_backup"), icon="msg_download", on_click=self.import_backup))
        settings.append(Text(text=T("restore_auto_backup"), icon="msg_archive", on_click=self.restore_auto_backup))
        settings.append(Text(text=T("open_backup_folder"), icon="msg_list", on_click=self.open_backup_folder))

        try:
            import sys
            f_val = globals().get("__file__")
            curr_dir = os.path.dirname(os.path.abspath(f_val)) if f_val else ""
            for base_dir in [
                curr_dir,
                os.path.dirname(curr_dir) if curr_dir else "",
                os.path.dirname(os.path.dirname(curr_dir)) if curr_dir else ""
            ]:
                if base_dir and base_dir not in sys.path:
                    sys.path.insert(0, base_dir)

            loader_mod = None
            try:
                import loader as loader_mod
            except Exception:
                try:
                    from . import loader as loader_mod
                except Exception:
                    pass

            gh_loader = getattr(loader_mod, "OmniGitHubLoader", None) if loader_mod else None
            if not gh_loader:
                try:
                    from loader import OmniGitHubLoader as gh_loader
                except Exception:
                    pass

            if gh_loader:
                settings.append(Header(text="Обновления" if is_ru else "Updates"))
                settings.append(Switch(
                    key="auto_check_updates",
                    text="Автопроверка обновлений" if is_ru else "Auto-check updates",
                    default=True,
                    subtext="Уведомлять при появлении нового релиза" if is_ru else "Notify when a new release is available",
                    icon="msg_info"
                ))
                settings.append(Text(
                    text="Проверить обновления" if is_ru else "Check for updates",
                    subtext=(f"У вас установлена последняя версия (v{getattr(self, '__version__', '2.0.0')})" if is_ru else f"You have the latest version (v{getattr(self, '__version__', '2.0.0')})"),
                    icon="msg_retry",
                    on_click=lambda *a, l=gh_loader: l.check_for_updates(self, ctx, notify_if_latest=True)
                ))
                settings.append(Text(
                    text="Загрузчик версий" if is_ru else "Version Loader",
                    subtext="Открыть список релизов и установить нужную версию" if is_ru else "Open release list and install a version",
                    icon="msg_download",
                    on_click=lambda *a, l=gh_loader: l.show_releases_dialog(self, ctx)
                ))
        except Exception as e:
            self._log_error(f"GitHub loader settings error: {e}")

        settings.append(Header(text=T("about_dev")))

        settings.append(Text(
            text=T("plugin_channel"),
            subtext="@neo_plugin",
            icon="msg_channel",
            on_click=lambda v: self.open_tg_link("neo_plugin"),
            on_long_click=lambda v: self.on_link_long_click("neo_plugin")
        ))

        settings.append(Text(
            text=T("contact_me"),
            subtext="@mrneoner",
            icon="msg_openprofile",
            on_click=lambda v: self.open_tg_link("mrneoner"),
            on_long_click=lambda v: self.on_link_long_click("mrneoner")
        ))

        settings.append(Text(
            text=T("special_thanks"),
            subtext="@xindor_apps",
            icon="msg_channel",
            on_click=lambda v: self.open_tg_link("xindor_apps"),
            on_long_click=lambda v: self.on_link_long_click("xindor_apps")
        ))

        if hasattr(self, 'error_logs') and len(self.error_logs) > 0:
            settings.append(Header(text=T("debug_header")))
            settings.append(Text(text=T("debug_errors_count").format(count=len(self.error_logs)), subtext=T("debug_copy_subtext"), icon="msg_copy", on_click=self._copy_logs))

        settings.append(Header(text=T("danger_zone")))
        settings.append(Text(
            text=T("factory_reset"),
            subtext=T("factory_reset_desc"),
            icon="msg_delete",
            red=True,
            on_click=self.factory_reset
        ))
        settings.append(Divider())
        settings.append(Text(
            text=f"v{__version__}",
            icon="msg_info",
            on_click=self.on_version_click,
            on_long_click=self.on_version_long_click
        ))

        return settings

    def update_max_logs(self, value: str):
        try:
            max_l = int(value)
            if max_l < 1:
                max_l = 1
        except ValueError:
            max_l = 400

        self.max_logs = str(max_l)
        changed = False
        now_ts = time.time()

        with self._data_lock:
            for uid, data in list(self.tracked_users.items()):
                history = data.get("history", [])
                sessions = data.get("sessions_log", [])

                if "hidden_ts" in data and (now_ts - data["hidden_ts"] > 1800):
                    data.pop("hidden_history", None)
                    data.pop("hidden_sessions", None)
                    data.pop("hidden_ts", None)
                    changed = True

                if max_l < len(history) or max_l < len(sessions):
                    if "hidden_history" not in data or max_l < len(data.get("history", [])):
                        data["hidden_history"] = history.copy()
                        data["hidden_sessions"] = sessions.copy()
                        data["hidden_ts"] = now_ts

                    data["history"] = history[-max_l:]
                    data["sessions_log"] = sessions[-max_l:]
                    changed = True
                elif max_l > len(history) and "hidden_history" in data:
                    if now_ts - data.get("hidden_ts", 0) <= 1800:
                        full_history = data["hidden_history"] + history
                        seen = set()
                        merged_h = []
                        for ev in full_history:
                            ts_val = ev.get('ts', 0)
                            if ts_val not in seen:
                                seen.add(ts_val)
                                merged_h.append(ev)
                        merged_h.sort(key=lambda x: x.get('ts', 0))
                        data["history"] = merged_h[-max_l:]

                        full_sess = data.get("hidden_sessions", []) + sessions
                        seen_s = set()
                        merged_s = []
                        for s in full_sess:
                            if s not in seen_s:
                                seen_s.add(s)
                                merged_s.append(s)
                        data["sessions_log"] = merged_s[-max_l:]
                        changed = True
                    else:
                        data.pop("hidden_history", None)
                        data.pop("hidden_sessions", None)
                        data.pop("hidden_ts", None)
                        changed = True

        if changed:
            self._save_users()

        self.set_setting("max_logs", str(max_l), reload_settings=False)

    def on_version_click(self, view: Any):
        current_fragment = get_last_fragment()
        if not current_fragment:
            return
        ctx = current_fragment.getParentActivity()
        if not ctx:
            return
        if OmniWelcomeUI:
            OmniWelcomeUI.show_changelog_sheet(self, ctx)

    def on_version_long_click(self, view: Any):
        try:
            is_ru = self.get_lang_code() == "ru"
            BulletinHelper.show_success("Приветственный экран открыт" if is_ru else "Welcome screen opened")
            self.reset_onboarding()
        except Exception as e:
            self._log_error(f"on_version_long_click err: {e}")
        return True

    def update_days_setting(self, key: str, value: str, default_val: int):
        try:
            val = int(value)
            if val < 1:
                val = 1
        except ValueError:
            val = default_val

        setattr(self, key, str(val))
        self.set_setting(key, str(val), reload_settings=False)

    def update_setting(self, key, value, reload: bool = False):
        setattr(self, key, value)
        self.set_setting(key, value, reload_settings=reload)
