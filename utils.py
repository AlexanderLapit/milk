import os
import shutil
from datetime import datetime

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