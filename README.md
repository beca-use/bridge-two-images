# Bridge Two Images

`bridge-two-images` is a Codex Skill that turns exactly two user-supplied still images into one unified editorial artwork. It automatically chooses anchors, a visible relationship, composition, treatment, and (when safe) a short caption.

It is intended for artistic image bridging, not ordinary collages, side-by-side comparisons, screenshot stitching, panoramas, or simple background replacement.

## Install

Copy this folder into your Codex skills directory:

```text
~/.codex/skills/bridge-two-images
```

On Windows, the equivalent default location is:

```text
%USERPROFILE%\\.codex\\skills\\bridge-two-images
```

Install the Python helper dependency:

```bash
python -m pip install -r requirements.txt
```

Use Python 3.10 or newer.

## Use

Provide exactly two distinct still raster images and invoke:

```text
Use $bridge-two-images to artistically bridge these two images into one unified editorial artwork.
```

The Skill returns one passing raster image and a short sentence describing the visible connection. It performs at most one diagnosed retry.

## Backend configuration

The Skill prefers the installed `codex-image2` Skill. If that route is configured, set:

```text
CODEX_API_URL=https://your-backend.example/v1
CODEX_API_KEY=your-key
```

On macOS or Linux, set these for the current shell with:

```bash
export CODEX_API_URL="https://your-backend.example/v1"
export CODEX_API_KEY="your-key"
```

On Windows PowerShell:

```powershell
$env:CODEX_API_URL = "https://your-backend.example/v1"
$env:CODEX_API_KEY = "your-key"
```

Never commit real keys, `.env` files, or private service URLs. Remote routes should use HTTPS. If `CODEX_API_URL` is absent, the Skill does not silently enable the default remote route unless the user explicitly named `codex-image2` in the request. The repository does not include credentials.

The `codex-image2` Skill is a separate Codex dependency; install and configure it according to its own instructions when using that backend. Without a compatible configured backend, the Skill follows its documented fallback routing rules.

## Validate and test

From this directory, validate the Skill and run all regression tests:

```bash
python path/to/quick_validate.py .
python -m unittest discover -s scripts -p "test_*.py"
```

The `quick_validate.py` path refers to the validator bundled with the Codex `skill-creator` Skill.

## Repository layout

```text
SKILL.md                 Skill instructions
agents/openai.yaml       UI metadata
references/              Detailed workflow references
scripts/                 Validators, helpers, and regression tests
requirements.txt         Python helper dependency
```

## License

MIT License. See [LICENSE](LICENSE).
