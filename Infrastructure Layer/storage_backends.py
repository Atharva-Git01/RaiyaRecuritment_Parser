from __future__ import annotations

import shutil
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import Settings, get_settings


@dataclass
class StoredObject:
    backend: str
    object_key: str
    size_bytes: int
    content_type: str
    local_path: Optional[Path] = None


class StorageBackend(ABC):
    @abstractmethod
    def store_bytes(self, object_key: str, data: bytes, content_type: str, quarantine: bool = False) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def store_file(self, object_key: str, source_path: Path, content_type: str, quarantine: bool = False) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, object_key: str, quarantine: bool = False) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def exists(self, object_key: str, quarantine: bool = False) -> bool:
        raise NotImplementedError

    @abstractmethod
    def materialize(self, object_key: str, suffix: str = '', quarantine: bool = False) -> Path:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: Path):
        self.root = root
        self.quarantine_root = root / 'quarantine'
        self.root.mkdir(parents=True, exist_ok=True)
        self.quarantine_root.mkdir(parents=True, exist_ok=True)

    def _base(self, quarantine: bool) -> Path:
        return self.quarantine_root if quarantine else self.root

    def _resolve_path(self, object_key: str, quarantine: bool) -> Path:
        base = self._base(quarantine)
        candidate = (base / Path(object_key)).resolve()
        root_resolved = base.resolve()
        if not str(candidate).startswith(str(root_resolved)):
            raise ValueError('Unsafe object key.')
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def store_bytes(self, object_key: str, data: bytes, content_type: str, quarantine: bool = False) -> StoredObject:
        target = self._resolve_path(object_key, quarantine)
        target.write_bytes(data)
        return StoredObject('local', object_key, len(data), content_type, target)

    def store_file(self, object_key: str, source_path: Path, content_type: str, quarantine: bool = False) -> StoredObject:
        target = self._resolve_path(object_key, quarantine)
        shutil.copyfile(source_path, target)
        return StoredObject('local', object_key, target.stat().st_size, content_type, target)

    def read_bytes(self, object_key: str, quarantine: bool = False) -> bytes:
        return self._resolve_path(object_key, quarantine).read_bytes()

    def exists(self, object_key: str, quarantine: bool = False) -> bool:
        return self._resolve_path(object_key, quarantine).exists()

    def materialize(self, object_key: str, suffix: str = '', quarantine: bool = False) -> Path:
        source = self._resolve_path(object_key, quarantine)
        temp_root = get_settings().temp_materialized_root
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix='raiya-object-', dir=str(temp_root))
        target = Path(temp_dir) / f'materialized{suffix}'
        shutil.copyfile(source, target)
        return target


class AzureBlobStorageBackend(StorageBackend):
    def __init__(self, settings: Settings):
        from azure.storage.blob import BlobServiceClient, ContentSettings
        if not settings.azure_blob_connection_string:
            raise RuntimeError('AZURE_BLOB_CONNECTION_STRING is not configured.')
        self._content_settings = ContentSettings
        self.service = BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
        self.container = self.service.get_container_client(settings.azure_blob_container)
        self.quarantine_container = self.service.get_container_client(settings.azure_blob_quarantine_container)
        for container in (self.container, self.quarantine_container):
            try:
                container.create_container()
            except Exception:
                pass

    def _container(self, quarantine: bool):
        return self.quarantine_container if quarantine else self.container

    def store_bytes(self, object_key: str, data: bytes, content_type: str, quarantine: bool = False) -> StoredObject:
        blob = self._container(quarantine).get_blob_client(object_key)
        blob.upload_blob(data, overwrite=True, content_settings=self._content_settings(content_type=content_type))
        return StoredObject('azure_blob', object_key, len(data), content_type)

    def store_file(self, object_key: str, source_path: Path, content_type: str, quarantine: bool = False) -> StoredObject:
        return self.store_bytes(object_key, source_path.read_bytes(), content_type, quarantine=quarantine)

    def read_bytes(self, object_key: str, quarantine: bool = False) -> bytes:
        blob = self._container(quarantine).get_blob_client(object_key)
        return blob.download_blob().readall()

    def exists(self, object_key: str, quarantine: bool = False) -> bool:
        blob = self._container(quarantine).get_blob_client(object_key)
        return blob.exists()

    def materialize(self, object_key: str, suffix: str = '', quarantine: bool = False) -> Path:
        temp_root = get_settings().temp_materialized_root
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix='raiya-object-', dir=str(temp_root))
        target = Path(temp_dir) / f'materialized{suffix}'
        target.write_bytes(self.read_bytes(object_key, quarantine=quarantine))
        return target


def get_storage_backend(settings: Settings | None = None) -> StorageBackend:
    active = settings or get_settings()
    if active.storage_backend.lower() == 'azure_blob':
        return AzureBlobStorageBackend(active)
    return LocalStorageBackend(active.local_object_root)
