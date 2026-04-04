#!/usr/bin/env node

/**
 * Convert pipeline transcript to Remotion caption format
 */

const fs = require('fs');

// Load pipeline transcript
const transcript = JSON.parse(fs.readFileSync('/home/carlos/side-projects/mvp-editing-pipeline/transcripts/study/segments.json'));

// Convert to Remotion Caption format (word-level timestamps)
const captions = [];

for (const segment of transcript) {
  const words = segment.words || [];
  
  for (const word of words) {
    captions.push({
      text: word.word.trim(),
      startMs: Math.round(word.start * 1000),
      endMs: Math.round(word.end * 1000),
      timestampMs: Math.round((word.start + word.end) / 2 * 1000),
      confidence: word.probability || 0.9
    });
  }
}

// Sort by start time
captions.sort((a, b) => a.startMs - b.startMs);

console.log('Converted', captions.length, 'word-level captions');
console.log('First word:', captions[0].text, 'at', captions[0].startMs, 'ms');
console.log('Last word:', captions[captions.length - 1].text, 'at', captions[captions.length - 1].startMs, 'ms');

// Save
fs.writeFileSync('/home/carlos/side-projects/mvp-editing-pipeline/remotion/test_captions.json', JSON.stringify(captions, null, 2));
console.log('Saved to test_captions.json');