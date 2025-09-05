import asyncio

from openhands.core.config import OpenHandsConfig
from openhands.events.stream import EventStream
from openhands.llm.llm_registry import LLMRegistry
from openhands.runtime import create_runtime_with_factory
from openhands.runtime.base import Runtime
from openhands.storage.files import FileStore
from openhands.utils.async_utils import call_sync_from_async


class ServerConversation:
    sid: str
    file_store: FileStore
    event_stream: EventStream
    runtime: Runtime
    user_id: str | None
    _attach_to_existing: bool = False

    def __init__(
        self,
        sid: str,
        file_store: FileStore,
        config: OpenHandsConfig,
        user_id: str | None,
        event_stream: EventStream | None = None,
        runtime: Runtime | None = None,
    ):
        self.sid = sid
        self.config = config
        self.file_store = file_store
        self.user_id = user_id

        if event_stream is None:
            event_stream = EventStream(sid, file_store, user_id)
        self.event_stream = event_stream

        if runtime:
            self._attach_to_existing = True
            self.runtime = runtime
        else:
            runtime = create_runtime_with_factory(
                config=config,
                event_stream=self.event_stream,
                llm_registry=LLMRegistry(self.config),
                sid=self.sid,
            )
            # Set additional parameters for existing runtime behavior
            if hasattr(runtime, 'attach_to_existing'):
                runtime.attach_to_existing = True  # type: ignore[union-attr]
            if hasattr(runtime, 'headless_mode'):
                runtime.headless_mode = False  # type: ignore[union-attr]
            self.runtime = runtime  # type: ignore[assignment]

    @property
    def security_analyzer(self):
        """Access security analyzer through runtime."""
        return self.runtime.security_analyzer

    async def connect(self) -> None:
        if not self._attach_to_existing:
            await self.runtime.connect()

    async def disconnect(self) -> None:
        if self._attach_to_existing:
            return
        if self.event_stream:
            self.event_stream.close()
        asyncio.create_task(call_sync_from_async(self.runtime.close))
