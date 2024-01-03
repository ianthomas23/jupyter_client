from typing import Any, Dict, List, Optional, Union

from .provisioner_base import KernelProvisionerBase
from ..connect import KernelConnectionInfo
from ..iant_debug import iant_debug


class DependentProvisioner(KernelProvisionerBase):
    def __init__(self, **kwargs):
        iant_debug("DependentKernelProvisioner")
        super().__init__(**kwargs)

        # Also needs all of the ports????????

    @property
    def has_process(self) -> bool:
        """
        Returns true if this provisioner is currently managing a process.

        This property is asserted to be True immediately following a call to
        the provisioner's :meth:`launch_kernel` method.
        """
        return True

    async def poll(self) -> Optional[int]:
        return None

    async def wait(self) -> Optional[int]:
        pass

    async def send_signal(self, signum: int) -> None:
        pass

    async def kill(self, restart: bool = False) -> None:
        pass

    async def terminate(self, restart: bool = False) -> None:
        pass

    async def launch_kernel(self, cmd: List[str], **kwargs: Any) -> KernelConnectionInfo:
        iant_debug("DependentProvisioner.launch_kernel")
        return self.connection_info

    async def cleanup(self, restart: bool = False) -> None:
        pass

    async def pre_launch(self, **kwargs: Any) -> Dict[str, Any]:
        iant_debug(f"DependentProvisioner.pre_launch {kwargs}")

        # This is where deal with ports and write connection file, etc
        km = self.parent

        conn_info = kwargs['env']['IANT_BOTCH_CONNECTION_INFO']
        km.transport = conn_info['transport']
        #km.ip = conn_info['ip']
        km.iopub_port = conn_info['iopub_port']
        km.stdin_port = conn_info['stdin_port']
        km.hb_port = conn_info['hb_port']
        km.control_port = conn_info['control_port']

        km.shell_port = int(kwargs['env']['IANT_BOTCH_SHELL_PORT'])  # Was a string for some reason?

        if "env" in kwargs:
            jupyter_session = kwargs["env"].get("JPY_SESSION_NAME", "")  # Do I remove the port suffix?
            km.write_connection_file(jupyter_session=jupyter_session)
        else:
            km.write_connection_file()
        self.connection_info = km.get_connection_info()
        iant_debug(f"  dependent conn info {self.connection_info}")

        kernel_cmd = []
        return await super().pre_launch(cmd=kernel_cmd, **kwargs)
