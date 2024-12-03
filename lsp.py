import asyncio
import json
import re
import sys
from json.decoder import JSONDecodeError
from typing import Any
from uuid import uuid4

from termcolor import cprint

lsp_process: Any = None

# LSP_SERVER = ["rust-analyzer"]
# PROJECT_PATH = "/home/falko17/Dokumente/git/dcaf-rs"
# FILE = "src/common/constants.rs"
LSP_SERVER = ["pyright-langserver", "--stdio"]
PROJECT_PATH = "/home/falko17/Dokumente/git/dayfinder"
FILE = "bot.py"


async def ainput(string: str) -> str:
    def print_prompt():
        sys.stdout.write(string)
        sys.stdout.flush()

    await asyncio.get_event_loop().run_in_executor(None, print_prompt)
    return await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)


async def run_lsp_server():
    return await asyncio.create_subprocess_exec(
        *LSP_SERVER,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def send_request(method, params, notification=False):
    # Send the request to the LSP server and return the response
    request = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": method,
        "params": params,
    }
    if notification:
        del request["id"]

    cprint(f"\n{json.dumps(request, indent=2)}\n", "blue")
    json_request = json.dumps(request)
    await send_request_direct(json_request)


async def send_request_direct(json_request):
    content_length = len(json_request)
    lsp_process.stdin.write(f"Content-Length: {content_length}\r\n\r\n".encode())
    lsp_process.stdin.write(f"{json_request}".encode())
    await lsp_process.stdin.drain()


async def read_lsp_output():
    while True:
        line = await lsp_process.stdout.readline()
        line = re.sub(r"Content-Length: \d+$", "", line.decode().strip())
        line = re.sub(r"Content-Type: .*$", "", line)
        if line == "":
            continue
        try:
            json_response = json.loads(line)
            cprint(
                f"\n{json.dumps(json_response, indent=2)}\n",
                "green",
            )
        except JSONDecodeError:
            cprint(
                f"\nIncoming transmission:\n{line}\n",
                "green",
            )


async def read_lsp_errors():
    while True:
        line = await lsp_process.stderr.readline()
        line = line.decode().strip()
        if line == "":
            continue
        cprint(
            f"\n{line}\n",
            "red",
        )


async def initialize_lsp():
    # Initialize the LSP server
    params = {
        "processId": None,
        "rootUri": f"file://{PROJECT_PATH}/",
        "rootPath": PROJECT_PATH,
        "capabilities": {
            "workspace": {
                "workspaceFolders": False,
            },
            "textDocument": {
                "documentSymbol": {
                    "hierarchicalDocumentSymbolSupport": True,
                    "dynamicRegistration": False,
                }
            },
            "window": {"workDoneProgress": False},
            "general": {},
            "experimental": {},
        },
        "workspaceFolders": [{"uri": f"file://{PROJECT_PATH}", "name": "main"}],
    }
    await send_request("initialize", params)
    await send_request("initialized", {}, notification=True)


async def list_document_symbols():
    # List all document symbols in the hardcoded project
    params = {
        "textDocument": {
            "uri": f"file://{PROJECT_PATH}/{FILE}",
        }
    }
    await send_request("textDocument/documentSymbol", params)


async def custom_request():
    # Send a custom request to the LSP server
    input_request = await ainput("Enter the JSON request: ")
    await send_request_direct(input_request)


async def exit_program():
    cprint("Exiting...", "red")
    lsp_process.terminate()
    exit(0)


async def cli():
    choices = {
        "1": ("Initialize LSP", initialize_lsp),
        "2": ("List Document Symbols", list_document_symbols),
        "3": ("Send Custom Request", custom_request),
        "0": ("Exit", exit_program),
    }
    while True:
        cprint("\n=== LSP Debugging CLI ===", attrs=["underline", "bold"])
        for num, (description, _) in choices.items():
            cprint(f"[{num}] {description}", "cyan")
        choice = await ainput("Enter your choice: ")
        choice = choice.strip()

        if choice == "":
            continue
        elif choice in choices:
            _, function = choices[choice]
            await function()
        else:
            cprint("Invalid choice. Please try again.", "red")


async def main():
    global lsp_process
    lsp_process = await run_lsp_server()

    lsp_out_task = asyncio.create_task(read_lsp_output())
    lsp_err_task = asyncio.create_task(read_lsp_errors())
    cli_task = asyncio.create_task(cli())
    try:
        await asyncio.gather(lsp_out_task, lsp_err_task, cli_task)
    except SystemExit:
        pass


if __name__ == "__main__":
    asyncio.run(main())
