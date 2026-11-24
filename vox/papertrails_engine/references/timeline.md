# Timeline v1

The pipeline's `timeline.json` is the single source of timing for visuals, subtitles, and voice duration. Required root fields:

| Field | Meaning |
|---|---|
| version | `1` |
| width, height | even pixel dimensions; default 1920×1080 or 1080×1920 |
| fps | positive integer, normally 30 |
| seed | fixed integer; same seed/timing/environment should repeat |
| duration | measured source voice seconds, positive finite number |
| audio | local file path, normally absolute to project/media/voice.ext |
| captions | ordered `{start, end, text, words?}` in seconds; `words` = measured `{word, start, end}` for the karaoke highlight |
| scenes | contiguous ordered shot list covering 0..duration, with no gap/overlap |

A shot:

```json
{
  "id": "shot-001",
  "start": 0,
  "end": 3,
  "narration": "Saving money takes patience.",
  "title": "Save for tomorrow",
  "biome": "heartland",
  "night": false,
  "action": "reveal",
  "prop": "coin",
  "camera": "wide",
  "color": "#d79a45",
  "visual": "Intent note: build a coin stack as the sentence is spoken."
}
```

## Supported controls

- `biome`: `heartland`, `desert`, `snow`, `blossom`, `pinewood`.
- `night`: boolean.
- `action`: `walk`, `idle`, `reveal`, `celebrate`, `grow` (tile props grow piece by piece; other props scale up).
  `reveal` on a tile prop (village, forest, house…) also grows it piece by piece instead of flipping the whole tile.
- `prop`: `none`, `village`, `forest`, `bridge`, `mountain`, `sun`, `moon`, `house`, `tree`, `book`, `coin`, `chart`, `factory`, `clock`, `people`, `water`, `globe`, `voice-note`, `edit-board`, `pop-up`, `film`, `bubble`, `mic`.
  `voice-note`, `bubble` and `mic` follow the measured loudness of the ORIGINAL voice (computed by the renderer), not a decorative loop.
- `camera`: `wide`, `close`, `orbit`, `top`, `push` (slow dolly in), `low` (hero angle from the page), `crane` (rises to reveal the set).
  Consecutive shots in the same biome automatically view the set from a different side.
- `color`: six-digit RGB hex string.
- `title`: short on-screen phrase, ideally ≤6 words; captions already carry the full narration.
- `visual`: director's note only. The renderer does NOT interpret natural language or generate new geometry from this field. Implement a missing prop in the video module and add its accepted name/validation before using it.

Read `scripts/render.mjs --help` and the video modules for exact renderer options. The original `engine/index.html` remains the game in the full package; the lite package ships only the video entry (`engine/video.html`).

## Transcription inputs

`prepare --transcript` accepts a Whisper-style JSON object with `segments`, or a segment array:

```json
{
  "segments": [
    {
      "start": 0.2,
      "end": 2.8,
      "text": "Tiết kiệm cho ngày mai.",
      "words": [
        {"word": "Tiết", "start": 0.2, "end": 0.5},
        {"word": "kiệm", "start": 0.5, "end": 0.9},
        {"word": "cho", "start": 0.9, "end": 1.1},
        {"word": "ngày", "start": 1.1, "end": 1.5},
        {"word": "mai.", "start": 1.5, "end": 2.8}
      ]
    }
  ]
}
```

`words` is optional. Valid SRT is also accepted. Timestamps must be finite, ordered, and inside measured audio duration (tiny ASR rounding tolerance only). A supplied transcript is the user's timing assertion; the script cannot prove it was transcribed from that specific recording.

`timing.mode=word` means word timestamps were supplied/recognized; `segment` means measured sentence/segment timings only. Neither means human-perfect forced alignment. Never fabricate word timestamps from text length and label them measured.

## Planning metadata

`direction.status` starts as `starter-needs-agent-review`. The calling agent must read the entire narration, refine scene meaning and set `agent-reviewed` only after actual scene review. Extra metadata is permitted and not rendered. `source.audioSha256` identifies the copied voice; keep it when revising shots.

Money/clock/chart icons are symbolic. There is no numeric-data schema for chart props; if a factual chart is required, add explicit sourced data and an accurate scale instead of treating decorative bars as quantitative evidence.

## On-screen text and cuts

- The scene `title` appears as a pinned paper tag in the upper safe area; it pops in at each cut.
- The active caption is a cream torn-paper strip with ink text (no dark bar). When the caption carries `words`
  and the word count matches its text, the word being spoken is inked red, earlier words stay ink, later words are faded.
  If you edit a caption's text (e.g. to fix an ASR spelling), edit the matching `words[i].word` too, keeping the same count.
- Every cut gets a 0.36 s paper page-wipe.
- `node scripts/render.mjs … --sfx` adds a soft synthesized paper flip at each cut, mixed under the untouched voice. Off by default.

## Optional paper cards

A shot may carry `card`, a paper overlay drawn above the 3D set (below the caption):

```json
"card": {"kind": "note", "head": "Bước 1 · Cài plugin", "lines": ["`python scripts/install.py`", "Xem trước rồi mới cài"],
         "side": "right", "lineAt": [0.4, 2.1]}
```

- `kind`: `note` (taped note; `head` + up to 12 `lines`, numbered dots unless `"numbered": false`; text in backticks renders as code)
  or `photo` (pinned print of an embedded image).
- `side`: `left`, `right` (default) or `center` (wider). `"big": true` on a centered note makes a chapter card.
- `lineAt`: seconds from the shot start at which each line writes in; without it lines appear in a gentle stagger.
- `photo` needs `img` as an embedded `data:image/(jpeg|png|webp);base64,…` URI (no external URLs), `aspect` (height/width),
  optional `hl` `[x, y, w, h]` in 0..1 image units for a hand-drawn marker ellipse (drawn at `hlAt` s), optional `badge`
  (stamp text, `\n` for a line break, shown at `badgeAt` s) and `caption`.
- Keep the 3D prop visible: put a side card opposite the prop, and use cards for facts the voice states, never invented numbers.
