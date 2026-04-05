#!/usr/bin/env node

console.log('Running CLI...');
const { renderVideo } = require('./src/render.js');
const fs = require('fs');
const path = require('path');

// CLI Colors
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m'
};

function log(color, ...args) {
  console.log(color, ...args, colors.reset);
}

// Resolution presets
const resolutions = {
  '144p': { width: 256, height: 144 },
  '240p': { width: 426, height: 240 },
  '360p': { width: 640, height: 360 },
  '480p': { width: 854, height: 480 },
  '720p': { width: 1280, height: 720 },
  '1080p': { width: 1920, height: 1080 },
  '1440p': { width: 2560, height: 1440 },
  '4k': { width: 3840, height: 2160 }
};

// Parse arguments
const args = process.argv.slice(2);
const options = {
  proxy: false,
  resolution: '480p',
  start: null,
  end: null,
  scale: null,
  output: null,
  input: null,
  captions: null,
  preset: null,
  help: false
};

// Parse flags
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  switch (arg) {
    case '--proxy':
    case '-p':
      options.proxy = true;
      break;
    case '--resolution':
    case '-r':
      options.resolution = args[++i] || '480p';
      break;
    case '--start':
    case '-s':
      options.start = parseInt(args[++i]);
      break;
    case '--end':
    case '-e':
      options.end = parseInt(args[++i]);
      break;
    case '--scale':
      options.scale = parseFloat(args[++i]);
      break;
    case '--output':
    case '-o':
      options.output = args[++i];
      break;
    case '--help':
    case '-h':
      options.help = true;
      break;
    default:
      // Positional args
      if (!options.input) options.input = arg;
      else if (!options.captions) options.captions = arg;
      else if (!options.preset) options.preset = arg;
  }
}

// Show help
if (options.help) {
  log(colors.cyan, `
${colors.bright}Remotion Subtitle Renderer CLI${colors.reset}

${colors.yellow}Usage:${colors.reset}
  node cli.js <input_video> <captions_json> <preset_json> [options]

${colors.yellow}Options:${colors.reset}
  -p, --proxy           Use proxy mode (faster encoding)
  -r, --resolution     Resolution: 144p, 240p, 360p, 480p, 720p, 1080p, 4k (default: 480p)
  -s, --start N        Start second (default: 0)
  -e, --end N          End second (default: video duration)
  -o, --output N       Output filename
  -h, --help           Show this help

${colors.yellow}Examples:${colors.reset}
  # Quick proxy render at 480p (seconds 10-20)
  node cli.js input.mp4 caps.json preset.json -p -s 10 -e 20

  # Full quality 1080p render
  node cli.js input.mp4 caps.json preset.json -r 1080p

  # 4K render with range
  node cli.js input.mp4 caps.json preset.json -r 4k -s 5 -e 15

  # Custom scale (0.5 = half size)
  node cli.js input.mp4 caps.json preset.json --scale 0.5
`);
  process.exit(0);
}

// Validate required args
if (!options.input || !options.captions || !options.preset) {
  log(colors.yellow, 'Missing required arguments!');
  log(colors.cyan, 'Use: node cli.js <input> <captions> <preset> [options]');
  log(colors.cyan, 'Or: node cli.js --help for usage info');
  process.exit(1);
}

// Resolve paths
const inputPath = path.resolve(options.input);
const captionsPath = path.resolve(options.captions);
const presetPath = path.resolve(options.preset);

// Default output filename
if (!options.output) {
  const res = options.resolution.replace('p', 'p_').replace('4k', '4k');
  const range = options.start ? `_${options.start}-${options.end}` : '';
  options.output = `output/render_${res}${range}.mp4`;
}

const outputPath = path.resolve(options.output);

// Get resolution dimensions
const res = resolutions[options.resolution] || resolutions['480p'];
const width = res.width;
const height = res.height;

// Build render options
const renderOptions = {
  proxy: options.proxy,
  start: options.start,
  end: options.end,
  resolution: options.resolution,
  scale: options.scale
};

// Banner
log(colors.cyan, `
╔═══════════════════════════════════════════════════╗
║   ${colors.bright}Remotion Subtitle Renderer CLI${colors.reset}                    ║
╚═══════════════════════════════════════════════════╝
`);

// Show config
log(colors.green, '┌─ Configuration ─────────────────────────────────────┐');
log(colors.green, '│ '), log(colors.yellow, 'Input:     '), log(colors.reset, options.input);
log(colors.green, '│ '), log(colors.yellow, 'Output:     '), log(colors.reset, options.output);
log(colors.green, '│ '), log(colors.yellow, 'Resolution: '), log(colors.reset, options.resolution, ` (${width}x${height})`);
log(colors.green, '│ '), log(colors.yellow, 'Range:      '), log(colors.reset, options.start || 0, 's →', options.end ? options.end + 's' : 'end');
log(colors.green, '│ '), log(colors.yellow, 'Proxy:      '), log(colors.reset, options.proxy ? 'Yes (faster)' : 'No (quality)');
if (options.scale) {
  log(colors.green, '│ '), log(colors.yellow, 'Scale:      '), log(colors.reset, options.scale);
}
log(colors.green, '└──────────────────────────────────────────────────┘');

// Run render
log(colors.cyan, '\n▶ Starting render...\n');

renderVideo(
  inputPath,
  outputPath,
  captionsPath,
  presetPath,
  30, // fps
  57, // default duration (will be calculated from range)
  width,
  height,
  renderOptions
).then(() => {
  log(colors.green, '\n✅ Render complete!');
  log(colors.cyan, `Output: ${outputPath}\n`);
}).catch((err) => {
  log(colors.yellow, '\n❌ Render failed:', err.message);
  process.exit(1);
});
