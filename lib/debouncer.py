"""
ARVANA Message Debouncer / Buffering Engine
Buffers rapid-fire WhatsApp messages from the same user within a 10-second window
so the AI generates a single, cohesive reply to the entire thought instead of
firing multiple fragmented responses.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger("arvana.debouncer")


class MessageDebouncer:
    """
    Buffers rapid incoming messages from a user.
    When a user sends multiple texts within the debounce window (default 10s),
    this engine merges them into a single coherent prompt before invoking the AI handler.
    """

    def __init__(self, default_delay: float = 10.0):
        self.default_delay = default_delay
        self._buffers: Dict[str, List[str]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, Callable] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def has_pending(self, key: str) -> bool:
        """Returns True if there is a pending debounced message timer for the given key."""
        return key in self._tasks and not self._tasks[key].done()

    def get_buffered_messages(self, key: str) -> List[str]:
        """Returns the list of buffered messages for the given key."""
        return list(self._buffers.get(key, []))

    async def add_message(
        self,
        key: str,
        message_text: str,
        handler: Callable[[str, str, Dict[str, Any]], Any],
        metadata: Optional[Dict[str, Any]] = None,
        delay: Optional[float] = None
    ) -> None:
        """
        Adds an incoming message to the user's buffer and resets/starts the debounce timer.
        """
        delay = delay if delay is not None else self.default_delay

        if key not in self._buffers:
            self._buffers[key] = []
        self._buffers[key].append(message_text.strip())

        self._handlers[key] = handler
        if metadata:
            self._metadata[key] = metadata

        # Cancel any existing countdown timer for this user
        if key in self._tasks and not self._tasks[key].done():
            self._tasks[key].cancel()

        # Start a new countdown timer
        loop = asyncio.get_running_loop()
        self._tasks[key] = loop.create_task(self._wait_and_flush(key, delay))
        logger.info(
            f"Debouncing message for {key}. Buffer size: {len(self._buffers[key])}, "
            f"waiting {delay}s for silence before triggering AI."
        )

    async def _wait_and_flush(self, key: str, delay: float) -> None:
        """Waits for the debounce duration; if no new message arrives, flushes buffer."""
        try:
            await asyncio.sleep(delay)
            await self.flush(key)
        except asyncio.CancelledError:
            # Another message arrived before timer expired, timer was reset
            pass
        except Exception as e:
            logger.error(f"Error during debounce flush for {key}: {e}", exc_info=True)

    async def flush(self, key: str) -> Optional[Any]:
        """
        Immediately flushes all buffered messages for the user and triggers the handler.
        Combines multiple messages with newlines so the AI processes the full thought.
        """
        # Cancel running task if any
        if key in self._tasks and not self._tasks[key].done():
            self._tasks[key].cancel()
        self._tasks.pop(key, None)

        messages = self._buffers.pop(key, [])
        handler = self._handlers.pop(key, None)
        meta = self._metadata.pop(key, {})

        if not messages or not handler:
            return None

        # Combine fragmented thoughts into one cohesive message
        combined_text = "\n".join(m for m in messages if m)
        logger.info(f"Flushing debounce buffer for {key} ({len(messages)} messages combined).")

        # Invoke handler
        res = handler(key, combined_text, meta)
        if asyncio.iscoroutine(res):
            return await res
        return res

    def cancel(self, key: str) -> None:
        """Cancels any pending debounce timer and clears the buffer without triggering."""
        if key in self._tasks and not self._tasks[key].done():
            self._tasks[key].cancel()
        self._tasks.pop(key, None)
        self._buffers.pop(key, None)
        self._handlers.pop(key, None)
        self._metadata.pop(key, None)
        logger.info(f"Cancelled debounce buffer for {key}.")

    def clear_all(self) -> None:
        """Cleans up all pending tasks and buffers (useful for tests)."""
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        self._tasks.clear()
        self._buffers.clear()
        self._handlers.clear()
        self._metadata.clear()


# Global singleton instance (10-second default window)
debouncer = MessageDebouncer(default_delay=10.0)
