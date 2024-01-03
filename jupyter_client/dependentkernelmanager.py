import typing as t
import uuid

from jupyter_core.utils import run_sync

from .iant_debug import iant_debug
from .manager import KernelManager, in_pending_state
from .provisioning import DependentProvisioner


class DependentKernelManager(KernelManager):
    """Subclassing KernelManager here, but production solution needs both deriving
    from a common base class.
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

    #connect_shell = as_zmqstream(KernelManager.connect_shell)
    #connect_control = as_zmqstream(KernelManager.connect_control)
    #connect_iopub = as_zmqstream(KernelManager.connect_iopub)
    #connect_stdin = as_zmqstream(KernelManager.connect_stdin)
    #connect_hb = as_zmqstream(KernelManager.connect_hb)
