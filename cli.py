#!/usr/bin/env python3
"""
Content-OS CLI
Menu-driven video content pipeline
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ui import menus
from scripts.utils.session import SessionManager, load_settings, ensure_session_dirs
from scripts.utils import filepicker
from scripts.core import Pipeline
from scripts.config import ConfigProvider, reset_config


WORKSPACE_ROOT = str(PROJECT_ROOT)
settings = load_settings(WORKSPACE_ROOT)
session_manager = SessionManager(WORKSPACE_ROOT)
pipeline = Pipeline(WORKSPACE_ROOT)


def run_new_session() -> None:
    menus.console.print("\n[bold cyan]=== Nueva Sesion ===[/bold cyan]\n")

    # Step 1: Session ID
    today = datetime.now().strftime("%Y%m%d")
    default_id = today  # e.g., "20260328"
    session_id = menus.prompt_session_id(default_id)
    if not session_id:
        menus.print_error("ID de sesion requerido")
        return

    # Step 2: Topic
    topic = menus.prompt_topic()
    if not topic:
        menus.print_error("Tema requerido")
        return

    # Step 3: Profile
    profile = menus.prompt_profile()

    # Step 4: Goal
    goal = menus.prompt_goal()

    # Step 5: Tone
    tone = menus.prompt_tone()

    # Step 6: Duration (convert float minutes to int)
    duration_minutes = menus.prompt_duration()
    duration = int(round(duration_minutes))

    # Step 7: Camera file
    menus.console.print(
        "\n[bold cyan]=== Seleccionar archivo de camara ===[/bold cyan]"
    )
    camera_path = run_file_picker("camera")
    if not camera_path:
        menus.print_error("Archivo de camara requerido")
        return

    # Step 8: Screen file (optional - for b-roll/screen capture)
    menus.console.print(
        "\n[bold cyan]=== Archivo de pantalla/B-Roll (opcional) ===[/bold cyan]"
    )
    menus.console.print("  1. [cyan]Si[/cyan] - tengo archivo de pantalla o B-Roll")
    menus.console.print("  2. [cyan]No[/cyan] - solo tengo camara")

    has_screen = menus.Prompt.ask(
        "\n[bold]Tienes pantalla o B-Roll?[/bold]",
        choices=["1", "2"],
        default="2",
    )

    if has_screen == "1":
        screen_path = run_file_picker("screen", exclude=camera_path)
        if screen_path is None:
            screen_path = ""
    else:
        screen_path = ""
        menus.print_warning("Continuando sin pantalla/B-Roll")

    # Create session
    ensure_session_dirs(WORKSPACE_ROOT, session_id)
    session = session_manager.create_session(
        session_id=session_id,
        topic=topic,
        profile=profile,
        goal=goal,
        tone=tone,
        duration=duration,
    )
    session.camera_file = camera_path
    session.screen_file = screen_path
    session_manager.save_session(session)

    menus.print_success(f"Sesion '{session_id}' creada")
    menus.print_info(f"Archivos: {camera_path}, {screen_path}")

    # Ask to run pipeline
    if menus.confirm_continue("Ejecutar pipeline ahora?"):
        run_pipeline(session_id)


def run_file_picker(purpose: str, exclude: Optional[str] = None) -> Optional[str]:
    """Run file picker with 3 modes: auto, browse, manual"""
    mount = settings.get("recordings_mount", "/mnt/c/Users/carlos/Videos")

    while True:
        menus.console.print(
            f"\n[bold cyan]Seleccionar archivo ({purpose}):[/bold cyan]"
        )
        menus.console.print("  1. [cyan]Auto-detectar[/cyan] en carpeta de grabaciones")
        menus.console.print("  2. [cyan]Explorar[/cyan] directorio")
        menus.console.print("  3. [cyan]Introducir[/cyan] ruta manualmente")
        menus.console.print("  0. [dim]Volver[/dim]")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona[/bold]",
            choices=["0", "1", "2", "3"],
            default="1",
        )

        if choice == "0":
            return None

        elif choice == "1":
            # Auto-detect
            videos = filepicker.find_videos_in_mount(mount)
            videos = filepicker.select_video(videos, exclude)

            if not videos:
                if exclude:
                    menus.print_warning(
                        f"Solo hay un video (usado para {purpose}), usa Explorar o Introducir ruta"
                    )
                else:
                    menus.print_warning(f"No se encontraron videos en {mount}")
                continue

            menus.console.print(f"\n[bold]Videos encontrados:[/bold]")
            for i, v in enumerate(videos, 1):
                menus.console.print(f"  {i}. [cyan]{v.name}[/cyan] ({v.size_mb} MB)")

            idx = menus.Prompt.ask(
                "\n[bold]Selecciona (0 para volver):[/bold]",
                default="",
            )

            if idx == "0" or not idx:
                continue

            try:
                selected = videos[int(idx) - 1]
                return selected.path
            except (ValueError, IndexError):
                menus.print_error("Seleccion invalida")

        elif choice == "2":
            # Browse with intuitive navigation
            current_path = mount

            while True:
                entries, current = filepicker.browse_directory(
                    current_path, show_hidden=False
                )

                if not entries:
                    menus.print_warning(
                        "Directorio vacio o solo tiene archivos ocultos"
                    )
                    if current == "/":
                        break
                    current_path = filepicker.navigate_to_parent(current)
                    continue

                # Show navigation help
                menus.console.print(f"\n[bold cyan]📁 {current}[/bold cyan]")
                menus.console.print(
                    "[dim]Comandos: ↑ = parent | Enter = seleccionar archivo | q = salir[/dim]"
                )
                menus.console.print()

                # Group: directories first, then videos
                dirs = [
                    (i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if e[2]
                ]
                videos = [
                    (i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if not e[2]
                ]

                # Show directories
                if dirs:
                    menus.console.print("[bold]Carpetas:[/bold]")
                    for num, display, path, is_dir in dirs:
                        menus.console.print(f"  [{num}] {display}")

                # Show videos
                if videos:
                    menus.console.print("[bold]Videos:[/bold]")
                    for num, display, path, is_dir in videos:
                        menus.console.print(f"  [{num}] [green]{display}[/green]")

                # Build choices
                all_nums = [str(n) for n, _, _, _ in dirs + videos]
                choices = all_nums + ["0", "q", "p", "h"]

                idx = menus.Prompt.ask(
                    "\n[bold]Numero para entrar/carpeta, Enter para archivo, 0/p=parent, q=salir:[/bold]",
                    choices=choices,
                    default="",
                )

                if idx == "0" or idx == "p":
                    if current == "/":
                        break
                    current_path = filepicker.navigate_to_parent(current)
                    continue

                if idx == "q":
                    break

                if idx == "":
                    if videos:
                        _, display, path, _ = videos[0]
                        menus.print_success(f"Seleccionado: {path}")
                        return path
                    menus.print_warning("No hay archivos de video para seleccionar")
                    continue

                if idx == "h":
                    # Toggle hidden files
                    entries, current = filepicker.browse_directory(
                        current_path, show_hidden=True
                    )
                    # Re-process with hidden
                    dirs = [
                        (i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if e[2]
                    ]
                    videos = [
                        (i + 1, e[0], e[1], e[2])
                        for i, e in enumerate(entries)
                        if not e[2]
                    ]
                    all_nums = [str(n) for n, _, _, _ in dirs + videos]
                    continue

                try:
                    num = int(idx)
                    # Find in dirs first
                    for _, display, path, is_dir in dirs:
                        if num == int(idx):
                            if is_dir:
                                current_path = path
                                break
                            else:
                                # It's a video file
                                menus.print_success(f"Seleccionado: {path}")
                                return path
                    else:
                        # Check videos
                        for _, display, path, is_dir in videos:
                            if num == int(idx):
                                menus.print_success(f"Seleccionado: {path}")
                                return path
                except (ValueError, IndexError):
                    menus.print_error("Seleccion invalida")

        elif choice == "3":
            # Manual
            path = menus.prompt_manual_path()
            if filepicker.validate_video(path):
                return path
            else:
                menus.print_error("Archivo no encontrado o formato no valido")


def run_continue_session() -> None:
    sessions = session_manager.list_sessions()

    if not sessions:
        menus.print_warning("No hay sesiones")
        return

    menus.console.print("\n[bold cyan]=== Continuar Sesion ===[/bold cyan]\n")
    menus.print_session_list(sessions)

    session_id = menus.prompt_session_id()
    if not session_id:
        return

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        menus.print_error(f"Sesion '{session_id}' no encontrada")
        return

    menus.print_session_info(session)

    # Show continue menu
    current_stage = session.status or "created"

    while True:
        # Refresh session status
        session = session_manager.load_session(session_id)
        current_stage = session.status or "created"

        menus.console.print(f"\n[bold cyan]=== {session_id} ===[/bold cyan]")
        menus.console.print(f"Estado: [yellow]{current_stage}[/yellow]")
        menus.console.print(
            f"Perfil: {session.profile or 'longform'} | Tema: {session.topic}"
        )
        menus.console.print()
        menus.console.print("  1. [green]Ejecutar todo el pipeline[/green]")
        menus.console.print("  2. [cyan]Ejecutar etapa especifica[/cyan]")
        menus.console.print("  3. [magenta]Ver resultados[/magenta]")
        menus.console.print("  0. [dim]Volver al menu principal[/dim]")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona[/bold]",
            choices=["0", "1", "2", "3"],
            default="",
        )

        if choice == "0":
            break
        elif choice == "1":
            run_pipeline(session_id)
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()
        elif choice == "2":
            run_single_stage(session_id)
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()
        elif choice == "3":
            view_results(session_id)
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()


def run_pipeline(session_id: str) -> None:
    menus.console.print(
        f"\n[bold cyan]Ejecutando pipeline para {session_id}...[/bold cyan]\n"
    )

    def on_progress(stage_name: str, status: str):
        if status == "running":
            menus.console.print(f"[bold cyan]→ {stage_name}[/bold cyan]")
        elif status == "done":
            menus.print_success(f"{stage_name} completado")
        elif status == "failed":
            menus.print_error(f"{stage_name} fallo")

    try:
        pipeline.run_full(session_id, on_progress=on_progress)
        menus.print_success("Pipeline completado!")
    except Exception as e:
        menus.print_error(f"Pipeline fallo: {e}")


def run_single_stage(session_id: str) -> None:
    session = session_manager.load_session(session_id)

    profile = session.profile or "longform"
    stages = pipeline.get_stages_for_profile(profile)

    menus.console.print("\n[bold]Etapas disponibles:[/bold]")
    for i, stage in enumerate(stages, 1):
        menus.console.print(f"  {i}. {stage.description}")
    menus.console.print("  0. Cancelar")

    choice = menus.Prompt.ask(
        "\n[bold]Selecciona etapa[/bold]",
        choices=["0"] + [str(i) for i in range(1, len(stages) + 1)],
    )

    if choice == "0":
        return

    idx = int(choice) - 1
    stage = stages[idx]

    menus.console.print(f"\n[bold cyan]Ejecutando {stage.description}...[/bold cyan]")

    try:
        pipeline.run_stage(session_id, stage.name)
        menus.print_success(f"{stage.description} completado")
    except Exception as e:
        menus.print_error(f"Error: {e}")


def view_results(session_id: str) -> None:
    session = session_manager.load_session(session_id)

    menus.console.print(f"\n[bold cyan]Resultados de {session_id}[/bold cyan]\n")

    base = Path(WORKSPACE_ROOT)

    # List files in each output dir
    dirs = [
        ("Grabaciones", base / "recordings" / session_id),
        ("Proxies", base / "proxies" / session_id),
        ("Audio", base / "audio" / session_id),
        ("Transcripcion", base / "transcripts" / session_id),
        ("Analisis", base / "analysis" / session_id),
        ("Cutmaps", base / "cutmaps" / session_id),
        ("Exportes", base / "exports" / session_id),
    ]

    for name, d in dirs:
        if d.exists():
            files = list(d.iterdir())
            if files:
                menus.console.print(f"[bold]{name}:[/bold]")
                for f in files:
                    size = f.stat().st_size / 1024
                    menus.console.print(f"  - {f.name} ({size:.1f} KB)")
            else:
                menus.console.print(f"[bold]{name}:[/bold] [dim]vacio[/dim]")


def preview_session(session_id: str) -> None:
    import subprocess

    session = session_manager.load_session(session_id)

    exports_dir = Path(WORKSPACE_ROOT) / "exports" / session_id
    videos = list(exports_dir.glob("*.mp4"))

    if not videos:
        menus.print_warning("No hay videos para preview")
        return

    menus.console.print("\n[bold]Videos disponibles:[/bold]")
    for i, v in enumerate(videos, 1):
        menus.console.print(f"  {i}. {v.name}")

    idx = menus.Prompt.ask(
        "\n[bold]Selecciona video (0 para cancelar)[/bold]", default=""
    )
    if not idx or idx == "0":
        return

    try:
        video = videos[int(idx) - 1]
        menus.print_info(f"Abriendo {video.name} con reproductor...")
        subprocess.run(["xdg-open", str(video)], check=False)
    except Exception as e:
        menus.print_error(f"No se pudo abrir: {e}")


def preview_audio(session_id: str) -> None:
    import subprocess
    import json

    session = session_manager.load_session(session_id)

    # Use master_voice.wav (VAD extracted + cleaned) or fallback to master.wav
    voice_audio = Path(WORKSPACE_ROOT) / "audio" / session_id / "master_voice.wav"
    raw_audio = Path(WORKSPACE_ROOT) / "audio" / session_id / "master.wav"
    report_file = (
        Path(WORKSPACE_ROOT) / "analysis" / session_id / "preprocess_report.json"
    )

    if not voice_audio.exists() and not raw_audio.exists():
        menus.print_warning("Audio no encontrado")
        menus.print_info("Ejecuta 'Proxies' primero")
        return

    menus.console.print(f"\n[bold cyan]=== Preview Audio ===[/bold cyan]\n")
    menus.console.print(f"Session: [yellow]{session_id}[/yellow]")
    menus.console.print(f"Perfil: {session.profile or 'longform'}")
    menus.console.print(f"Audio: [green]{clean_audio.name}[/green]")

    if report_file.exists():
        report = json.loads(report_file.read_text())
        before = report.get("before", {})
        after = report.get("after", {})

        menus.console.print("\n[bold]Procesamiento:[/bold]")
        menus.console.print(
            f"  RMS:      {before.get('rms_db', 0):.1f}dB → [green]{after.get('rms_db', 0):.1f}dB[/green]"
        )
        menus.console.print(
            f"  Noise:   {before.get('noise_floor_db', 0):.1f}dB → [green]{after.get('noise_floor_db', 0):.1f}dB[/green]"
        )
        menus.console.print(
            f"  SNR:     {before.get('snr_estimate_db', 0):.1f}dB → [green]{after.get('snr_estimate_db', 0):.1f}dB[/green]"
        )

        errors = report.get("errors", [])
        warnings = report.get("warnings", [])

        if errors:
            menus.console.print("\n[bold red]Errores:[/bold red]")
            for e in errors:
                menus.console.print(f"  - {e}")

        if warnings:
            menus.console.print("\n[bold yellow]Advertencias:[/bold yellow]")
            for w in warnings:
                menus.console.print(f"  - {w}")

    menus.console.print()
    play = menus.Prompt.ask(
        "[bold]Reproducir audio?[/bold] (s/n)",
        choices=["s", "S", "n", "N"],
        default="s",
    )

    if play.lower() == "s":
        menus.print_info("Reproduciendo... (cierra el reproductor cuando termines)")
        subprocess.run(["xdg-open", str(clean_audio)], check=False)

        menus.console.print()
        menus.console.print("[bold]Ajustes de audio:[/bold]")
        menus.console.print("  5. [cyan]Menu Audio[/cyan] - modificar filtros")

        again = menus.Prompt.ask(
            "\n[bold]Otra vez?[/bold] (s/n)", choices=["s", "S", "n", "N"], default="n"
        )

        if again.lower() == "s":
            preview_audio(session_id)


def list_sessions() -> None:
    sessions = session_manager.list_sessions()
    menus.print_session_list(sessions)


def run_settings() -> None:
    menus.console.print("\n[bold cyan]=== Configuracion ===[/bold cyan]\n")
    menus.print_settings_menu(settings)

    choice = menus.prompt_setting_change()

    if choice == "0":
        return
    elif choice == "1":
        new_path = menus.Prompt.ask(
            "Nuevo directorio de grabaciones",
            default=settings.get("recordings_mount", ""),
        )
        settings["recordings_mount"] = new_path
    elif choice == "2":
        new_model = menus.Prompt.ask(
            "Nuevo modelo Whisper", default=settings.get("whisper_model", "large-v2")
        )
        settings["whisper_model"] = new_model
    elif choice == "3":
        new_res = menus.Prompt.ask(
            "Nueva resolucion proxy (ej: 1280x720)",
            default=settings.get("proxy_resolution", "1280x720"),
        )
        settings["proxy_resolution"] = new_res

    # Save settings
    import json

    settings_file = Path(WORKSPACE_ROOT) / "config" / "settings.json"
    settings_file.write_text(json.dumps(settings, indent=2))
    menus.print_success("Configuracion guardada")


def run_audio_settings() -> None:
    import json

    reset_config()
    config = ConfigProvider(WORKSPACE_ROOT)

    while True:
        menus.console.print("\n[bold cyan]=== Configuracion de Audio ===[/bold cyan]\n")

        hp = config.get_highpass_settings()
        afftdn = config.get_afftdn_settings()
        comp = config.get_compressor_settings()
        gate = config.get_agate_settings()
        eq = config.get_eq_settings()
        loud = config.get_loudnorm_settings()

        menus.console.print(
            "[bold]1. Highpass:[/bold] freq={}Hz, muffled={}Hz".format(
                hp.get("default_freq"), hp.get("muffled_voice_freq")
            )
        )
        menus.console.print(
            "[bold]2. Denoising:[/bold] mild={}, moderate={}, heavy={}, max={}".format(
                afftdn.get("nr_mild"),
                afftdn.get("nr_moderate"),
                afftdn.get("nr_heavy"),
                afftdn.get("nr_max_voice"),
            )
        )
        menus.console.print(
            "[bold]3. Compressor:[/bold] threshold={}dB, ratio={}:1, makeup={}dB".format(
                comp.get("threshold_db"), comp.get("ratio"), comp.get("makeup_db")
            )
        )
        menus.console.print(
            "[bold]4. Noise Gate:[/bold] above_floor={}dB, ratio={}".format(
                gate.get("above_floor_db"), gate.get("ratio_heavy")
            )
        )
        menus.console.print(
            "[bold]5. EQ Presence:[/bold] freq={}Hz, gain={}dB".format(
                eq.get("presence", {}).get("freq"), eq.get("presence", {}).get("gain")
            )
        )
        menus.console.print(
            "[bold]6. Loudnorm:[/bold] longform=I:{} TP:{} LRA:{}".format(
                loud.get("longform", {}).get("I"),
                loud.get("longform", {}).get("TP"),
                loud.get("longform", {}).get("LRA"),
            )
        )
        menus.console.print()
        menus.console.print("  0. [dim]Volver[/dim]")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona parametro a modificar[/bold]",
            choices=["0", "1", "2", "3", "4", "5", "6"],
        )

        if choice == "0":
            break

        filters_file = Path(WORKSPACE_ROOT) / "config" / "filters.json"
        filters = json.loads(filters_file.read_text())

        if choice == "1":
            menus.console.print("\n[bold]Highpass:[/bold]")
            new_freq = menus.Prompt.ask(
                "Frecuencia normal (Hz)", default=str(hp.get("default_freq"))
            )
            new_muffled = menus.Prompt.ask(
                "Frecuencia para voz amortiguada (Hz)",
                default=str(hp.get("muffled_voice_freq")),
            )
            filters["highpass"]["default_freq"] = int(new_freq)
            filters["highpass"]["muffled_voice_freq"] = int(new_muffled)

        elif choice == "2":
            menus.console.print("\n[bold]Denoising (afftdn):[/bold]")
            new_mild = menus.Prompt.ask(
                "NR mild (8-15)", default=str(afftdn.get("nr_mild"))
            )
            new_mod = menus.Prompt.ask(
                "NR moderate (15-25)", default=str(afftdn.get("nr_moderate"))
            )
            new_heavy = menus.Prompt.ask(
                "NR heavy (25-40)", default=str(afftdn.get("nr_heavy"))
            )
            filters["afftdn"]["nr_mild"] = int(new_mild)
            filters["afftdn"]["nr_moderate"] = int(new_mod)
            filters["afftdn"]["nr_heavy"] = int(new_heavy)

        elif choice == "3":
            menus.console.print("\n[bold]Compressor:[/bold]")
            new_thresh = menus.Prompt.ask(
                "Threshold (-10 a -30 dB)", default=str(comp.get("threshold_db"))
            )
            new_ratio = menus.Prompt.ask("Ratio (2-10)", default=str(comp.get("ratio")))
            new_makeup = menus.Prompt.ask(
                "Makeup gain (0-20 dB)", default=str(comp.get("makeup_db"))
            )
            filters["compressor"]["threshold_db"] = int(new_thresh)
            filters["compressor"]["ratio"] = int(new_ratio)
            filters["compressor"]["makeup_db"] = int(new_makeup)

        elif choice == "4":
            menus.console.print("\n[bold]Noise Gate:[/bold]")
            new_above = menus.Prompt.ask(
                "Above floor (4-10 dB)", default=str(gate.get("above_floor_db"))
            )
            new_ratio = menus.Prompt.ask(
                "Ratio (4-20)", default=str(gate.get("ratio_heavy"))
            )
            filters["agate"]["above_floor_db"] = int(new_above)
            filters["agate"]["ratio_heavy"] = int(new_ratio)

        elif choice == "5":
            menus.console.print("\n[bold]EQ Presence:[/bold]")
            new_freq = menus.Prompt.ask(
                "Frecuencia (2000-6000 Hz)",
                default=str(eq.get("presence", {}).get("freq")),
            )
            new_gain = menus.Prompt.ask(
                "Ganancia (-3 a +6 dB)", default=str(eq.get("presence", {}).get("gain"))
            )
            filters["eq"]["presence"]["freq"] = int(new_freq)
            filters["eq"]["presence"]["gain"] = int(new_gain)

        elif choice == "6":
            menus.console.print("\n[bold]Loudnorm:[/bold]")
            new_i = menus.Prompt.ask(
                "I target (-3 a -20)", default=str(loud.get("longform", {}).get("I"))
            )
            new_tp = menus.Prompt.ask(
                "True Peak (-0.5 a -3)", default=str(loud.get("longform", {}).get("TP"))
            )
            new_lra = menus.Prompt.ask(
                "LRA (4-15)", default=str(loud.get("longform", {}).get("LRA"))
            )
            filters["loudnorm"]["longform"]["I"] = int(new_i)
            filters["loudnorm"]["longform"]["TP"] = float(new_tp)
            filters["loudnorm"]["longform"]["LRA"] = int(new_lra)
            filters["loudnorm"]["shorts"]["I"] = int(new_i) + 2
            filters["loudnorm"]["shorts"]["TP"] = float(new_tp)
            filters["loudnorm"]["shorts"]["LRA"] = int(new_lra) - 3

        filters_file.write_text(json.dumps(filters, indent=2))
        reset_config()
        config = ConfigProvider(WORKSPACE_ROOT)
        menus.print_success("Configuracion guardada")


def run_audio_preview_select() -> None:
    sessions = session_manager.list_sessions()

    if not sessions:
        menus.print_warning("No hay sesiones")
        return

    menus.console.print("\n[bold cyan]=== Preview Audio ===[/bold cyan]\n")
    menus.print_session_list(sessions)

    session_id = menus.prompt_session_id()
    if not session_id:
        return

    try:
        preview_audio(session_id)
    except FileNotFoundError:
        menus.print_error(f"Sesion '{session_id}' no encontrada")


def main():
    menus.clear_screen()
    menus.print_header()

    while True:
        try:
            menus.clear_screen()
            menus.print_header()
            menus.print_main_menu()
            choice = menus.get_main_menu_choice()

            if choice == "0":
                menus.console.print("\n[bold yellow]Hasta luego![/bold yellow]\n")
                break
            elif choice == "1":
                menus.clear_screen()
                run_new_session()
            elif choice == "2":
                menus.clear_screen()
                run_continue_session()
            elif choice == "3":
                menus.clear_screen()
                list_sessions()
            elif choice == "4":
                menus.clear_screen()
                run_settings()
            elif choice == "5":
                menus.clear_screen()
                run_audio_settings()
            elif choice == "6":
                menus.clear_screen()
                run_audio_preview_select()

            if choice != "0":
                menus.Prompt.ask(
                    "\n[dim]Presiona Enter para continuar...[/dim]", default=""
                )

        except KeyboardInterrupt:
            menus.console.print(
                "\n\n[bold yellow]Ctrl+C detectado. Saliendo...[/bold yellow]\n"
            )
            break
        except EOFError:
            menus.console.print(
                "\n\n[bold yellow]Entrada cerrada. Saliendo...[/bold yellow]\n"
            )
            break


if __name__ == "__main__":
    main()
