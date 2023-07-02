#!/usr/bin/env python3

import os
import ast
import datetime

from pathlib import Path
from typing import List
from subprocess import run as srun
from dataclasses import dataclass

@dataclass()
class EmojiObject:
    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime
    creator_id: str
    name: str

DEFAULT_USER_OPTS = {
    "url": "http://localhost:8065/api/v4",
    "login-id": "user-1",
    "password": "SampleUs@r-1",
    "insecure": True,
    "output-dir": "emojis",
}

class CallableEmojiOption:
    def __init__(self, cmd, option):
        self.cmd = cmd + option

    def __call__(self, **kwargs) -> List[EmojiObject]:
        for k,v in kwargs.items():
            if v is None:
                v = DEFAULT_USER_OPTS[k]

            if k == "emojis" or k == "output-dir":
                continue

            if k == 'insecure':
                self.cmd += [f'--{k}']
            else:
                self.cmd += [f'--{k}'] + [f'{v}']

        emojis = kwargs.get("emojis")
        if emojis is not None:
            output_dir = kwargs.get("output-dir")
            if output_dir is None:
                output_dir = DEFAULT_USER_OPTS.get("output-dir")

            if output_dir is None:
                raise IOError("`output-dir` not specified.")

            for emoji in emojis:
                name = emoji.get("name")
                proc = srun(self.cmd + [name, str(Path(f"{output_dir}/{name}"))], capture_output=True)

                if proc.returncode != 0:
                    print(f"[Err] failed: {proc.stderr}")
                    return list()

            return list()

        proc = srun(self.cmd, capture_output=True)

        if proc.returncode != 0:
            print(f"[Err] failed: {proc.stderr}")
            return list()

        return ast.literal_eval(proc.stdout.decode())

    def __repr__(self):
        s = f'{type(self).__name__}{self.cmd}'
        return s


class CommandBuilder:
    def __init__(self, base_cmd: List[str], options: List[str]) -> None:
        self.base_cmd = base_cmd

        for opt in options:
            setattr(self, opt, CallableEmojiOption(base_cmd, [opt]))

    def __call__(self, *args) -> List[str]:
        output = list()
        for arg in args:
            proc = srun(self.base_cmd + [arg], capture_output=True)

            if proc.returncode != 0:
                print(f"[Err] proc returned not 0: {proc.stderr}")
            output.append(proc.stdout.decode())

        return output


    def __repr__(self):
            return str(self.__dict__)


def detect_and_rename_images(directory: str):
    base = ["file"]
    options = []
    cmd = CommandBuilder(base, options)

    if directory is None:
        directory = DEFAULT_USER_OPTS["output-dir"]

    files = Path(directory).glob("**/*")
    files = [x for x in files if x.is_file()]

    things_to_be_renamed = list()
    for file in files:
        output_to_parse = cmd(file)[0].strip()
        parsed = output_to_parse.split(' ')[:2]
        parsed[0] = Path(parsed[0][:-1]) # pyright: ignore
        things_to_be_renamed.append(tuple(parsed))

    for path, filetype in things_to_be_renamed:
        match filetype:
            case 'GIF':
                path.replace(path.with_suffix('.gif'))
            case 'PNG':
                path.replace(path.with_suffix('.png'))
            case _:
                print("[Err] unsupported replacement")


def main():
    base = ["poetry", "run", "mmemoji"]
    options = ["create", "delete", "download", "list", "search"]
    cmd = CommandBuilder(base, options)

    options = {
        "url": os.environ.get("MM_URL"),
        "login-id": os.environ.get("MM_LOGIN_ID"),
        "password": os.environ.get("MM_PASSWORD"),
        "insecure": os.environ.get("MM_INSECURE"),
        "output-dir": os.environ.get("MM_OUTPUT_DIR"),
        "output": "json",
    }

    options["emojis"] = cmd.list(**options) # pyright: ignore
    cmd.download(**options) # pyright: ignore

    detect_and_rename_images(options["output-dir"])


if __name__ == '__main__':
    main()
