import os
import time
import logging
import threading

logger = logging.getLogger(__name__)

MOCHI_ROOT_NAME = 'mochi'

# Serialize folder get-or-create so two concurrent uploads don't create
# duplicate "2026-06-27" folders. Cache resolved folder IDs to cut API calls.
_folder_lock = threading.Lock()
_folder_cache = {}


def _get_service():
    """Build Drive API service from service account JSON."""
    creds_path = os.environ.get('GDRIVE_CREDENTIALS_JSON', '')
    if not creds_path or not os.path.isfile(creds_path):
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f'GDrive service init failed: {e}')
        return None


def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    """Return ID of existing folder or create it under parent (thread-safe, cached)."""
    cache_key = f'{parent_id}/{name}'
    cached = _folder_cache.get(cache_key)
    if cached:
        return cached

    with _folder_lock:
        # Re-check inside the lock — another thread may have just created it.
        cached = _folder_cache.get(cache_key)
        if cached:
            return cached

        safe_name = name.replace("'", "\\'")
        q = (
            f"name = '{safe_name}' "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents "
            f"and trashed = false"
        )
        results = service.files().list(q=q, fields='files(id)', spaces='drive').execute()
        files = results.get('files', [])
        if files:
            folder_id = files[0]['id']
        else:
            meta = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id],
            }
            folder_id = service.files().create(body=meta, fields='id').execute()['id']

        _folder_cache[cache_key] = folder_id
        return folder_id


def _mochi_root_id(service) -> str:
    parent = os.environ.get('GDRIVE_MOCHI_FOLDER_ID', 'root')
    return _get_or_create_folder(service, MOCHI_ROOT_NAME, parent)


def _group_folder_name(group_id: str, group_name: str) -> str:
    name = f'{group_name} ({group_id})' if group_name else group_id
    return name.replace('/', '-').replace('\\', '-')[:100]


def get_group_folder_id(service, group_id: str, group_name: str) -> str:
    mochi_id = _mochi_root_id(service)
    return _get_or_create_folder(service, _group_folder_name(group_id, group_name), mochi_id)


def upload_file_to_folder(service, local_path: str, folder_id: str,
                          filename: str = None, retries: int = 3) -> str | None:
    """Upload or replace a file in a specific Drive folder. Returns file ID.

    Retries with exponential backoff on transient API/network errors.
    """
    from googleapiclient.http import MediaFileUpload
    import mimetypes

    fname = filename or os.path.basename(local_path)
    safe_fname = fname.replace("'", "\\'")
    mime = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'

    last_err = None
    for attempt in range(retries):
        try:
            q = f"name = '{safe_fname}' and '{folder_id}' in parents and trashed = false"
            existing = service.files().list(q=q, fields='files(id)').execute().get('files', [])
            media = MediaFileUpload(local_path, mimetype=mime, resumable=True)

            if existing:
                result = service.files().update(
                    fileId=existing[0]['id'], media_body=media, fields='id'
                ).execute()
            else:
                result = service.files().create(
                    body={'name': fname, 'parents': [folder_id]},
                    media_body=media, fields='id'
                ).execute()
            return result.get('id')
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
    logger.error(f'GDrive upload_file_to_folder failed after {retries} tries: {last_err}')
    return None


def download_file(service, file_id: str, dest_path: str) -> bool:
    """Download a Drive file to a local path."""
    try:
        from googleapiclient.http import MediaIoBaseDownload
        req = service.files().get_media(fileId=file_id)
        with open(dest_path, 'wb') as f:
            dl = MediaIoBaseDownload(f, req)
            done = False
            while not done:
                _, done = dl.next_chunk()
        return True
    except Exception as e:
        logger.error(f'GDrive download failed: {e}')
        return False


def upload_media_async(local_path: str, group_id: str, group_name: str,
                       date_str: str, media_type: str):
    """Fire-and-forget: upload media file to mochi/GROUP/DATE/TYPE/."""
    def _worker():
        service = _get_service()
        if not service:
            return
        try:
            group_folder_id = get_group_folder_id(service, group_id, group_name)
            date_folder_id = _get_or_create_folder(service, date_str, group_folder_id)
            type_folder_id = _get_or_create_folder(service, media_type, date_folder_id)
            file_id = upload_file_to_folder(service, local_path, type_folder_id)
            if file_id:
                logger.info(f'GDrive upload OK: {os.path.basename(local_path)} -> {file_id}')
        except Exception as e:
            logger.error(f'GDrive media upload worker failed: {e}')

    threading.Thread(target=_worker, daemon=True).start()
