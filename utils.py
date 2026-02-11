import os
import shutil
from datetime import datetime

def backup_database(db_path='database.db', backup_folder='backups'):
    """
    Создаёт резервную копию файла базы данных.
    """
    if not os.path.exists(db_path):
        return False, "Файл базы данных не найден."

    os.makedirs(backup_folder, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    backup_path = os.path.join(backup_folder, backup_name)

    try:
        shutil.copy2(db_path, backup_path)
        return True, f"Резервная копия создана: {backup_name}"
    except Exception as e:
        return False, f"Ошибка при создании резервной копии: {e}"


def cleanup_temp_files(folder='temp'):
    """
    Удаляет все временные файлы из папки.
    """
    if not os.path.exists(folder):
        return 0

    count = 0
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                count += 1
        except Exception:
            pass
    return count