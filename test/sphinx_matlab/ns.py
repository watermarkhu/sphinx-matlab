from pathlib import Path
from colorama import Fore
from colorama import init as colorama_init
from matlab_ns import NamespaceNodeType, Workspace


colorama_init(autoreset=True)

# create an empty namespace
# and initialize it with two directories
workspace = Workspace()
current_path = Path(__file__).parent.resolve()
workspace.init_namespace(
    [current_path / d for d in ["src"]]
)


# dump the content of the namespace
for _symbol_name, symbol in workspace._namespace.items():
    if symbol.node_type == NamespaceNodeType.PACKAGE:
        print(f"{Fore.YELLOW}{symbol.fully_qualified_name}")
    elif symbol.node_type == NamespaceNodeType.CLASS:
        print(f"{Fore.GREEN}{symbol.fully_qualified_name}")
    elif symbol.node_type == NamespaceNodeType.FUNCTION:
        print(f"{Fore.BLUE}{symbol.fully_qualified_name}")
    elif symbol.node_type == NamespaceNodeType.SCRIPT:
        print(f"{Fore.MAGENTA}{symbol.fully_qualified_name}")
