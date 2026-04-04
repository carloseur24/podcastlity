# Remotion Subtitle Renderer

Domain-based architecture for kinetic subtitle rendering.

## Architecture

```
remotion/
├── src/                    # Source code
│   ├── index.tsx           # Main entry point
│   ├── render.js           # CLI render script
│   └── components/          # React components
│
├── config/                 # Configuration
│   ├── presets/            # Subtitle presets
│   └── input-props.json
│
├── data/                   # Data inputs
│   └── captions/           # Caption data & utilities
│
├── assets/                 # Static assets
│   ├── fonts/              # Font files
│   ├── videos/             # Input videos (source)
│   └── templates/          # HTML templates
│
├── public/                 # Runtime assets (auto-copied)
│   ├── fonts/             # Fonts for staticFile
│   └── input_video.mp4     # Video for staticFile
│
├── output/                 # Render outputs
│   └── *.mp4              # Rendered videos
│
├── bin/                    # Executables
├── demos/                  # Demo files
├── build/                  # Bundled output
└── package.json
```

## Usage

```bash
# Render with 144p proxy (fast)
node src/render.js assets/videos/input_video.mp4 output/test.mp4 data/captions/test_captions.json config/presets/test_preset.json 30 57 1920 1080 --start 16 --end 22 --proxy --resolution 144p

# Render with 480p
node src/render.js assets/videos/input_video.mp4 output/test.mp4 data/captions/test_captions.json config/presets/test_preset.json 30 57 1920 1080 --start 16 --end 22 --proxy --resolution 480p

# Render with 1080p (full quality)
node src/render.js assets/videos/input_video.mp4 output/test.mp4 data/captions/test_captions.json config/presets/test_preset.json 30 57 1920 1080 --start 16 --end 22
```

## CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--start N` | Start second | `--start 16` |
| `--end N` | End second | `--end 22` |
| `--proxy` | Use proxy mode (faster) | `--proxy` |
| `--resolution Np` | Resolution (144p, 480p, 720p, 1080p) | `--resolution 480p` |
| `--scale N` | Scale factor (0.5 = half size) | `--scale 0.5` |

## Font Scaling

Font size now scales automatically based on resolution using percentage of viewport height:
- 144p (256x144): ~8px
- 480p (854x480): ~14px  
- 1080p (1920x1080): ~32px

This ensures subtitles are readable at all resolutions.

## Development

```bash
# Auto-bundle on first run (no separate build needed)
node src/render.js ...
```

The render script will automatically bundle the project if needed.

## Notes

- `public/` folder contains runtime files needed by staticFile() - do not delete
- Font is loaded via CSS from public/fonts/poppins.ttf
- Video is accessed via staticFile('input_video.mp4') from public/