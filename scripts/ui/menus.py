from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from typing import Optional, Callable
import sys


console = Console()


def print_header(title: str = "CONTENT-OS") -> None:
    subtitle = "Video Content Pipeline"
    panel = Panel(
        f"[bold cyan]{subtitle}[/bold cyan]",
        title=f"[bold yellow]{title}[/bold yellow]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def print_main_menu() -> None:
    table = Table(show_header=False, box=None, padding=(1, 2))
    table.add_column(style="bold cyan", width=4)
    table.add_column(style="white")

    table.add_row("1", "Nueva Sesion")
    table.add_row("2", "Continuar Sesion")
    table.add_row("3", "Listar Sesiones")
    table.add_row("", "")
    table.add_row("4", "[green]Procesar Audio[/green]  (Stage 1)")
    table.add_row("5", "[magenta]Agregar Subtítulos[/magenta]  (Stage 3)")
    table.add_row("6", "[yellow]Coloración[/yellow]  (Stage 4 - Opcional)")
    table.add_row("", "")
    table.add_row("7", "Presets")
    table.add_row("8", "Configuración")
    table.add_row("9", "Preview Audio")
    table.add_row("0", "Salir")

    panel = Panel(
        table,
        title="[bold]Menú Principal[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def get_main_menu_choice() -> str:
    return Prompt.ask(
        "[bold cyan]Selecciona una opción[/bold cyan]",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        default="",
    )


def print_session_info(session) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="dim", width=20)
    table.add_column(style="white")

    table.add_row("Sesión:", f"[bold]{session.session_id}[/bold]")
    table.add_row("Tema:", session.topic)
    table.add_row("Perfil:", session.profile or "default")
    table.add_row("Estado:", f"[yellow]{session.status}[/yellow]")

    console.print(
        Panel(table, title="[bold]Info de Sesión[/bold]", border_style="blue")
    )


def print_stage_status(stages: list[tuple[str, str]]) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(width=3)
    table.add_column(width=15)
    table.add_column()

    for name, status in stages:
        if status == "done":
            icon = "[green]✓[/green]"
        elif status == "current":
            icon = "[bold yellow]>[/bold yellow]"
        elif status == "pending":
            icon = "[dim]○[/dim]"
        else:
            icon = "[red]✗[/red]"

        style = "white" if status != "current" else "bold cyan"
        table.add_row(icon, f"[{style}]{name}[/{style}]", status)

    console.print(
        Panel(table, title="[bold]Pipeline Stages[/bold]", border_style="cyan")
    )


def prompt_session_id(default: str = "", max_retries: int = 3) -> str:
    from scripts.utils.validation import SessionIdValidator

    for attempt in range(max_retries):
        value = Prompt.ask(
            "[bold cyan]ID de sesión[/bold cyan] (YYYYMMDD_slug)",
            default=default,
        )

        result = SessionIdValidator.validate(value)
        if result.is_valid and result.value:
            return str(result.value)

        print_error(result.error or "Validación fallida")
        console.print(f"[dim]Intento {attempt + 1}/{max_retries}[/dim]")

    print_warning("Usando valor por defecto")
    return default or "20260328_default"


def prompt_topic(max_retries: int = 3) -> str:
    from scripts.utils.validation import TopicValidator

    for attempt in range(max_retries):
        value = Prompt.ask("[bold cyan]Tema del video[/bold cyan]")

        result = TopicValidator.validate(value)
        if result.is_valid and result.value:
            return str(result.value)

        print_error(result.error or "Validación fallida")
        console.print(f"[dim]Intento {attempt + 1}/{max_retries}[/dim]")

    print_warning("Por favor ingresa un tema válido")
    return ""


def prompt_duration(default: float = 10.0, max_retries: int = 3) -> float:
    from scripts.utils.validation import DurationValidator

    for attempt in range(max_retries):
        value = Prompt.ask(
            "[bold cyan]Duración aproximada (minutos)[/bold cyan]",
            default=str(default),
        )

        result = DurationValidator.validate(value)
        if result.is_valid and result.value is not None:
            return float(result.value)

        print_error(result.error or "Validación fallida")
        console.print(f"[dim]Ejemplo: 0.5 (30 segundos), 1.5 (90 segundos)[/dim]")
        console.print(f"[dim]Intento {attempt + 1}/{max_retries}[/dim]")

    print_warning(f"Usando valor por defecto: {default} minutos")
    return default


def prompt_profile() -> str:
    # Simplified - single "default" profile for all content
    return "default"


def prompt_goal() -> str:
    console.print("\n[bold]Objetivo del video:[/bold]")
    console.print("  1. [cyan]Educativo[/cyan]")
    console.print("  2. [cyan]Entretenimiento[/cyan]")
    console.print("  3. [cyan]Tutorial[/cyan]")
    console.print("  4. [cyan]Review[/cyan]")

    choice = Prompt.ask(
        "\n[bold cyan]Selecciona[/bold cyan]",
        choices=["1", "2", "3", "4"],
        default="1",
    )

    goals = {"1": "educativo", "2": "entretenimiento", "3": "tutorial", "4": "review"}
    return goals[choice]


def prompt_tone() -> str:
    console.print("\n[bold]Tono del video:[/bold]")
    console.print("  1. [cyan]Directo y prático[/cyan]")
    console.print("  2. [cyan]Amigable[/cyan]")
    console.print("  3. [cyan]Profesional[/cyan]")
    console.print("  4. [cyan]Casual[/cyan]")

    choice = Prompt.ask(
        "\n[bold cyan]Selecciona[/bold cyan]",
        choices=["1", "2", "3", "4"],
        default="1",
    )

    tones = {
        "1": "directo y prático",
        "2": "amigable",
        "3": "profesional",
        "4": "casual",
    }
    return tones[choice]


def print_file_picker_menu(
    mode: str,
    files: list,
    current_path: str = "",
) -> None:
    if mode == "auto":
        panel = Panel(
            f"[bold yellow]Archivos encontrados en:[/bold yellow]\n[current_path]",
            title="[bold]Auto-detectar[/bold]",
            border_style="green",
        )
        console.print(panel)
    elif mode == "browse":
        console.print(f"\n[bold yellow]Directorio:[/bold yellow] {current_path}\n")
    elif mode == "manual":
        console.print("\n[bold]Introduce la ruta manualmente:[/bold]")

    for i, f in enumerate(files, 1):
        if hasattr(f, "size_mb"):
            console.print(f"  {i}. [cyan]{f.name}[/cyan]  [dim]({f.size_mb} MB)[/dim]")
        else:
            console.print(f"  {i}. {f}")


def get_file_selection(max_idx: int) -> str:
    return Prompt.ask(
        "\n[bold cyan]Selecciona archivo (0 para volver)[/bold cyan]",
        default="",
    )


def prompt_manual_path() -> str:
    return Prompt.ask("[bold cyan]Ruta del archivo[/bold cyan]")


def confirm_continue(prompt: str) -> bool:
    return Confirm.ask(f"\n[bold yellow]{prompt}[/bold yellow]")


def print_pipeline_progress(stage: str, progress: float, status: str) -> None:
    bar_width = 30
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)

    color = "green" if status == "done" else "yellow" if status == "running" else "red"
    console.print(
        f"\n[bold cyan]{stage:12s}[/bold cyan] [{color}]{bar}[/{color}] {int(progress * 100)}%"
    )


