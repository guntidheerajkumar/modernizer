from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def banner():
    console.print(Panel.fit("[bold cyan]Legacy .NET Modernization Agent[/]\n"
                            "Knowledge base → migration → verification", border_style="cyan"))


class Steps:
    """Numbered pipeline steps so the user always sees where we are."""
    def __init__(self, names):
        self.names, self.i = names, 0

    def start(self, extra=""):
        self.i += 1
        console.rule(f"[bold]Step {self.i}/{len(self.names)}: {self.names[self.i-1]}[/] {extra}")

    def ok(self, msg): console.print(f"  [green]✔[/] {msg}")
    def warn(self, msg): console.print(f"  [yellow]![/] {msg}")
    def fail(self, msg): console.print(f"  [red]✘[/] {msg}")
    def info(self, msg): console.print(f"  [dim]{msg}[/]")


def table(title, cols, rows):
    t = Table(title=title)
    for c in cols:
        t.add_column(c)
    for r in rows:
        t.add_row(*[str(x) for x in r])
    console.print(t)
