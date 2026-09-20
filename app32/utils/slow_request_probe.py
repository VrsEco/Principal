"""Temporary opt-in diagnostics: no request payloads, locals or source lines."""
import json
import math
import os
import sys
import threading
import time
import uuid


class SlowRequestProbe:
    """One bounded timer per request, created after fork, not at app startup.

    Covers WSGI dispatch and response iteration. Does not cancel requests.
    Requires Python threads enabled in the serving process.
    """

    def __init__(self, app, logger, seconds=5, max_pending=16):
        if not math.isfinite(seconds) or seconds < 1:
            raise ValueError("slow request probe threshold must be >= 1 second")
        self.app = app
        self.logger = logger
        self.seconds = seconds
        self.slots = threading.BoundedSemaphore(max_pending)

    def __call__(self, environ, start_response):
        if not self.slots.acquire(blocking=False):
            return self.app(environ, start_response)
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        thread_id = threading.get_ident()
        lock = threading.Lock()
        active = True

        def capture():
            # Serialize cleanup and snapshot so a reused thread is not sampled.
            with lock:
                if not active:
                    return
                frame = sys._current_frames().get(thread_id)
                stack = []
                try:
                    while frame is not None and len(stack) < 64:
                        stack.append((os.path.basename(frame.f_code.co_filename),
                                      frame.f_lineno, frame.f_code.co_name))
                        frame = frame.f_back
                finally:
                    del frame
                record = {
                    "event": "slow_request_stack", "request_id": request_id,
                    "pid": os.getpid(), "thread_id": thread_id,
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                    "stack_leaf_first": stack,
                }
            # Never inspect environ: even URL paths can contain credentials.
            try:
                self.logger.warning("%s", json.dumps(record))
            except Exception:
                pass  # Diagnostics must not affect the response.

        timer = threading.Timer(self.seconds, capture)
        timer.daemon = True

        def finish():
            nonlocal active
            with lock:
                if not active:
                    return
                active = False
            timer.cancel()
            self.slots.release()

        try:
            timer.start()
        except Exception:
            finish()
            return self.app(environ, start_response)
        try:
            iterable = self.app(environ, start_response)
        except BaseException:
            finish()
            raise

        try:
            return _ObservedResponse(iterable, finish)
        except BaseException:
            finish()
            raise


class _ObservedResponse:
    def __init__(self, iterable, finish):
        self.iterable = iterable
        self.iterator = iter(iterable)
        self.finish = finish

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.iterator)
        except BaseException:
            self.finish()
            raise

    def close(self):
        try:
            close = getattr(self.iterable, "close", None)
            if close is not None:
                close()
        finally:
            self.finish()


def install_slow_request_probe(app):
    if app.config.get("SLOW_REQUEST_STACK_ENABLED", False):
        app.wsgi_app = SlowRequestProbe(
            app.wsgi_app, app.logger,
            seconds=app.config.get("SLOW_REQUEST_STACK_SECONDS", 5),
        )
        app.logger.warning(
            "slow_request_probe_enabled threshold_seconds=%s max_pending=16",
            app.wsgi_app.seconds,
        )
