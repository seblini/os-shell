#!/usr/bin/env python
from enum import Enum
from dataclasses import dataclass
import os
import re
import sys

class IOType(Enum):
	PIPE_IN = 0
	FILE_IN = 1
	STD_IN = 2
	PIPE_OUT = 3
	FILE_OUT = 4
	STD_OUT = 5

@dataclass
class Program:
    cmd: str
    args: list
    input: IOType = IOType.STD_IN
    output: IOType = IOType.STD_OUT
    out_file: str = ""
    in_file: str = ""
    background_group: int = -1
    error: str = ""

class TokenType(Enum):
	EXIT = "exit"
	PIPE = "|"
	REDIRECT_IN = "<"
	REDIRECT_OUT = ">"
	BACKGROUND = "&"

def tokenize(cmd):
    return re.split(r"\s+", cmd)

def populate_background_group(programs, background_group):
    for program in programs[::-1]:
        if program.background_group != -1:
            return

        program.background_group = background_group

def parse(tokens):
    programs = [Program(cmd="", args=[])]
    background_group = 0

    for token in tokens:
        try:
            token = TokenType(token)
        except ValueError:
            pass

        if programs[-1].error != "":
            return programs

        # new program
        if programs[-1].cmd == "":
            match(token):
                case TokenType.EXIT:
                    programs[-1].cmd = str(TokenType.EXIT)
                case TokenType.PIPE | TokenType.REDIRECT_IN | TokenType.REDIRECT_OUT | TokenType.BACKGROUND:
                    programs[-1].error=f"Invalid command: {token}"
                case _:
                    programs[-1].cmd = token
                    programs[-1].args.append(token)

        # add output redirection file
        elif programs[-1].output == IOType.FILE_OUT:
            if programs[-1].out_file == "":
                match(token):
                    case TokenType.PIPE | TokenType.REDIRECT_IN | TokenType.REDIRECT_OUT | TokenType.BACKGROUND:
                        programs[-1].error=f"Syntax error: unexpected token: {token}"
                    case _:
                        programs[-1].out_file = str(token)
            elif token != TokenType.BACKGROUND:
                programs[-1].error=f"Syntax error: unexpected token: {token}"
            else:
                populate_background_group(programs, background_group)
                background_group += 1
                programs.append(Program(cmd="", args=[]))

        # add input redirection file
        elif programs[-1].input == IOType.FILE_IN: 
            if programs[-1].in_file == "":
                match(token):
                    case TokenType.PIPE | TokenType.REDIRECT_IN | TokenType.REDIRECT_OUT | TokenType.BACKGROUND:
                        programs[-1].error=f"Syntax error: unexpected token: {token}"
                    case _:
                        programs[-1].in_file = str(token)

            # catch unexpected tokens after input redirect
            else:
                match(token):
                    case TokenType.PIPE:
                        programs[-1].output = IOType.PIPE_OUT
                        programs.append(Program(cmd="", args=[], input=IOType.PIPE_IN))
                    case TokenType.REDIRECT_OUT:
                        programs[-1].output = IOType.FILE_OUT
                    case TokenType.BACKGROUND:
                        populate_background_group(programs, background_group)
                        background_group += 1
                        programs.append(Program(cmd="", args=[]))
                    case _:
                        programs[-1].error=f"Syntax error: unexpected token: {token}"

            # add args, handle redir and background
        else:
            match(token):
                case TokenType.PIPE:
                    programs[-1].output = IOType.PIPE_OUT
                    programs.append(Program(cmd="", args=[], input=IOType.PIPE_IN))
                case TokenType.REDIRECT_IN:
                    programs[-1].input = IOType.FILE_IN
                case TokenType.REDIRECT_OUT:
                    programs[-1].output = IOType.FILE_OUT
                case TokenType.BACKGROUND:
                    populate_background_group(programs, background_group)
                    background_group += 1
                    programs.append(Program(cmd="", args=[]))
                case _:
                    programs[-1].args.append(token)

    return programs

def main():
    env = os.environ

    while True:
        print(env["PS1"] if "PS1" in env else "$ ", end="")

        user = input()

        tokens = tokenize(user)
        if len(tokens) == 0:
            sys.exit(0)

        programs = parse(tokens)

        if programs[-1].cmd == "":
            programs.pop()

        pipes = [(-1, -1)] * len(programs)

        for i, program in enumerate(programs):
            if program.error != "":
                print(programs[-1].error)
                sys.exit(1)

            if program.cmd == str(TokenType.EXIT):
                sys.exit(0)

            if program.cmd == "cd":
                if len(programs[-1].args) != 2:
                    print(f"usage: cd <dir>")
                    sys.exit(1)

                os.chdir(program.args[1])
                continue

            if program.output == IOType.PIPE_OUT:
                pipes[i] = os.pipe()

            rc = os.fork()
            # child
            if rc == 0:
                if program.input == IOType.FILE_IN:
                    os.dup2(os.open(program.in_file, os.O_RDONLY), 0)

                if program.output == IOType.FILE_OUT:
                    os.dup2(os.open(program.out_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC), 1)
                    
                if program.output == IOType.PIPE_OUT:
                    os.dup2(pipes[i][1], 1)

                elif pipes[i][0] != -1:
                    os.close(pipes[i][1])

                if program.input == IOType.PIPE_IN:
                    os.dup2(pipes[i-1][0], 0)

                elif pipes[i-1][1] != -1:
                    os.close(pipes[i-1][0])

                #TODO: handle non-absolute paths and invalid commands
                os.execve(program.cmd, program.args, env)

            # parent
            else:
                if pipes[i][1] != -1:
                    os.close(pipes[i][1])

                if i > 0 and  pipes[i-1][0] != -1:
                    os.close(pipes[i-1][0])

                #TODO: handle background tasks
                if program.output != IOType.PIPE_OUT:
                    os.waitpid(rc, 0)

if __name__ == "__main__":
    main()
