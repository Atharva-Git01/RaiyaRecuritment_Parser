from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app import repositories
from app.config import Settings, get_settings


class QueueBackend(ABC):
    @abstractmethod
    def enqueue(self, job_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def claim_next(self, worker_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def reschedule(self, job_id: int, error: str, delay_seconds: int) -> None:
        raise NotImplementedError


class DatabaseQueueBackend(QueueBackend):
    def enqueue(self, job_id: int) -> None:
        repositories.update_job_state(job_id, status='queued', stage='queued', scan_status='passed')

    def claim_next(self, worker_id: str) -> Optional[Dict[str, Any]]:
        return repositories.claim_next_job(worker_id)

    def reschedule(self, job_id: int, error: str, delay_seconds: int) -> None:
        repositories.reschedule_job(job_id, error, delay_seconds)


class AzureServiceBusQueueBackend(DatabaseQueueBackend):
    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._sender = None
        self._receiver = None
        try:
            from azure.servicebus import ServiceBusClient
        except ImportError:
            ServiceBusClient = None
        if ServiceBusClient and settings.azure_service_bus_connection_string:
            client = ServiceBusClient.from_connection_string(settings.azure_service_bus_connection_string)
            self._sender = client.get_queue_sender(settings.azure_service_bus_queue)
            self._receiver = client.get_queue_receiver(settings.azure_service_bus_queue, max_wait_time=5)

    def enqueue(self, job_id: int) -> None:
        super().enqueue(job_id)
        if not self._sender:
            return
        try:
            from azure.servicebus import ServiceBusMessage
            with self._sender:
                self._sender.send_messages(ServiceBusMessage(str(job_id)))
        except Exception:
            pass

    def claim_next(self, worker_id: str) -> Optional[Dict[str, Any]]:
        if not self._receiver:
            return repositories.claim_next_job(worker_id)
        try:
            with self._receiver:
                messages = self._receiver.receive_messages(max_message_count=1, max_wait_time=5)
                for message in messages:
                    body = ''.join([chunk.decode('utf-8') if isinstance(chunk, (bytes, bytearray)) else str(chunk) for chunk in message.body]) if getattr(message, 'body', None) else str(message)
                    job_row = repositories.claim_specific_job(int(body.strip()), worker_id)
                    if job_row:
                        self._receiver.complete_message(message)
                        return job_row
                    self._receiver.dead_letter_message(message, reason='job-not-claimable')
        except Exception:
            return repositories.claim_next_job(worker_id)
        return None

    def reschedule(self, job_id: int, error: str, delay_seconds: int) -> None:
        repositories.reschedule_job(job_id, error, delay_seconds)
        self.enqueue(job_id)


def get_queue_backend(settings: Settings | None = None) -> QueueBackend:
    active = settings or get_settings()
    if active.queue_backend.lower() == 'azure_service_bus':
        return AzureServiceBusQueueBackend(active)
    return DatabaseQueueBackend()


