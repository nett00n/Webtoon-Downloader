import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from threading import Event

from rich import traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from webtoon_downloader.cmd.options import Options
from webtoon_downloader.core.downloader import download_webtoon
from webtoon_downloader.core.utils import TextExporter


class CustomTransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task) -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed", justify="center")
        return Text(
            f"{task.speed:2.0f} {task.fields.get('type')}/s",
            style="progress.data.speed",
            justify="center",
        )


######################## Header Configuration ################################
USER_AGENT = (
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/92.0.4515.107 Safari/537.36"
    )
    if os.name == "nt"
    else ("Mozilla/5.0 (X11; Linux ppc64le; rv:75.0)" "Gecko/20100101 Firefox/75.0")
)

headers = {
    "dnt": "1",
    "user-agent": USER_AGENT,
    "accept-language": "en-US,en;q=0.9",
}
image_headers = {"referer": "https://www.webtoons.com/", **headers}
###########################################################################

######################## Log Configuration ################################
sys.stdout.reconfigure(encoding="utf-8")
console = Console()
traceback.install(console=console, show_locals=False)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
# create logger
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)  # set log level

# create formatter
CLI_FORMAT = "%(message)s"
FILE_FORMAT = "%(asctime)s - %(levelname)-8s - %(message)s - %(filename)s - %(lineno)d - %(name)s"  # rearranged

# create file handler
LOG_FILENAME = "webtoon_downloader.log"
file_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=1000000, backupCount=10, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(FILE_FORMAT))

console_handler = RichHandler(
    level=logging.WARNING,
    console=console,
    rich_tracebacks=True,
    tracebacks_show_locals=False,
    markup=True,
)
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter(CLI_FORMAT))
log.addHandler(file_handler)
log.addHandler(console_handler)
##################################################################

done_event = Event()


progress: Progress = None


def exit_handler(sig, frame):
    """
    stops execution of the program.
    """
    done_event.set()
    if progress:
        progress.console.print("[bold red]Stopping Download[/]...")
        progress.console.print("[red]Download Stopped[/]!")
        progress.console.print("")
    sys.exit(0)


def run():
    global progress
    signal.signal(signal.SIGINT, exit_handler)
    parser = Options()
    parser.initialize()
    try:
        args = parser.parse()
    except Exception as exc:
        console.print(f"[red]Error:[/] {exc}")
        sys.exit(1)

    series_url = args.url
    separate = args.separate
    exporter = TextExporter(args.export_format) if args.export_texts else None

    progress = Progress(
        TextColumn("{task.description}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.2f}%",
        "•",
        SpinnerColumn(style="progress.data.speed"),
        CustomTransferSpeedColumn(),
        "•",
        TextColumn(
            "[green]{task.completed:>02d}[/]/[bold green]{task.fields[rendered_total]}[/]",
            justify="left",
        ),
        SpinnerColumn(),
        "•",
        TimeRemainingColumn(),
        transient=True,
        refresh_per_second=20,
    )
    try:
        download_webtoon(
            progress,
            done_event,
            series_url,
            args.start,
            args.end,
            args.dest,
            args.images_format,
            args.latest,
            separate,
            exporter,
        )
        if exporter:
            exporter.write_data()
    except Exception:
        log.exception("Error while downloading webtoon")
        sys.exit(1)
