# Neuravox - Manual Pages

This directory contains manual (man) pages for the neuravox platform commands.

## Available Man Pages

- `neuravox.1` - Main command overview
- `neuravox-init.1` - Workspace initialization
- `neuravox-process.1` - Audio processing pipeline
- `neuravox-status.1` - Status and statistics
- `neuravox-config.1` - Configuration management

## Installation

### System-wide Installation (requires sudo)

```bash
sudo cp *.1 /usr/local/share/man/man1/
sudo mandb  # Update man database
```

### User Installation (no sudo required)

```bash
mkdir -p ~/.local/share/man/man1
cp *.1 ~/.local/share/man/man1/
mandb -u  # Update user man database

# Add to your shell profile if not already there:
export MANPATH="$HOME/.local/share/man:$MANPATH"
```

### Using Without Installation

You can read the man pages directly without installing:

```bash
man ./neuravox.1
man ./neuravox-process.1
# etc.
```

## Viewing Man Pages

After installation, you can view the documentation using:

```bash
man neuravox
man neuravox-process
man neuravox-init
man neuravox-status
man neuravox-config
```

## Building from Source

The man pages are written in troff format. To convert to other formats:

```bash
# Convert to PDF
groff -man -Tpdf neuravox.1 > neuravox.pdf

# Convert to HTML
groff -man -Thtml neuravox.1 > neuravox.html

# Convert to plain text
groff -man -Tutf8 neuravox.1 | col -b > neuravox.txt
```

## Quick Reference

For quick help without man pages:

```bash
neuravox --help
neuravox process --help
neuravox init --help
# etc.
```