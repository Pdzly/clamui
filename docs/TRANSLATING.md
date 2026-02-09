# Translating ClamUI

This guide explains how to contribute a new language translation to ClamUI or update an existing one.

ClamUI uses [GNU gettext](https://www.gnu.org/software/gettext/) for internationalization. Translatable strings are extracted from the source code into a POT template (`po/clamui.pot`), and each language gets its own PO file (e.g., `po/de.po` for German).

## Prerequisites

Install the gettext tools:

```bash
# Ubuntu / Debian
sudo apt install gettext

# Fedora
sudo dnf install gettext

# Arch
sudo pacman -S gettext
```

## Adding a New Language

### Step 1: Initialize a PO file

From the project root, run `msginit` to create a PO file for your language:

```bash
msginit \
    --input=po/clamui.pot \
    --output-file=po/<LANG>.po \
    --locale=<LANG>
```

Replace `<LANG>` with the appropriate [language code](https://www.gnu.org/software/gettext/manual/html_node/Usual-Language-Codes.html) — for example `de` for German, `fr` for French, or `pt_BR` for Brazilian Portuguese.

`msginit` pre-fills the PO header (your name, email, plural forms) based on your locale settings. Review and correct the header if needed.

### Step 2: Register the language

Add your language code to `po/LINGUAS`, one code per line:

```
# po/LINGUAS
de
```

This tells the build system which languages to compile.

### Step 3: Translate strings

Open `po/<LANG>.po` in a PO editor or a text editor and translate each `msgstr` entry.

**Recommended PO editors:**

| Editor | Platform | Notes |
|--------|----------|-------|
| [Poedit](https://poedit.net/) | Linux, macOS, Windows | GUI, free version available |
| [Gtranslator](https://wiki.gnome.org/Apps/Gtranslator) | Linux (GNOME) | Native GNOME app |
| [Lokalize](https://apps.kde.org/lokalize/) | Linux (KDE) | KDE translation tool |
| Any text editor | All | PO files are plain text |

**Translation tips:**

- Keep format placeholders intact: `{count}`, `{name}`, `%(prog)s`, etc.
- Preserve leading/trailing whitespace and newlines from the original string.
- Translate the `msgstr`, not the `msgid`.
- Strings marked `#, fuzzy` need review — remove the fuzzy flag after translating.
- For plural forms, fill in all `msgstr[N]` entries according to your language's plural rules.

### Step 4: Test locally

Compile the PO file and run ClamUI with your language:

```bash
# Compile the PO file to MO
msgfmt po/<LANG>.po -o po/<LANG>.mo

# Install to the locale directory (from project root)
mkdir -p locale/<LANG>/LC_MESSAGES
cp po/<LANG>.mo locale/<LANG>/LC_MESSAGES/clamui.mo

# Run ClamUI with your language
LANGUAGE=<LANG> uv run clamui
```

Verify that the translated strings appear correctly in the UI.

### Step 5: Submit a pull request

Your PR should include:

- `po/<LANG>.po` — the translation file
- `po/LINGUAS` — updated with your language code

Do **not** include compiled `.mo` files — these are generated during the build process.

## Updating an Existing Translation

When source strings change (after `./scripts/update-pot.sh` regenerates `po/clamui.pot`), update your PO file with `msgmerge`:

```bash
msgmerge --update po/<LANG>.po po/clamui.pot
```

This merges new strings into your PO file, marks removed strings as obsolete, and flags changed strings as fuzzy for review. After running `msgmerge`:

1. Search for `#, fuzzy` entries and review/update them.
2. Translate any new (empty `msgstr`) entries.
3. Remove obsolete entries if desired (lines starting with `#~`).

## What to Translate

**Translate:**

- Button labels, menu items, dialog titles
- Status messages, error messages shown to users
- Tooltips and descriptions

**Do NOT translate:**

- Logger messages (`logger.debug/info/warning/error`)
- Developer-facing exception messages
- CSS class names, D-Bus paths, settings keys, technical identifiers
- Shell commands shown to users (e.g., `sudo apt install clamav`)
- Application name "ClamUI"

## File Overview

| File | Purpose |
|------|---------|
| `po/clamui.pot` | POT template — extracted translatable strings (do not edit manually) |
| `po/POTFILES.in` | List of source files scanned for translatable strings |
| `po/LINGUAS` | List of available language codes |
| `po/<LANG>.po` | Translation file for a specific language |
| `scripts/update-pot.sh` | Script to regenerate the POT template from source |
| `src/core/i18n.py` | Runtime i18n module (`_`, `N_`, `ngettext`, `pgettext`) |

## For Developers

If you are adding new translatable strings to the source code, see the [i18n section in CLAUDE.md](../CLAUDE.md) for the string-marking conventions (`_()`, `N_()`, `ngettext()`, format string rules). After adding strings:

```bash
./scripts/update-pot.sh
```

This regenerates `po/clamui.pot`. Existing PO files can then be updated with `msgmerge` as described above.
