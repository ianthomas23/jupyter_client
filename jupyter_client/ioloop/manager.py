"""A kernel manager with a tornado IOLoop"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import typing as t

from tornado import ioloop
from traitlets import Instance, Type

from ..manager import AsyncKernelManager, KernelManager
from .restarter import AsyncIOLoopKernelRestarter, IOLoopKernelRestarter
from ..stream import as_zmqstream


class IOLoopKernelManager(KernelManager):
    """An io loop kernel manager."""

    loop = Instance("tornado.ioloop.IOLoop")

    def _loop_default(self) -> ioloop.IOLoop:
        return ioloop.IOLoop.current()

    restarter_class = Type(
        default_value=IOLoopKernelRestarter,
        klass=IOLoopKernelRestarter,
        help=(
            "Type of KernelRestarter to use. "
            "Must be a subclass of IOLoopKernelRestarter.\n"
            "Override this to customize how kernel restarts are managed."
        ),
        config=True,
    )
    _restarter: t.Any = Instance("jupyter_client.ioloop.IOLoopKernelRestarter", allow_none=True)

    def start_restarter(self) -> None:
        """Start the restarter."""
        if self.autorestart and self.has_kernel:
            if self._restarter is None:
                self._restarter = self.restarter_class(
                    kernel_manager=self, loop=self.loop, parent=self, log=self.log
                )
            self._restarter.start()

    def stop_restarter(self) -> None:
        """Stop the restarter."""
        if self.autorestart and self._restarter is not None:
            self._restarter.stop()

    connect_shell = as_zmqstream(KernelManager.connect_shell)
    connect_control = as_zmqstream(KernelManager.connect_control)
    connect_iopub = as_zmqstream(KernelManager.connect_iopub)
    connect_stdin = as_zmqstream(KernelManager.connect_stdin)
    connect_hb = as_zmqstream(KernelManager.connect_hb)


class AsyncIOLoopKernelManager(AsyncKernelManager):
    """An async ioloop kernel manager."""

    loop = Instance("tornado.ioloop.IOLoop")

    def _loop_default(self) -> ioloop.IOLoop:
        return ioloop.IOLoop.current()

    restarter_class = Type(
        default_value=AsyncIOLoopKernelRestarter,
        klass=AsyncIOLoopKernelRestarter,
        help=(
            "Type of KernelRestarter to use. "
            "Must be a subclass of AsyncIOLoopKernelManager.\n"
            "Override this to customize how kernel restarts are managed."
        ),
        config=True,
    )
    _restarter: t.Any = Instance(
        "jupyter_client.ioloop.AsyncIOLoopKernelRestarter", allow_none=True
    )

    def start_restarter(self) -> None:
        """Start the restarter."""
        if self.autorestart and self.has_kernel:
            if self._restarter is None:
                self._restarter = self.restarter_class(
                    kernel_manager=self, loop=self.loop, parent=self, log=self.log
                )
            self._restarter.start()

    def stop_restarter(self) -> None:
        """Stop the restarter."""
        if self.autorestart and self._restarter is not None:
            self._restarter.stop()

    connect_shell = as_zmqstream(AsyncKernelManager.connect_shell)
    connect_control = as_zmqstream(AsyncKernelManager.connect_control)
    connect_iopub = as_zmqstream(AsyncKernelManager.connect_iopub)
    connect_stdin = as_zmqstream(AsyncKernelManager.connect_stdin)
    connect_hb = as_zmqstream(AsyncKernelManager.connect_hb)
