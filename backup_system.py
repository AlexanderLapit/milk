# backup.py
import os
import shutil
import json
from datetime import datetime
import time
from pathlib import Path

# Константы
BACKUP_LOG_FILE = 'backups/backup_log.json'
DEFAULT_DB_PATH = 'database.db'


def ensure_backup_dirs():
    """Создаёт необходимые директории для бэкапов."""
    os.makedirs('backups/full', exist_ok=True)
    os.makedirs('backups/incremental', exist_ok=True)
    os.makedirs('backups/differential', exist_ok=True)


def get_timestamp():
    """Возвращает текущую метку времени в формате YYYYMMDD_HHMMSS."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def get_iso_timestamp():
    """Возвращает текущую метку времени в формате ISO."""
    return datetime.now().isoformat()


def read_backup_log():
    """Загружает журнал бэкапов из файла."""
    ensure_backup_dirs()

    if not os.path.exists(BACKUP_LOG_FILE):
        return []

    try:
        with open(BACKUP_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_backup_log(log_entries):
    """Сохраняет журнал бэкапов в файл."""
    ensure_backup_dirs()

    with open(BACKUP_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log_entries, f, indent=2, ensure_ascii=False)


def log_backup(backup_type, filename, path):
    """
    Добавляет запись о бэкапе в журнал.

    Args:
        backup_type (str): Тип бэкапа ('full', 'incremental', 'differential')
        filename (str): Имя файла бэкапа
        path (str): Полный путь к файлу бэкапа
    """
    log_entries = read_backup_log()

    log_entry = {
        "type": backup_type,
        "timestamp": get_iso_timestamp(),
        "filename": filename,
        "path": path
    }

    log_entries.append(log_entry)
    save_backup_log(log_entries)


def get_last_full_backup_time():
    """
    Читает лог и возвращает время последнего полного бэкапа.

    Returns:
        float: Временная метка Unix последнего полного бэкапа или None
    """
    log_entries = read_backup_log()

    # Ищем все полные бэкапы
    full_backups = [entry for entry in log_entries if entry.get('type') == 'full']

    if not full_backups:
        return None

    # Берём последний по времени
    last_full = max(full_backups, key=lambda x: x['timestamp'])

    # Преобразуем ISO timestamp в Unix timestamp
    dt = datetime.fromisoformat(last_full['timestamp'])
    return dt.timestamp()


def get_last_backup_time():
    """
    Читает лог и возвращает время последнего бэкапа (любого типа).

    Returns:
        float: Временная метка Unix последнего бэкапа или None
    """
    log_entries = read_backup_log()

    if not log_entries:
        return None

    # Берём последнюю запись по времени
    last_backup = max(log_entries, key=lambda x: x['timestamp'])

    dt = datetime.fromisoformat(last_backup['timestamp'])
    return dt.timestamp()


def full_backup(db_path=DEFAULT_DB_PATH, backup_dir="backups/full"):
    """
    Создаёт полную резервную копию базы данных.

    Args:
        db_path (str): Путь к файлу базы данных
        backup_dir (str): Директория для сохранения бэкапа

    Returns:
        tuple: (success, msg) где success - bool, msg - строка с результатом
    """
    ensure_backup_dirs()

    # Проверяем существование файла БД
    if not os.path.exists(db_path):
        return False, f"❌ Файл базы данных не найден: {db_path}"

    # Создаём имя файла
    timestamp = get_timestamp()
    filename = f"full_{timestamp}.db"
    backup_path = os.path.join(backup_dir, filename)

    try:
        # Копируем файл
        shutil.copy2(db_path, backup_path)
        msg = f"✅ Полный бэкап создан: {backup_path}"

        # Логируем
        log_backup('full', filename, backup_path)

        return True, msg
    except Exception as e:
        return False, f"❌ Ошибка при создании полного бэкапа: {e}"


def incremental_backup(db_path=DEFAULT_DB_PATH, last_backup_time=None, backup_dir="backups/incremental"):
    """
    Создаёт инкрементальную резервную копию, если файл БД изменился.

    Args:
        db_path (str): Путь к файлу базы данных
        last_backup_time (float): Время последнего бэкапа (Unix timestamp)
        backup_dir (str): Директория для сохранения бэкапа

    Returns:
        tuple: (success, msg) где success - bool, msg - строка с результатом
    """
    ensure_backup_dirs()

    # Проверяем существование файла БД
    if not os.path.exists(db_path):
        return False, f"❌ Файл базы данных не найден: {db_path}"

    # Если время не указано, получаем время последнего бэкапа из лога
    if last_backup_time is None:
        last_backup_time = get_last_backup_time()

    # Если нет информации о предыдущих бэкапах, предлагаем сделать полный
    if last_backup_time is None:
        return False, "ℹ️  Нет информации о предыдущих бэкапах. Рекомендуется сначала сделать полный бэкап."

    # Получаем время модификации файла БД
    db_mtime = os.path.getmtime(db_path)

    # Сравниваем с временем последнего бэкапа
    if db_mtime <= last_backup_time:
        return False, "ℹ️  База данных не изменялась с момента последнего бэкапа."

    # Создаём инкрементальный бэкап
    timestamp = get_timestamp()
    filename = f"incremental_{timestamp}.db"
    backup_path = os.path.join(backup_dir, filename)

    try:
        shutil.copy2(db_path, backup_path)
        msg = f"✅ Инкрементальный бэкап создан: {backup_path}"

        # Логируем
        log_backup('incremental', filename, backup_path)

        return True, msg
    except Exception as e:
        return False, f"❌ Ошибка при создании инкрементального бэкапа: {e}"


def differential_backup(db_path=DEFAULT_DB_PATH, last_full_backup_time=None, backup_dir="backups/differential"):
    """
    Создаёт дифференциальную резервную копию.

    Args:
        db_path (str): Путь к файлу базы данных
        last_full_backup_time (float): Время последнего полного бэкапа (Unix timestamp)
        backup_dir (str): Директория для сохранения бэкапа

    Returns:
        tuple: (success, msg) где success - bool, msg - строка с результатом
    """
    ensure_backup_dirs()

    # Проверяем существование файла БД
    if not os.path.exists(db_path):
        return False, f"❌ Файл базы данных не найден: {db_path}"

    # Если время не указано, получаем время последнего полного бэкапа из лога
    if last_full_backup_time is None:
        last_full_backup_time = get_last_full_backup_time()

    # Проверяем наличие полного бэкапа
    if last_full_backup_time is None:
        return False, "ℹ️  Нет информации о полных бэкапах. Сначала сделайте полный бэкап."

    # Получаем время модификации файла БД
    db_mtime = os.path.getmtime(db_path)

    # Сравниваем с временем последнего полного бэкапа
    if db_mtime <= last_full_backup_time:
        return False, "ℹ️  База данных не изменялась с момента последнего полного бэкапа."

    # Создаём дифференциальный бэкап
    timestamp = get_timestamp()
    filename = f"differential_{timestamp}.db"
    backup_path = os.path.join(backup_dir, filename)

    try:
        shutil.copy2(db_path, backup_path)
        msg = f"✅ Дифференциальный бэкап создан: {backup_path}"

        # Логируем
        log_backup('differential', filename, backup_path)

        return True, msg
    except Exception as e:
        return False, f"❌ Ошибка при создании дифференциального бэкапа: {e}"


def restore_backup(backup_file_path, db_path=DEFAULT_DB_PATH):
    """
    Восстанавливает базу данных из резервной копии.

    Args:
        backup_file_path (str): Путь к файлу резервной копии
        db_path (str): Путь к файлу базы данных для восстановления

    Returns:
        tuple: (success, msg) где success - bool, msg - строка с результатом
    """
    # Проверяем существование файла бэкапа
    if not os.path.exists(backup_file_path):
        return False, f"❌ Файл резервной копии не найден: {backup_file_path}"

    try:
        # Если файл БД существует, создаём резервную копию текущей БД
        if os.path.exists(db_path):
            bak_timestamp = get_timestamp()
            bak_path = f"{db_path}.bak_{bak_timestamp}"
            shutil.move(db_path, bak_path)
            backup_msg = f"ℹ️  Текущая БД перемещена в: {bak_path}"
        else:
            backup_msg = ""

        # Восстанавливаем из бэкапа
        shutil.copy2(backup_file_path, db_path)
        restore_msg = f"✅ База данных восстановлена из: {backup_file_path}"

        # Объединяем сообщения
        full_msg = f"{backup_msg} {restore_msg}".strip()

        return True, full_msg
    except Exception as e:
        return False, f"❌ Ошибка при восстановлении: {e}"