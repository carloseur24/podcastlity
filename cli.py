#!/usr/bin/env python3
"""
Content-OS CLI
Menu-driven video content pipeline
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import ConfigProvider, reset_config
from scripts.preset_manager import get_preset_manager
from scripts.ui import menus
from scripts.utils import filepicker
from scripts.utils.session import SessionManager, ensure_session_dirs, load_settings

WORKSPACE_ROOT = str(PROJECT_ROOT)
settings = load_settings(WORKSPACE_ROOT)
session_manager = SessionManager(WORKSPACE_ROOT)


def run_new_session() -> None:
    menus.console.print("\n[bold cyan]=== Nueva Sesion ===[/bold cyan]\n")

    # Step 1: Session ID
    today = datetime.now().strftime("%Y%m%d")
    default_id = today  # e.g., "20260328"
    session_id = menus.prompt_session_id(default_id)
    if not session_id:
        menus.print_error("ID de sesion requerido")
        return

    # Step 2: Video file (single input)
    menus.console.print("\n[bold cyan]=== Seleccionar archivo de video ===[/bold cyan]")
    video_path = run_file_picker("video")
    if not video_path:
        menus.print_error("Archivo de video requerido")
        return

    # Create session
    ensure_session_dirs(WORKSPACE_ROOT, session_id)
    session = session_manager.create_session(
        session_id=session_id,
        topic="",  # No longer used
        duration=0,  # No longer used
    )
    session.video_file = video_path
    session_manager.save_session(session)

    menus.print_success(f"Sesion '{session_id}' creada")
    menus.print_info(f"Video: {video_path}")


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
        menus.console.print(f"Video: {session.video_file or 'N/A'}")
        menus.console.print()
        menus.console.print("  1. [green]Procesar Audio[/green]")
        menus.console.print("  2. [cyan]Agregar Subtítulos[/cyan]")
        menus.console.print("  3. [magenta]Coloración (Opcional)[/magenta]")
        menus.console.print("  4. [yellow]Ver resultados[/yellow]")
        menus.console.print("  0. [dim]Volver al menu principal[/dim]")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona[/bold]",
            choices=["0", "1", "2", "3", "4"],
            default="",
        )

        if choice == "0":
            break
        elif choice == "1":
            run_audio_processing_menu(session_id)
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()
        elif choice == "2":
            run_stage_3_subtitles()
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()
        elif choice == "3":
            run_stage_4_coloring()
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()
        elif choice == "4":
            view_results(session_id)
            menus.Prompt.ask("\n[dim]Presiona Enter para volver...[/dim]", default="")
            menus.clear_screen()


def edit_filter_parameters(session_id: str, audio_config: dict) -> None:
    """Edit parameters for a specific filter."""
    from scripts.config import ConfigProvider
    from scripts.ui import menus

    config = ConfigProvider(WORKSPACE_ROOT)

    # Map filter keys to display names and parameter definitions
    filter_info = {
        "highpass": {
            "name": "Highpass",
            "params": [
                ("frequency", "Frecuencia (Hz)", 60, 200, 80),
                ("poles", "Polos (1-2)", 1, 2, 2),
            ],
        },
        "eq_boxiness": {
            "name": "EQ Boxiness",
            "params": [
                ("frequency", "Frecuencia (Hz)", 300, 600, 450),
                ("gain", "Ganancia (dB)", -12, 0, -3),
                ("width", "Ancho de banda (Hz)", 100, 500, 300),
            ],
        },
        "compressor": {
            "name": "Compressor",
            "params": [
                ("threshold", "Umbral (dB)", -60, 0, -24),
                ("ratio", "Ratio (1:1 a 20:1)", 1, 20, 3.5),
                ("attack", "Attack (ms)", 0, 50, 5),
                ("release", "Release (ms)", 10, 500, 100),
                ("makeup", "Makeup (dB)", 0, 20, 4),
                ("knee", "Knee (dB)", 0, 10, 1),
            ],
        },
        "highshelf": {
            "name": "High Shelf",
            "params": [
                ("frequency", "Frecuencia (Hz)", 5000, 15000, 10000),
                ("gain", "Ganancia (dB)", -12, 12, 3),
            ],
        },
        "limiter": {
            "name": "Limiter",
            "params": [
                ("ceiling", "Ceiling (dB)", -12, 0, -1),
            ],
        },
        "loudnorm": {
            "name": "Loudnorm",
            "params": [
                ("I", "Target I (LUFS)", -24, -9, -16),
                ("TP", "True Peak (dB)", -6, 0, -1.5),
                ("LRA", "LRA (LU)", 1, 20, 11),
            ],
        },
    }

    while True:
        menus.console.print("\n[bold cyan]=== Editar Parámetros ===[/bold cyan]\n")

        # Show filter list
        for i, (key, info) in enumerate(filter_info.items(), 1):
            filter_data = audio_config.get(key, {})
            enabled = filter_data.get("enabled", False)
            status = "[✓]" if enabled else "[✗]"
            menus.console.print(f"  {i}. {status} {info['name']}")

        menus.console.print("  0. Volver")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona filtro[/bold]",
            choices=["0"] + [str(i) for i in range(1, len(filter_info) + 1)],
            default="",
        )

        if choice == "0":
            break

        # Get selected filter
        filter_key = list(filter_info.keys())[int(choice) - 1]
        filter_data = audio_config.get(filter_key, {})
        info = filter_info[filter_key]

        # Check if filter is enabled
        if not filter_data.get("enabled", False):
            menus.print_warning(
                f"{info['name']} está deshabilitado. Habilítalo primero para editar parámetros."
            )
            continue

        # Edit parameters for selected filter
        while True:
            menus.console.print(f"\n[bold]Editar: {info['name']}[/bold]\n")

            # Show current parameters
            for j, (param_key, param_label, min_val, max_val, default) in enumerate(
                info["params"], 1
            ):
                current = filter_data.get(param_key, default)
                menus.console.print(f"  {j}. {param_label}: {current}")

            menus.console.print("  0. Listo")

            param_choice = menus.Prompt.ask(
                "\n[bold]Selecciona parámetro[/bold]",
                choices=["0"] + [str(j) for j in range(1, len(info["params"]) + 1)],
                default="",
            )

            if param_choice == "0":
                break

            # Get selected parameter
            param_key, param_label, min_val, max_val, default = info["params"][
                int(param_choice) - 1
            ]
            current = filter_data.get(param_key, default)

            # Ask for new value
            menus.console.print(f"\n[dim]Valor actual: {current}[/dim]")
            new_value = menus.Prompt.ask(
                f"[bold]Nuevo valor para {param_label}[/bold]",
                default=str(current),
            )

            # Validate and convert
            try:
                if param_key == "ratio":
                    new_val = float(new_value)
                    if new_val < min_val or new_val > max_val:
                        menus.print_error(f"Valor debe estar entre {min_val} y {max_val}")
                        continue
                elif param_key in ["frequency", "poles", "attack", "release", "width"]:
                    new_val = int(new_value)
                    if new_val < min_val or new_val > max_val:
                        menus.print_error(f"Valor debe estar entre {min_val} and {max_val}")
                        continue
                else:
                    new_val = float(new_value)
                    if new_val < min_val or new_val > max_val:
                        menus.print_error(f"Valor debe estar entre {min_val} y {max_val}")
                        continue

                # Update parameter
                audio_config[filter_key] = audio_config.get(filter_key, {})
                audio_config[filter_key][param_key] = new_val
                config.save_session_audio_config(WORKSPACE_ROOT, session_id, audio_config)
                menus.print_success(f"{param_label} actualizado a {new_val}")

            except ValueError:
                menus.print_error("Valor inválido. Ingresa un número.")


def run_audio_processing_menu(session_id: str) -> None:
    """Show audio processing menu with toggles and edit options."""
    from scripts.config import ConfigProvider

    config = ConfigProvider(WORKSPACE_ROOT)
    audio_config = config.get_session_audio_config(WORKSPACE_ROOT, session_id)

    while True:
        menus.console.print(f"\n[bold cyan]=== Procesar Audio: {session_id} ===[/bold cyan]\n")

        # Display current configuration
        menus.console.print("[bold]Configuración actual:[/bold]\n")

        filter_names = {
            "highpass": "Highpass",
            "eq_boxiness": "EQ Boxiness",
            "compressor": "Compressor",
            "highshelf": "High Shelf",
            "limiter": "Limiter",
            "loudnorm": "Loudnorm",
        }

        for filter_key, filter_name in filter_names.items():
            filter_data = audio_config.get(filter_key, {})
            enabled = filter_data.get("enabled", False)
            status = "[✓]" if enabled else "[✗]"
            desc = filter_data.get("description", "")

            # Show key parameters
            params = []
            if filter_key == "highpass":
                params.append(f"{filter_data.get('frequency', 80)}Hz")
                params.append(f"{filter_data.get('poles', 2)} poles")
            elif filter_key == "eq_boxiness":
                params.append(f"{filter_data.get('frequency', 450)}Hz")
                params.append(f"{filter_data.get('gain', -3)}dB")
            elif filter_key == "compressor":
                params.append(f"{filter_data.get('threshold', -24)}dB")
                params.append(f"{filter_data.get('ratio', 3.5)}:1")
            elif filter_key == "highshelf":
                params.append(f"{filter_data.get('frequency', 10000)}Hz")
                params.append(f"{filter_data.get('gain', 3)}dB")
            elif filter_key == "limiter":
                params.append(f"{filter_data.get('ceiling', -1)}dB")
            elif filter_key == "loudnorm":
                params.append(f"{filter_data.get('I', -16)} LUFS")
                params.append(f"{filter_data.get('TP', -1.5)}dB TP")

            param_str = " | ".join(params) if params else ""
            menus.console.print(f"  {status} [bold]{filter_name}[/bold] {param_str} - {desc}")

        menus.console.print()
        menus.console.print("  1. Toggle Highpass")
        menus.console.print("  2. Toggle EQ Boxiness")
        menus.console.print("  3. Toggle Compressor")
        menus.console.print("  4. Toggle High Shelf")
        menus.console.print("  5. Toggle Limiter")
        menus.console.print("  6. Toggle Loudnorm")
        menus.console.print("  7. Editar parámetros")
        menus.console.print("  8. Restaurar defaults")
        menus.console.print("  9. [green]Procesar audio[/green]")
        menus.console.print("  0. Volver")

        choice = menus.Prompt.ask(
            "\n[bold]Selecciona[/bold]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="",
        )

        if choice == "0":
            break
        elif choice in ["1", "2", "3", "4", "5", "6"]:
            filter_keys = [
                "highpass",
                "eq_boxiness",
                "compressor",
                "highshelf",
                "limiter",
                "loudnorm",
            ]
            filter_key = filter_keys[int(choice) - 1]
            current_enabled = audio_config.get(filter_key, {}).get("enabled", False)
            audio_config[filter_key] = audio_config.get(filter_key, {})
            audio_config[filter_key]["enabled"] = not current_enabled
            config.save_session_audio_config(WORKSPACE_ROOT, session_id, audio_config)
            menus.print_success(
                f"{filter_key} {'habilitado' if not current_enabled else 'deshabilitado'}"
            )
        elif choice == "7":
            # Edit parameters
            edit_filter_parameters(session_id, audio_config)
            # Reload config after editing
            audio_config = config.get_session_audio_config(WORKSPACE_ROOT, session_id)
        elif choice == "8":
            # Restore defaults
            default_config = config.get_audio_processing_config()
            config.save_session_audio_config(WORKSPACE_ROOT, session_id, default_config)
            audio_config = default_config
            menus.print_success("Configuración restaurada a defaults")
        elif choice == "9":
            # Run voice extract stage
            menus.console.print("\n[bold]Ejecutando procesamiento de audio...[/bold]")
            from scripts.core.stages import voice_extract

            try:
                result = voice_extract.run(session_id, WORKSPACE_ROOT)
                menus.print_success(
                    f"Audio procesado: {result.get('voice_duration', 0):.1f}s de voz"
                )
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


# ============================================================================
# STAGE FUNCTIONS - Subtitles, Coloring
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
        # Stage 1: Audio processing - Proxies + VoiceExtract
        from scripts.core.stages import proxies, voice_extract

        menus.console.print("\n[bold]1/2: Extrayendo audio...[/bold]")
        proxies.run(session_id, WORKSPACE_ROOT)

        menus.console.print("[bold]2/2: Reduciendo ruido y normalizando...[/bold]")
        voice_extract.run(session_id, WORKSPACE_ROOT)

        menus.print_success("Audio procesado correctamente")
        menus.print_info("Listo para edición manual. Luego usa Stage 3 para subtítulos.")
    except Exception as e:
        menus.print_error(f"Error procesando audio: {e}")


def run_stage_3_subtitles() -> None:
    """Add subtitles to any video file - select video, transcribe, render with Remotion."""

    # Step 1: Select video file using file picker
    video_path = run_file_picker("video")
    if not video_path:
        menus.print_error("Archivo de video requerido")
        return

    # Step 2: Always extract audio from the source video (disconnected from audio processing stage)
    video_path_obj = Path(video_path)
    video_stem = video_path_obj.stem

    menus.console.print("\n[bold]Extrayendo audio del video seleccionado...[/bold]")
    # Extract audio using ffmpeg - use temp directory
    temp_audio = Path(WORKSPACE_ROOT) / "output" / "temp" / f"{video_stem}_audio.wav"
    temp_audio.parent.mkdir(parents=True, exist_ok=True)

    import subprocess

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path_obj.absolute()),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(temp_audio),
    ]

    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            audio_path = temp_audio
            menus.print_success("Audio extraído")
        else:
            menus.print_error(f"Error extrayendo audio: {result.stderr}")
            return
    except Exception as e:
        menus.print_error(f"Error extrayendo audio: {e}")
        return

    # Verify we have a valid audio file to transcribe
    if audio_path is None or not audio_path.exists():
        menus.print_error("No se pudo obtener audio para transcribir")
        return

    # Step 4: Transcribe with Whisper (direct import)
    transcript_file = (
        Path(WORKSPACE_ROOT) / "output" / "transcripts" / "temp" / f"{video_stem}_segments.json"
    )
    transcript_file.parent.mkdir(parents=True, exist_ok=True)

    # Always regenerate if user doesn't want to reuse
    do_transcribe = True
    if transcript_file.exists():
        menus.print_info(f"Transcripción existente encontrada: {transcript_file.name}")
        reuse = menus.Confirm.ask(
            "\n[bold]¿Reusar transcripción existente?[/bold] (s/n)", default=True
        )
        do_transcribe = not reuse

    if do_transcribe:
        menus.console.print("\n[bold]Transcribiendo audio con Whisper...[/bold]")
        try:
            from faster_whisper import WhisperModel

            # Use int8 for CPU, or cuda if available
            model = WhisperModel("large-v2", device="cpu", compute_type="int8")

            segments, info = model.transcribe(
                str(audio_path),
                language="es",
                word_timestamps=True,
            )

            # Collect all segments
            all_segments = []
            for seg in segments:
                all_segments.append(
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text.strip(),
                    }
                )

            # Save segments
            with open(transcript_file, "w") as f:
                json.dump(all_segments, f, indent=2)

            menus.print_success(f"Transcripción creada: {transcript_file.name}")
        except Exception as e:
            menus.print_error(f"Error transcribiendo: {e}")
            return

    # Step 5: Select subtitle preset
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

    # Step 6: Ask for time range (optional)
    use_range = menus.Confirm.ask("\n[bold]¿Usar rango de tiempo?[/bold] (s/n)", default=False)

    start_sec = None
    end_sec = None
    if use_range:
        start_sec_str = menus.Prompt.ask("Segundo inicial", default="0")
        end_sec_str = menus.Prompt.ask("Segundo final", default="")
        start_sec = int(start_sec_str)
        if end_sec_str.strip():
            end_sec = int(end_sec_str)

    # Step 7: Ask for resolution
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

    # Step 8: Run Remotion
    import subprocess

    remotion_dir = Path(WORKSPACE_ROOT) / "remotion"
    video_path_abs = video_path_obj.absolute()
    captions_path = transcript_file.absolute()
    preset_path = remotion_dir / "config" / "presets" / f"{preset_name}.json"

    if not preset_path.exists():
        preset_path = remotion_dir / "config" / "presets" / "test_preset.json"

    # Output to exports folder with video name
    output_dir = Path(WORKSPACE_ROOT) / "output" / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"subtitled_{video_stem}_{resolution}.mp4"
    output_path = output_dir / output_filename

    cmd = [
        "node",
        "cli.js",
        str(video_path_abs),
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
            menus.print_info(f"Output: {output_path}")
        else:
            menus.print_error(f"Error en renderizado: {result.stderr}")
    except subprocess.TimeoutExpired:
        menus.print_error("Tiempo de renderizado agotado")
    except Exception as e:
        menus.print_error(f"Error ejecutando Remotion: {e}")


def run_stage_4_coloring() -> None:
    """Stage 4: Coloring - Select any video, apply color preset."""

    # Step 1: Select video file using file picker
    video_path = run_file_picker("video")
    if not video_path:
        menus.print_error("Archivo de video requerido")
        return

    video_path_obj = Path(video_path)
    video_stem = video_path_obj.stem

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

    output_dir = Path(WORKSPACE_ROOT) / "output" / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"colored_{video_stem}.mp4"
    output_path = output_dir / output_filename

    try:
        ffmpeg.adjust_video_colors(
            str(video_path_obj.absolute()),
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
                run_settings()

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
