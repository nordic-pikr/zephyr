# SPDX-License-Identifier: Apache-2.0

"""Runner for flashing STM32 devices over ST-LINK with st-flash (stlink-org)."""

import argparse
import shlex

from runners.core import RunnerCaps, RunnerConfig, ZephyrBinaryRunner


class StFlashBinaryRunner(ZephyrBinaryRunner):
    """Runner front-end for st-flash from the open source stlink tools."""

    def __init__(
        self,
        cfg: RunnerConfig,
        stflash: str,
        erase: bool,
        reset: bool,
        dev_id: str | None,
        connect_under_reset: bool,
        hot_plug: bool,
        freq: int | None,
        tool_opt: list[str],
        dry_run: bool = False,
    ):
        super().__init__(cfg)

        self.dry_run = dry_run

        self.stflash = stflash
        self.erase = erase
        self.reset = reset
        self.dev_id = dev_id
        self.connect_under_reset = connect_under_reset
        self.hot_plug = hot_plug
        self.freq = freq
        self.tool_opt = []
        for opts in [shlex.split(opt) for opt in tool_opt]:
            self.tool_opt += opts

    @classmethod
    def name(cls):
        return "stflash"

    @classmethod
    def capabilities(cls) -> RunnerCaps:
        return RunnerCaps(
            commands={"flash"},
            flash_addr=True,
            erase=True,
            reset=True,
            dev_id=True,
            tool_opt=True,
            dry_run=True,
        )

    @classmethod
    def dev_id_help(cls) -> str:
        return "ST-LINK serial number passed to st-flash --serial"

    @classmethod
    def do_add_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument("--stflash", default="st-flash", help="path to the st-flash binary")
        parser.add_argument(
            "--connect-under-reset",
            default=False,
            action=argparse.BooleanOptionalAction,
            help="connect to the target while holding it in reset",
        )
        parser.add_argument(
            "--hot-plug",
            default=False,
            action=argparse.BooleanOptionalAction,
            help="connect to the target without resetting it",
        )
        parser.add_argument("--freq", type=int, help="SWD frequency in kHz")
        parser.set_defaults(reset=True)

    @classmethod
    def do_create(cls, cfg: RunnerConfig, args: argparse.Namespace):
        return StFlashBinaryRunner(
            cfg,
            stflash=args.stflash,
            erase=args.erase,
            reset=args.reset,
            dev_id=args.dev_id,
            connect_under_reset=args.connect_under_reset,
            hot_plug=args.hot_plug,
            freq=args.freq,
            tool_opt=args.tool_opt,
            dry_run=args.dry_run,
        )

    def do_run(self, command: str, **kwargs):
        self.require(self.stflash)

        if command == "flash":
            self.flash()
        else:
            raise ValueError(f"BUG: unhandled command {command}")

    def _common_args(self) -> list[str]:
        args = []

        if self.dev_id:
            args.extend(["--serial", self.dev_id])
        if self.connect_under_reset:
            args.append("--connect-under-reset")
        if self.hot_plug:
            args.append("--hot-plug")
        if self.freq:
            args.append(f"--freq={self.freq}")

        return args + self.tool_opt

    def flash(self):
        self.ensure_output("bin")

        if self.erase:
            self.check_call([self.stflash] + self._common_args() + ["erase"])

        cmd = [self.stflash] + self._common_args()
        if self.reset:
            cmd.append("--reset")

        flash_addr = self.flash_address_from_build_conf(self.build_conf)
        cmd.extend(["write", self.cfg.bin_file or "", f"0x{flash_addr:x}"])

        self.logger.info(f"Flashing file: {self.cfg.bin_file} at 0x{flash_addr:x}")
        self.check_call(cmd)
