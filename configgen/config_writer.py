import os.path
from .constants import INDENT, BREAK
from typing import List, Union


class ConfigWriter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.config_lines = []
        self.current_indent = 0

    def indent(self):
        self.current_indent += 1

    def add_config(self, configs: Union[str, List[str]]):
        if isinstance(configs, str):
            self.config_lines.append(str(INDENT * self.current_indent) + configs)
        else:
            for config_str in list(configs):
                if config_str:
                    self.config_lines.append(str(INDENT * self.current_indent) + config_str)

    def unindent(self):
        if self.current_indent > 0:
            self.current_indent -= 1
            self.config_lines.append(str(INDENT * self.current_indent) + BREAK)

    def line_return(self):
        for _ in range(self.current_indent):
            self.unindent()

    def new_line(self):
        self.line_return()
        self.config_lines.append("")

    def reset(self):
        self.current_indent = 0
        self.config_lines.clear()

    def write(self, path=None, append=False):
        if not path:
            if not append:
                with open(self.name + ".conf", "w") as config_file:
                    config_file.writelines('\n'.join(self.config_lines))
            else:
                with open(self.name + ".conf", "a") as config_file:
                    config_file.writelines('\n'.join(self.config_lines))
        else:
            if not append:
                with open(os.path.join(path, self.name + ".conf"), "w") as config_file:
                    config_file.writelines('\n'.join(self.config_lines))
            else:
                with open(os.path.join(path, self.name + ".conf"), "a") as config_file:
                    config_file.writelines('\n'.join(self.config_lines))

    def __str__(self) -> str:
        return "\n".join(self.config_lines)
