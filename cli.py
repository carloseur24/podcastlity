#!/usr/bin/env python3
"""
Content-OS CLI
Menu-driven video content pipeline
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import ConfigProvider, reset_config
from scripts.core import Pipeline
from scripts.preset_manager import get_preset_manager
from scripts.ui import menus
from scripts.utils import filepicker
from scripts.utils.session import SessionManager, ensure_session_dirs, load_settings

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

    # Step 3: Duration (convert float minutes to int)
    duration_minutes = menus.prompt_duration()
    duration = int(round(duration_minutes))

    # Step 4: Video file (single input)
    menus.console.print("\n[bold cyan]=== Seleccionar archivo de video ===[/bold cyan]")
    video_path = run_file_picker("video")
    if not video_path:
        menus.print_error("Archivo de video requerido")
        return

    # Create session
    ensure_session_dirs(WORKSPACE_ROOT, session_id)
    session = session_manager.create_session(
        session_id=session_id,
        topic=topic,
        duration=duration,
    )
    session.video_file = video_path
    session_manager.save_session(session)

    menus.print_success(f"Sesion '{session_id}' creada")
    menus.print_info(f"Video: {video_path}")

    # Ask to run pipeline
    if menus.confirm_continue("Ejecutar pipeline ahora?"):
        run_pipeline(session_id)


def run_file_picker(purpose: str, exclude: str | None = None) -> str | None:
    """Run file picker with 3 modes: auto, browse, manual"""
    mount = settings.get("recordings_mount", "/mnt/c/Users/carlos/Videos")

    while True:
        menus.console.print(f"\n[bold cyan]Seleccionar archivo ({purpose}):[/bold cyan]")
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

            menus.console.print("\n[bold]Videos encontrados:[/bold]")
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
                entries, current = filepicker.browse_directory(current_path, show_hidden=False)

                if not entries:
                    menus.print_warning("Directorio vacio o solo tiene archivos ocultos")
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
                dirs = [(i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if e[2]]
                videos = [(i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if not e[2]]

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
                    entries, current = filepicker.browse_directory(current_path, show_hidden=True)
                    # Re-process with hidden
                    dirs = [(i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if e[2]]
                    videos = [(i + 1, e[0], e[1], e[2]) for i, e in enumerate(entries) if not e[2]]
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
        menus.console.print(f"Perfil: {session.profile or 'default'} | Tema: {session.topic}")
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
    menus.console.print(f"\n[bold cyan]Ejecutando pipeline para {session_id}...[/bold cyan]\n")

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

    profile = session.profile or "default"
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
        ("Grabaciones", base / "data" / "recordings" / session_id),
        ("Proxies", base / "output" / "proxies" / session_id),
        ("Audio", base / "output" / "audio" / session_id),
        ("Transcripcion", base / "output" / "transcripts" / session_id),
        ("Analisis", base / "output" / "analysis" / session_id),
        ("Cutmaps", base / "output" / "cutmaps" / session_id),
        ("Exportes", base / "output" / "exports" / session_id),
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

    exports_dir = Path(WORKSPACE_ROOT) / "output" / "exports" / session_id
    videos = list(exports_dir.glob("*.mp4"))

    if not videos:
        menus.print_warning("No hay videos para preview")
        return

    menus.console.print("\n[bold]Videos disponibles:[/bold]")
    for i, v in enumerate(videos, 1):
        menus.console.print(f"  {i}. {v.name}")

    idx = menus.Prompt.ask("\n[bold]Selecciona video (0 para cancelar)[/bold]", default="")
    if not idx or idx == "0":
        return

    try:
        video = videos[int(idx) - 1]
        menus.print_info(f"Abriendo {video.name} con reproductor...")
        subprocess.run(["xdg-open", str(video)], check=False)
    except Exception as e:
        menus.print_error(f"No se pudo abrir: {e}")


def preview_audio(session_id: str) -> None:
    import json
    import subprocess

    session = session_manager.load_session(session_id)

    # Use master_voice.wav (VAD extracted + cleaned) or fallback to master.wav
    voice_audio = Path(WORKSPACE_ROOT) / "output" / "audio" / session_id / "master_voice.wav"
    raw_audio = Path(WORKSPACE_ROOT) / "output" / "audio" / session_id / "master.wav"
    report_file = Path(WORKSPACE_ROOT) / "analysis" / session_id / "preprocess_report.json"

    # Determine which audio file exists
    clean_audio = voice_audio if voice_audio.exists() else raw_audio

    if not clean_audio.exists():
        menus.print_warning("Audio no encontrado")
        menus.print_info("Ejecuta 'Proxies' primero")
        return

    menus.console.print("\n[bold cyan]=== Preview Audio ===[/bold cyan]\n")
    menus.console.print(f"Session: [yellow]{session_id}[/yellow]")
    menus.console.print(f"Perfil: {session.profile or 'default'}")
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
            "[bold]6. Loudnorm:[/bold] default=I:{} TP:{} LRA:{}".format(
                loud.get("default", {}).get("I"),
                loud.get("default", {}).get("TP"),
                loud.get("default", {}).get("LRA"),
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
            new_mild = menus.Prompt.ask("NR mild (8-15)", default=str(afftdn.get("nr_mild")))
            new_mod = menus.Prompt.ask(
                "NR moderate (15-25)", default=str(afftdn.get("nr_moderate"))
            )
            new_heavy = menus.Prompt.ask("NR heavy (25-40)", default=str(afftdn.get("nr_heavy")))
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
            new_ratio = menus.Prompt.ask("Ratio (4-20)", default=str(gate.get("ratio_heavy")))
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
                "I target (-3 a -20)", default=str(loud.get("default", {}).get("I"))
            )
            new_tp = menus.Prompt.ask(
                "True Peak (-0.5 a -3)", default=str(loud.get("default", {}).get("TP"))
            )
            new_lra = menus.Prompt.ask(
                "LRA (4-15)", default=str(loud.get("default", {}).get("LRA"))
            )
            filters["loudnorm"]["default"]["I"] = int(new_i)
            filters["loudnorm"]["default"]["TP"] = float(new_tp)
            filters["loudnorm"]["default"]["LRA"] = int(new_lra)

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


# ============================================================================
# NEW STAGE FUNCTIONS - Stage 1, 3, 4
# ============================================================================


def run_stage_1_audio() -> None:
    """Stage 1: Audio Processing - Select session and process audio (NO transcription)."""
    sessions = session_manager.list_sessions()

    if not sessions:
        menus.print_warning("No hay sesiones")
        menus.print_info("Crea una sesión primero (Opción 1)")
        return

    menus.console.print("\n[bold cyan]=== Stage 1: Procesar Audio ===[/bold cyan]\n")
    menus.print_session_list(sessions)

    session_id = menus.prompt_session_id()
    if not session_id:
        return

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        menus.print_error(f"Sesión '{session_id}' no encontrada")
        return

    menus.console.print(f"\n[bold]Procesando audio para {session_id}...[/bold]")
    menus.print_info("Esto incluye: extracción de audio + reducción de ruido")
    menus.print_info("NO incluye transcripción (eso se hace en Stage 3)")

    try:
        # Stage 1: Audio processing ONLY (Proxies + VoiceExtract)
        # NO transcription here - that's Stage 3
        menus.console.print("\n[bold]1/2: Extrayendo audio...[/bold]")
        pipeline.run_stage(session_id, "Proxies")

        menus.console.print("[bold]2/2: Reduciendo ruido y normalizando...[/bold]")
        pipeline.run_stage(session_id, "VoiceExtract")

        menus.print_success("Audio procesado correctamente")
        menus.print_info("Listo para edición manual. Luego usa Stage 3 para subtítulos.")
    except Exception as e:
        menus.print_error(f"Error procesando audio: {e}")


def run_stage_3_subtitles() -> None:
    """Stage 3: Subtitles - Select session, video, transcribe (if needed), render with Remotion."""
    sessions = session_manager.list_sessions()

    if not sessions:
        menus.print_warning("No hay sesiones")
        menus.print_info("Crea una sesión primero")
        return

    menus.console.print("\n[bold magenta]=== Stage 3: Agregar Subtítulos ===[/bold magenta]\n")
    menus.print_session_list(sessions)

    session_id = menus.prompt_session_id()
    if not session_id:
        return

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        menus.print_error(f"Sesión '{session_id}' no encontrada")
        return

    # List video files in session
    session_dir = Path(WORKSPACE_ROOT) / "data" / "recordings" / session_id
    proxies_dir = Path(WORKSPACE_ROOT) / "output" / "proxies" / session_id
    exports_dir = Path(WORKSPACE_ROOT) / "output" / "exports" / session_id

    video_files = []
    for d in [session_dir, proxies_dir, exports_dir]:
        if d.exists():
            video_files.extend(list(d.glob("*.mp4")))
            video_files.extend(list(d.glob("*.mkv")))
            # Exclude already processed videos
            video_files = [
                v for v in video_files if not v.name.startswith(("subtitled_", "colored_"))
            ]

    if not video_files:
        menus.print_warning("No hay videos disponibles en esta sesión")
        menus.print_info("Primero ejecuta Stage 1 (Procesar Audio)")
        return

    # Show video files
    menus.console.print("\n[bold]Videos disponibles:[/bold]")
    for i, v in enumerate(video_files, 1):
        size = v.stat().st_size / 1024 / 1024
        menus.console.print(f"  {i}. [cyan]{v.name}[/cyan] ({size:.1f} MB)")

    choice = menus.Prompt.ask(
        "\n[bold]Selecciona video (0 para cancelar)[/bold]",
        choices=["0"] + [str(i) for i in range(1, len(video_files) + 1)],
        default="1",
    )

    if choice == "0":
        return

    selected_video = video_files[int(choice) - 1]
    menus.print_info(f"Video seleccionado: {selected_video.name}")

    # Check or generate transcription
    transcript_file = Path(WORKSPACE_ROOT) / "output" / "transcripts" / session_id / "segments.json"

    if transcript_file.exists():
        menus.print_info(f"Transcripción encontrada: {transcript_file.name}")
        reuse_transcript = menus.Confirm.ask(
            "\n[bold]¿Reusar transcripción existente?[/bold] (s/n)", default=True
        )
        if not reuse_transcript:
            menus.print_info("Generando nueva transcripción...")
            transcript_file = None  # Will regenerate
    else:
        transcript_file = None
        menus.print_info("No hay transcripción. Generando...")

    # Generate transcription if needed
    if transcript_file is None:
        try:
            menus.console.print("\n[bold]Transcribiendo audio con Whisper...[/bold]")

            # Extract audio if not exists
            audio_dir = Path(WORKSPACE_ROOT) / "output" / "audio" / session_id
            audio_path = audio_dir / "master_voice.wav"

            if not audio_path.exists():
                audio_path = audio_dir / "master.wav"

            if not audio_path.exists():
                menus.print_error("Audio no encontrado. Ejecuta Stage 1 primero.")
                return

            # Run whisper transcription
            pipeline.run_stage(session_id, "Transcribe")

            # Check if transcription was created
            transcript_file = Path(WORKSPACE_ROOT) / "transcripts" / session_id / "segments.json"
            if transcript_file.exists():
                menus.print_success("Transcripción creada")
            else:
                menus.print_error("Error al generar transcripción")
                return

        except Exception as e:
            menus.print_error(f"Error transcribiendo: {e}")
            return

    # Select preset
    pm = get_preset_manager(WORKSPACE_ROOT)
    subtitle_presets = pm.list_subtitle_presets()

    menus.console.print("\n[bold]Presets de subtítulos disponibles:[/bold]")
    for i, p in enumerate(subtitle_presets, 1):
        read_only = "[readonly]" if p["read_only"] else ""
        menus.console.print(f"  {i}. {p['display_name']} {read_only}")
        menus.console.print(f"      [dim]{p['description']}[/dim]")

    preset_choice = menus.Prompt.ask(
        "\n[bold]Selecciona preset (0 para cancelar)[/bold]",
        choices=["0"] + [str(i) for i in range(1, len(subtitle_presets) + 1)],
        default="1",
    )

    if preset_choice == "0":
        return

    selected_preset = subtitle_presets[int(preset_choice) - 1]
    preset_name = selected_preset["name"]

    menus.print_info(f"Preset: {selected_preset['display_name']}")

    # Ask for range (optional)
    use_range = menus.Confirm.ask("\n[bold]¿Usar rango de tiempo?[/bold] (s/n)", default=False)

    start_sec = None
    end_sec = None
    if use_range:
        start_sec = menus.Prompt.ask("Segundo inicial", default="0")
        end_sec = menus.Prompt.ask("Segundo final", default="")
        start_sec = int(start_sec)
        if end_sec:
            end_sec = int(end_sec)

    # Ask for resolution
    menus.console.print("\n[bold]Resolución:[/bold]")
    menus.console.print("  1. [cyan]144p[/cyan] (proxy - más rápido)")
    menus.console.print("  2. [cyan]480p[/cyan] (proxy)")
    menus.console.print("  3. [cyan]1080p[/cyan] (calidad)")
    menus.console.print("  4. [cyan]4k[/cyan] (máxima calidad)")

    res_choice = menus.Prompt.ask(
        "\n[bold]Selecciona resolución[/bold]",
        choices=["1", "2", "3", "4"],
        default="2",
    )

    resolution_map = {"1": "144p", "2": "480p", "3": "1080p", "4": "4k"}
    resolution = resolution_map[res_choice]

    # Run Remotion via subprocess
    import subprocess

    # Paths
    remotion_dir = Path(WORKSPACE_ROOT) / "remotion"
    video_path = selected_video.absolute()
    captions_path = transcript_file.absolute()
    preset_path = remotion_dir / "config" / "presets" / f"{preset_name}.json"

    # If preset doesn't exist in remotion folder, use default
    if not preset_path.exists():
        preset_path = remotion_dir / "config" / "presets" / "test_preset.json"

    # Output path
    output_dir = Path(WORKSPACE_ROOT) / "output" / "exports" / session_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"subtitled_{selected_video.stem}_{resolution}.mp4"
    output_path = output_dir / output_filename

    # Build CLI command
    cmd = [
        "node",
        "cli.js",
        str(video_path),
        str(captions_path),
        str(preset_path),
        "-r",
        resolution,
    ]

    if start_sec is not None:
        cmd.extend(["-s", str(start_sec)])
    if end_sec is not None:
        cmd.extend(["-e", str(end_sec)])

    menus.console.print("\n[bold cyan]Ejecutando Remotion...[/bold cyan]")
    menus.console.print(f"[dim]Comando: {' '.join(cmd)}[/dim]")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(remotion_dir),
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            menus.print_success("Subtítulos renderizados correctamente")
        else:
            menus.print_error(f"Error en renderizado: {result.stderr}")
    except subprocess.TimeoutExpired:
        menus.print_error("Tiempo de renderizado agotado")
    except Exception as e:
        menus.print_error(f"Error ejecutando Remotion: {e}")


def run_stage_4_coloring() -> None:
    """Stage 4: Coloring - Select session, video, apply color preset."""
    sessions = session_manager.list_sessions()

    if not sessions:
        menus.print_warning("No hay sesiones")
        return

    menus.console.print("\n[bold yellow]=== Stage 4: Coloración ===[/bold yellow]\n")
    menus.print_session_list(sessions)

    session_id = menus.prompt_session_id()
    if not session_id:
        return

    # List video files in session
    session_dir = Path(WORKSPACE_ROOT) / "data" / "recordings" / session_id
    exports_dir = Path(WORKSPACE_ROOT) / "output" / "exports" / session_id

    video_files = []
    for d in [session_dir, exports_dir]:
        if d.exists():
            video_files.extend(list(d.glob("*.mp4")))
            video_files.extend(list(d.glob("*.mkv")))

    if not video_files:
        menus.print_warning("No hay videos en esta sesión")
        return

    # Show video files
    menus.console.print("\n[bold]Videos disponibles:[/bold]")
    for i, v in enumerate(video_files, 1):
        size = v.stat().st_size / 1024 / 1024
        menus.console.print(f"  {i}. [cyan]{v.name}[/cyan] ({size:.1f} MB)")

    choice = menus.Prompt.ask(
        "\n[bold]Selecciona video (0 para cancelar)[/bold]",
        choices=["0"] + [str(i) for i in range(1, len(video_files) + 1)],
        default="1",
    )

    if choice == "0":
        return

    selected_video = video_files[int(choice) - 1]

    # Select color preset
    pm = get_preset_manager(WORKSPACE_ROOT)
    color_preset = pm.get_default_color_preset()

    subpresets = color_preset.get("presets", {})
    scales = color_preset.get("scales", {})

    menus.console.print("\n[bold]Presets de color (base):[/bold]")
    for i, (name, data) in enumerate(subpresets.items(), 1):
        menus.console.print(f"  {i}. [cyan]{data['name']}[/cyan] - {data['description']}")

    preset_choice = menus.Prompt.ask(
        "\n[bold]Selecciona preset de color[/bold]",
        choices=["1", "2", "3"],
        default="1",
    )

    subpreset_names = list(subpresets.keys())
    selected_subpreset = subpreset_names[int(preset_choice) - 1]

    # Select scale
    menus.console.print("\n[bold]Escala de color:[/bold]")
    menus.console.print("  0. [cyan]Sin escala[/cyan]")
    for i, (name, data) in enumerate(scales.items(), 1):
        menus.console.print(f"  {i}. {name} (temp: {data.get('temperature', 0)})")

    scale_choice = menus.Prompt.ask(
        "\n[bold]Selecciona escala (0 para ninguna)[/bold]",
        choices=["0"] + [str(i) for i in range(1, len(scales) + 1)],
        default="0",
    )

    selected_scale = None
    if scale_choice != "0":
        scale_names = list(scales.keys())
        selected_scale = scale_names[int(scale_choice) - 1]

    menus.console.print(f"\n[bold cyan]Aplicando color: {selected_subpreset}[/bold cyan]")
    if selected_scale:
        menus.print_info(f"Escala: {selected_scale}")

    # Run color grading via FFmpeg
    from scripts.utils import ffmpeg

    output_dir = Path(WORKSPACE_ROOT) / "output" / "exports" / session_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"colored_{selected_video.stem}.mp4"
    output_path = output_dir / output_filename

    try:
        # Simple color grading - adjust brightness/contrast/saturation
        ffmpeg.adjust_video_colors(
            str(selected_video.absolute()),
            str(output_path),
            brightness=0.02,
            contrast=1.05,
            saturation=1.1,
            temperature=15
            if selected_subpreset == "warm"
            else (-15 if selected_subpreset == "cold" else 0),
        )
        menus.print_success(f"Video coloreado: {output_path.name}")
    except Exception as e:
        menus.print_error(f"Error aplicando color: {e}")


def run_presets_menu() -> None:
    """Presets management menu."""
    pm = get_preset_manager(WORKSPACE_ROOT)

    while True:
        menus.console.print("\n[bold cyan]=== Gestión de Presets ===[/bold cyan]\n")

        menus.console.print("  1. [cyan]Ver presets de Subtítulos[/cyan]")
        menus.console.print("  2. [cyan]Ver presets de Audio[/cyan]")
        menus.console.print("  3. [cyan]Ver presets de Color[/cyan]")
        menus.console.print("  4. [cyan]Crear preset[/cyan]")
        menus.console.print("  5. [cyan]Editar preset[/cyan]")
        menus.console.print("  6. [cyan]Eliminar preset[/cyan]")
        menus.console.print("  0. [dim]Volver[/dim]")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona opción[/bold]",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="0",
        )

        if choice == "0":
            break
        elif choice == "1":
            # List subtitle presets
            presets = pm.list_subtitle_presets()
            menus.console.print("\n[bold]Presets de Subtítulos:[/bold]")
            for p in presets:
                marker = (
                    " [default]" if p["is_default"] else " [readonly]" if p["read_only"] else ""
                )
                menus.console.print(f"  • {p['display_name']}{marker}")
                menus.console.print(f"    [dim]{p['description']}[/dim]")
        elif choice == "2":
            # List audio presets
            presets = pm.list_audio_presets()
            menus.console.print("\n[bold]Presets de Audio:[/bold]")
            for p in presets:
                marker = (
                    " [default]" if p["is_default"] else " [readonly]" if p["read_only"] else ""
                )
                menus.console.print(f"  • {p['display_name']}{marker}")
                menus.console.print(f"    [dim]{p['description']}[/dim]")
        elif choice == "3":
            # List color presets
            presets = pm.list_color_presets()
            menus.console.print("\n[bold]Presets de Color:[/bold]")
            for p in presets:
                marker = (
                    " [default]" if p["is_default"] else " [readonly]" if p["read_only"] else ""
                )
                menus.console.print(f"  • {p['display_name']}{marker}")
                menus.console.print(f"    [dim]{p['description']}[/dim]")
        elif choice == "4":
            # Create preset
            menus.console.print("\n[bold]Crear nuevo preset:[/bold]")
            menus.console.print("  1. [cyan]Subtítulo[/cyan]")
            menus.console.print("  2. [cyan]Audio[/cyan]")
            menus.console.print("  3. [cyan]Color[/cyan]")

            ptype = menus.Prompt.ask(
                "\n[bold]Tipo de preset[/bold]",
                choices=["1", "2", "3"],
            )

            ptype_map = {"1": "subtitle", "2": "audio", "3": "color"}
            preset_type = ptype_map[ptype]

            name = menus.Prompt.ask("Nombre del preset")
            description = menus.Prompt.ask("Descripción")

            # For now, clone from default
            if preset_type == "subtitle":
                default = pm.get_default_subtitle_preset()
                default["name"] = name
                default["description"] = description
                default.pop("read_only", None)
                default.pop("is_default", None)
                success = pm.create_subtitle_preset(name, default)
            elif preset_type == "audio":
                default = pm.get_default_audio_preset()
                default["name"] = name
                default["description"] = description
                default.pop("read_only", None)
                default.pop("is_default", None)
                success = pm.create_audio_preset(name, default)
            else:
                default = pm.get_default_color_preset()
                default["name"] = name
                default["description"] = description
                default.pop("read_only", None)
                default.pop("is_default", None)
                success = pm.create_color_preset(name, default)

            if success:
                menus.print_success(f"Preset '{name}' creado")
            else:
                menus.print_error("Error creando preset")

        elif choice == "5":
            # Edit preset
            menus.console.print("\n[bold]Editar preset (no editable el default):[/bold]")
            menus.print_warning("Función no implementada aún")

        elif choice == "6":
            # Delete preset
            menus.console.print("\n[bold]Eliminar preset (no puede ser default):[/bold]")
            menus.print_warning("Función no implementada aún")


# ============================================================================
# MAIN
# ============================================================================


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
                run_stage_1_audio()
            elif choice == "5":
                menus.clear_screen()
                run_stage_3_subtitles()
            elif choice == "6":
                menus.clear_screen()
                run_stage_4_coloring()
            elif choice == "7":
                menus.clear_screen()
                run_presets_menu()
            elif choice == "8":
                menus.clear_screen()
                run_settings()
            elif choice == "9":
                menus.clear_screen()
                run_audio_preview_select()

            if choice != "0":
                menus.Prompt.ask("\n[dim]Presiona Enter para continuar...[/dim]", default="")

        except KeyboardInterrupt:
            menus.console.print("\n\n[bold yellow]Ctrl+C detectado. Saliendo...[/bold yellow]\n")
            break
        except EOFError:
            menus.console.print("\n\n[bold yellow]Entrada cerrada. Saliendo...[/bold yellow]\n")
            break


if __name__ == "__main__":
    main()
