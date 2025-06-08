# Virtual Environment Management in Neuravox

## The Challenge

When you install a Python application, the virtual environment (venv) question is: "Do I need to activate the venv every time I want to run the app?"

## Solutions

### 1. **pipx** - Best for End Users
```bash
pipx install neuravox
```

**How it works:**
- pipx creates an isolated venv automatically
- Installs the app in `~/.local/pipx/venvs/neuravox/`
- Creates a wrapper script in `~/.local/bin/neuravox`
- The wrapper automatically uses the correct Python from the venv

**Result:** Just type `neuravox` - no activation needed!

### 2. **System Installation Script** - Best for Self-Contained Apps
```bash
./scripts/install-system.sh
```

**How it works:**
- Copies entire project to `~/.neuravox/`
- Creates a venv inside: `~/.neuravox/venv/`
- Installs a wrapper script to `~/.local/bin/neuravox`:
  ```bash
  #!/usr/bin/env bash
  exec "$HOME/.neuravox/venv/bin/python" -m cli.main "$@"
  ```

**Result:** The wrapper handles venv activation transparently!

### 3. **Poetry/PDM** - Modern Package Managers
```bash
poetry install
poetry run neuravox
```

**How it works:**
- Poetry manages the venv location
- `poetry run` automatically activates the venv
- Can install global scripts with `poetry install --with-pip-args="--editable"`

### 4. **Development Mode** - For Active Development
```bash
source .venv/bin/activate
neuravox
```

**When to use:**
- During development
- When you need to run other commands in the same venv
- When debugging

## How Neuravox Handles This

Neuravox supports multiple installation methods:

1. **For users who just want it to work:**
   ```bash
   pipx install neuravox
   neuravox process audio.mp3
   ```

2. **For users who want control:**
   ```bash
   ./scripts/install-system.sh
   neuravox process audio.mp3
   ```

3. **For developers:**
   ```bash
   uv venv && source .venv/bin/activate
   uv pip install -e .
   neuravox process audio.mp3
   ```

## Behind the Scenes

When you run `neuravox`, here's what happens:

### With pipx:
1. Shell finds `neuravox` in PATH (`~/.local/bin/neuravox`)
2. This is a script that pipx created
3. Script activates the venv and runs the real neuravox
4. You never see the venv activation

### With our install script:
1. Shell finds `neuravox` in PATH (`~/.local/bin/neuravox`)
2. This wrapper script directly calls the venv's Python
3. Python runs with all dependencies available
4. No explicit activation needed

### With manual venv:
1. You must activate the venv first
2. This modifies PATH to prioritize venv binaries
3. `neuravox` command is found in venv
4. Runs with correct Python and dependencies

## Best Practices

1. **For distribution:** Use pipx or create wrapper scripts
2. **For development:** Use explicit venv activation
3. **For servers:** Use systemd services with full paths
4. **For containers:** Install globally (container IS the isolation)

## Example Wrapper Script

Here's what a production wrapper looks like:

```bash
#!/usr/bin/env bash
# /usr/local/bin/neuravox

# Find where neuravox is installed
if [ -d "$HOME/.neuravox/venv" ]; then
    PYTHON="$HOME/.neuravox/venv/bin/python"
elif [ -d "/opt/neuravox/venv" ]; then
    PYTHON="/opt/neuravox/venv/bin/python"
else
    echo "Error: Neuravox not found. Please run install script."
    exit 1
fi

# Run with the correct Python
exec "$PYTHON" -m cli.main "$@"
```

This wrapper:
- Finds the installation
- Uses the venv's Python directly
- Passes all arguments through
- No activation needed!