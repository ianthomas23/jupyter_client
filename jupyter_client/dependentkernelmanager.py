import typing as t
import uuid

from jupyter_core.utils import run_sync
from traitlets import (
    DottedObjectName,
    Instance,
    Type,
    default,
)
from tornado import ioloop
import zmq

from .asynchronous import AsyncKernelClient
from .iant_debug import iant_debug
from .manager import KernelManager, in_pending_state
from .provisioning import DependentProvisioner
from .ioloop.restarter import AsyncIOLoopKernelRestarter
from .stream import as_zmqstream


class DependentKernelManager(KernelManager):
    """Subclassing KernelManager here, but production solution needs both deriving
    from a common base class.

    DependentKernelManager is the equivalent of KernelManager.
    What we actually use is
      ServerKernelManager -> AsyncIOLoopKernelManager -> AsyncKernelManager -> KernelManager
    """
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        iant_debug("DependentKernelManager.__init__")
        # Would like to pass in the parent kernel manager here????
        super().__init__(**kwargs)

    async def _async_pre_start_kernel(
        self, **kw: t.Any
    ) -> t.Tuple[t.List[str], t.Dict[str, t.Any]]:
        self.shutting_down = False
        self.kernel_id = self.kernel_id or kw.pop("kernel_id", str(uuid.uuid4()))
        # save kwargs for use in restart
        # assigning Traitlets Dicts to Dict make mypy unhappy but is ok
        self._launch_args = kw.copy()  # type:ignore [assignment]
        if self.provisioner is None:  # will not be None on restarts
            iant_debug("DependentKernelManager._async_pre_start_kernel about to create/get provisioner")
            self.provisioner = DependentProvisioner(
                kernel_id=self.kernel_id,
                kernel_spec=self.kernel_spec,
                parent=self,
                #**provisioner_config,
            )
            #self.provisioner = KPF.instance(parent=self.parent).create_provisioner_instance(
            #    self.kernel_id,
            #    self.kernel_spec,
            #    parent=self,
            #)
            iant_debug(f"  provisioner is {self.provisioner}")
        kw = await self.provisioner.pre_launch(**kw)
        kernel_cmd = kw.pop("cmd")
        return kernel_cmd, kw

    pre_start_kernel = run_sync(_async_pre_start_kernel)

    @in_pending_state
    async def _async_start_kernel(self, **kw: t.Any) -> None:
        self._attempted_start = True
        kernel_cmd, kw = await self._async_pre_start_kernel(**kw)

        # launch the kernel subprocess
        await self._async_launch_kernel(kernel_cmd, **kw)
        await self._async_post_start_kernel(**kw)

    start_kernel = run_sync(_async_start_kernel)


class AsyncDependentKernelManager(DependentKernelManager):
    """Equivalent to AsyncKernelManager"""
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        iant_debug("AsyncDependentKernelManager.__init__")
        super().__init__(**kwargs)

    # the class to create with our `client` method
    client_class: DottedObjectName = DottedObjectName(
        "jupyter_client.asynchronous.AsyncKernelClient"
    )
    client_factory: Type = Type(klass="jupyter_client.asynchronous.AsyncKernelClient")

    # The PyZMQ Context to use for communication with the kernel.
    context: Instance = Instance(zmq.asyncio.Context)

    @default("context")
    def _context_default(self) -> zmq.asyncio.Context:
        self._created_context = True
        return zmq.asyncio.Context()

    def client(  # type:ignore[override]
        self, **kwargs: t.Any
    ) -> AsyncKernelClient:
        """Get a client for the manager."""
        return super().client(**kwargs)  # type:ignore[return-value]

    _launch_kernel = KernelManager._async_launch_kernel  # type:ignore[assignment]
    start_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_start_kernel  # type:ignore[assignment]
    pre_start_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_pre_start_kernel  # type:ignore[assignment]
    post_start_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_post_start_kernel  # type:ignore[assignment]
    request_shutdown: t.Callable[..., t.Awaitable] = DependentKernelManager._async_request_shutdown  # type:ignore[assignment]
    finish_shutdown: t.Callable[..., t.Awaitable] = DependentKernelManager._async_finish_shutdown  # type:ignore[assignment]
    cleanup_resources: t.Callable[..., t.Awaitable] = DependentKernelManager._async_cleanup_resources  # type:ignore[assignment]
    shutdown_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_shutdown_kernel  # type:ignore[assignment]
    restart_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_restart_kernel  # type:ignore[assignment]
    _send_kernel_sigterm = DependentKernelManager._async_send_kernel_sigterm  # type:ignore[assignment]
    _kill_kernel = DependentKernelManager._async_kill_kernel  # type:ignore[assignment]
    interrupt_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_interrupt_kernel  # type:ignore[assignment]
    signal_kernel: t.Callable[..., t.Awaitable] = DependentKernelManager._async_signal_kernel  # type:ignore[assignment]
    is_alive: t.Callable[..., t.Awaitable] = DependentKernelManager._async_is_alive  # type:ignore[assignment]


class AsyncIOLoopDependentKernelManager(AsyncDependentKernelManager):
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

    connect_shell = as_zmqstream(AsyncDependentKernelManager.connect_shell)
    connect_control = as_zmqstream(AsyncDependentKernelManager.connect_control)
    connect_iopub = as_zmqstream(AsyncDependentKernelManager.connect_iopub)
    connect_stdin = as_zmqstream(AsyncDependentKernelManager.connect_stdin)
    connect_hb = as_zmqstream(AsyncDependentKernelManager.connect_hb)