def print_error(message: str | None) -> None:
    console.print(f"[bold red]Error:[/bold red] {message or 'Error desconocido'}")


def print_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]ℹ[/bold cyan] {message}")


def print_session_list(sessions: list) -> None:
    if not sessions:
        console.print("[yellow]No hay sesiones[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Tema", style="white")
    table.add_column("Perfil", style="dim")
    table.add_column("Estado", style="yellow")
    table.add_column("Fecha", style="dim")

    for s in sessions:
        date = s.created_at[:10] if s.created_at else ""
        table.add_row(
            s.session_id,
            s.topic[:30],
            s.profile or "-",
            s.status or "-",
            date,
        )

    console.print(table)


def print_stage_menu(session_id: str, current_stage: str) -> None:
    table = Table(show_header=False, box=None)
    table.add_column(width=4)
    table.add_column()

    table.add_row("1", "[cyan]Ejecutar todo el pipeline[/cyan]")
    table.add_row("2", "[cyan]Ejecutar etapa específica[/cyan]")
    table.add_row("3", "[cyan]Ver resultados[/cyan]")
    table.add_row("4", "[cyan]Preview en reproductor[/cyan]")
    table.add_row("5", "[cyan]Reiniciar desde etapa...[/cyan]")
    table.add_row("0", "[dim]Volver[/dim]")

    console.print(
        Panel(
            f"Sesión: [bold]{session_id}[/bold] | Stage: [yellow]{current_stage}[/yellow]",
            title="[bold]Continuar Sesión[/bold]",
            border_style="cyan",
        )
    )
    console.print(table)


def print_settings_menu(current_settings: dict) -> None:
    table = Table(show_header=False, box=None)
    table.add_column(width=30)
    table.add_column()

    table.add_row(
        "[cyan]Grabaciones:[/cyan]", current_settings.get("recordings_mount", "")
    )
    table.add_row(
        "[cyan]Modelo Whisper:[/cyan]", current_settings.get("whisper_model", "")
    )
    table.add_row(
        "[cyan]Resolución proxy:[/cyan]", current_settings.get("proxy_resolution", "")
    )

    console.print(
        Panel(table, title="[bold]Configuración Actual[/bold]", border_style="cyan")
    )


def prompt_setting_change() -> str:
    console.print("\n[bold]Qué deseas modificar?[/bold]")
    console.print("  1. [cyan]Directorio de grabaciones[/cyan]")
    console.print("  2. [cyan]Modelo Whisper[/cyan]")
    console.print("  3. [cyan]Resolución proxy[/cyan]")
    console.print("  0. [dim]Volver[/dim]")

    return Prompt.ask(
        "\n[bold cyan]Selecciona opción[/bold cyan]",
        choices=["0", "1", "2", "3"],
        default="0",
    )


def print_presets_menu(preset_type: str = "subtitle") -> None:
    """Print the presets submenu."""
    table = Table(show_header=False, box=None)
    table.add_column(width=4)
    table.add_column()

    table.add_row("1", "[cyan]Ver presets de Subtítulos[/cyan]")
    table.add_row("2", "[cyan]Ver presets de Audio[/cyan]")
    table.add_row("3", "[cyan]Ver presets de Color[/cyan]")
    table.add_row("4", "[cyan]Crear nuevo preset[/cyan]")
    table.add_row("5", "[cyan]Editar preset[/cyan]")
    table.add_row("6", "[cyan]Eliminar preset[/cyan]")
    table.add_row("0", "[dim]Volver[/dim]")

    console.print(
        Panel(
            table,
            title="[bold]Gestión de Presets[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def print_video_files(files: list, title: str = "Archivos de video") -> None:
    """Print a list of video files for selection."""
    if not files:
        console.print("[yellow]No hay archivos de video[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Archivo", style="cyan")
    table.add_column("Tamaño", style="dim")

    for i, f in enumerate(files, 1):
        size = f.stat().st_size / 1024 / 1024 if f.exists() else 0
        table.add_row(str(i), f.name, f"{size:.1f} MB")

    console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="cyan"))


def clear_screen() -> None:
    console.clear()
