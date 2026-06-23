import os
import logging
from datetime import datetime
import pytz

from database import get_group_settings, increment_stat

logger = logging.getLogger(__name__)
TZ = pytz.timezone(os.environ.get('TIMEZONE', 'Asia/Bangkok'))
STORAGE_PATH = os.environ.get('STORAGE_PATH', './storage')


def _today() -> str:
    return datetime.now(TZ).strftime('%Y-%m-%d')


def _get_storage_dir(group_id: str, media_type: str) -> str:
    date = _today()
    path = os.path.join(STORAGE_PATH, group_id, date, media_type)
    os.makedirs(path, exist_ok=True)
    return path


def _timestamp() -> str:
    return datetime.now(TZ).strftime('%H%M%S')


def _get_chat_log_path(group_id: str) -> str:
    group_dir = os.path.join(STORAGE_PATH, group_id)
    os.makedirs(group_dir, exist_ok=True)
    return os.path.join(group_dir, 'chat_history.txt')


def append_chat_log(group_id: str, sender_name: str, message_type: str, content: str):
    path = _get_chat_log_path(group_id)
    now = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{now}] {sender_name}: [{message_type}] {content}\n'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line)


def save_image(line_bot_api, event) -> tuple[str, str]:
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'direct'
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return '', ''

    message_id = event.message.id
    ts = _timestamp()
    filename = f'{ts}_{message_id}.jpg'
    save_dir = _get_storage_dir(group_id, 'images')
    filepath = os.path.join(save_dir, filename)

    try:
        content = line_bot_api.get_message_content(message_id)
        with open(filepath, 'wb') as f:
            for chunk in content.iter_content():
                f.write(chunk)
        increment_stat(group_id, _today(), 'images_count')
        logger.info(f'Image saved: {filepath}')
        return filepath, filename
    except Exception as e:
        logger.error(f'Failed to save image: {e}')
        return '', ''


def save_video(line_bot_api, event) -> tuple[str, str]:
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'direct'
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return '', ''

    message_id = event.message.id
    ts = _timestamp()
    filename = f'{ts}_{message_id}.mp4'
    save_dir = _get_storage_dir(group_id, 'videos')
    filepath = os.path.join(save_dir, filename)

    try:
        content = line_bot_api.get_message_content(message_id)
        with open(filepath, 'wb') as f:
            for chunk in content.iter_content():
                f.write(chunk)
        increment_stat(group_id, _today(), 'videos_count')
        logger.info(f'Video saved: {filepath}')
        return filepath, filename
    except Exception as e:
        logger.error(f'Failed to save video: {e}')
        return '', ''


def save_file(line_bot_api, event) -> tuple[str, str]:
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'direct'
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return '', ''

    message_id = event.message.id
    original_name = getattr(event.message, 'file_name', f'{message_id}.bin')
    ts = _timestamp()
    filename = f'{ts}_{original_name}'
    save_dir = _get_storage_dir(group_id, 'files')
    filepath = os.path.join(save_dir, filename)

    try:
        content = line_bot_api.get_message_content(message_id)
        with open(filepath, 'wb') as f:
            for chunk in content.iter_content():
                f.write(chunk)
        increment_stat(group_id, _today(), 'files_count')
        logger.info(f'File saved: {filepath}')
        return filepath, filename
    except Exception as e:
        logger.error(f'Failed to save file: {e}')
        return '', ''


def save_audio(line_bot_api, event) -> tuple[str, str]:
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'direct'
    settings = get_group_settings(group_id)
    if not settings.get('archiving_enabled', 1):
        return '', ''

    message_id = event.message.id
    ts = _timestamp()
    filename = f'{ts}_{message_id}.m4a'
    save_dir = _get_storage_dir(group_id, 'audio')
    filepath = os.path.join(save_dir, filename)

    try:
        content = line_bot_api.get_message_content(message_id)
        with open(filepath, 'wb') as f:
            for chunk in content.iter_content():
                f.write(chunk)
        increment_stat(group_id, _today(), 'files_count')
        logger.info(f'Audio saved: {filepath}')
        return filepath, filename
    except Exception as e:
        logger.error(f'Failed to save audio: {e}')
        return '', ''


def get_group_storage_summary(group_id: str) -> dict:
    group_dir = os.path.join(STORAGE_PATH, group_id)
    if not os.path.isdir(group_dir):
        return {'dates': [], 'total_images': 0, 'total_videos': 0, 'total_files': 0}

    summary = {'dates': [], 'total_images': 0, 'total_videos': 0, 'total_files': 0}
    for date_dir in sorted(os.listdir(group_dir), reverse=True):
        date_path = os.path.join(group_dir, date_dir)
        if not os.path.isdir(date_path):
            continue
        images = len(os.listdir(os.path.join(date_path, 'images'))) if os.path.isdir(os.path.join(date_path, 'images')) else 0
        videos = len(os.listdir(os.path.join(date_path, 'videos'))) if os.path.isdir(os.path.join(date_path, 'videos')) else 0
        files = len(os.listdir(os.path.join(date_path, 'files'))) if os.path.isdir(os.path.join(date_path, 'files')) else 0
        summary['dates'].append({'date': date_dir, 'images': images, 'videos': videos, 'files': files})
        summary['total_images'] += images
        summary['total_videos'] += videos
        summary['total_files'] += files

    return summary
