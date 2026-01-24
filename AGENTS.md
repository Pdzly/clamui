# AGENTS.md - ClamUI Agent Guidelines

This document provides project-specific guidance for AI agents working on the ClamUI codebase.

## Required Setup

**Before making any commits**, ensure git hooks are installed:

```bash
./scripts/hooks/install-hooks.sh
```

This installs the **pre-commit hook** which checks for absolute `src.*` imports. These imports break when ClamUI is installed as a Debian package (installed as `clamui`, not `src`).

**What the hook checks:**

- Blocks commits with `from src.` or `import src.` in `src/` files
- Suggests using relative imports instead (`from ..core.module import X`)

## Project-Specific Agent Notes

### Security Reviews

When performing security reviews on ClamUI code:

- **Input Sanitization**: Always check for proper use of `sanitize_log_line()` and `sanitize_log_text()` for any user-controlled or external input before logging
- **Command Execution**: Verify `shlex.quote()` usage in subprocess commands, especially in `scheduler.py` and any code building shell commands
- **Path Validation**: Ensure `validate_path()` and `check_symlink_safety()` are used before file operations with user-provided paths
- **File Permissions**: New files containing sensitive data should use `chmod(0o600)` for owner-only access

### GTK4/Adwaita Changes

When modifying UI code:

- **Use `Adw.Window` (1.0+)**, NOT `Adw.Dialog` (1.5+) - required for Ubuntu 22.04 compatibility
- **Always use `GLib.idle_add()`** for UI updates from background threads
- **Use `resolve_icon_name()`** wrapper when creating icons for fallback support
- **Standard Adwaita icons only** - never use application-specific or KDE icons
- **gi.require_version()** must be called before importing from `gi.repository`

### Packaging Changes

When modifying dependencies:

- **Update BOTH** `flathub/requirements-runtime.txt` AND `debian/DEBIAN/control` when adding Python dependencies
- **Regenerate** `flathub/python3-runtime-deps.json` after Flatpak dependency changes using `req2flatpak`
- **Version constraints** should match `pyproject.toml` in packaging files
- **Test on Ubuntu 22.04** baseline for compatibility (libadwaita 1.1.x)

### Testing Requirements

When writing or modifying code:

- Run `pytest --cov=src` for coverage verification
- **Minimum 50% coverage** required (`fail_under` in `pyproject.toml`)
- **Target 80%+ coverage** for `src/core`, 70%+ for `src/ui`
- Use `mock_gi_modules` fixture from `tests/conftest.py` for UI tests
- Test files mirror source structure: `src/core/foo.py` → `tests/core/test_foo.py`

### Thread Safety

ClamUI is a GTK4 application with background operations:

- **Never update UI from background threads** - always use `GLib.idle_add(callback)`
- **Use `threading.Lock()`** for shared state in manager classes
- **Check existing patterns** in `scanner.py`, `quarantine/manager.py` for async operation examples

### Flatpak Considerations

When working with file operations:

- **Use `wrap_host_command()`** from `src/core/flatpak.py` for commands that execute on host
- **Check `is_flatpak()`** when behavior differs between native and Flatpak installations
- **Database paths** differ in Flatpak - see `get_clamav_database_dir()` for correct paths

### Code Style

Follow the project conventions:

- **Relative imports** within `src/` package (not absolute `src.*` imports)
- **Dataclasses** for structured data with computed `@property` methods
- **Type hints** throughout the codebase
- **Docstrings** for public methods and classes
- Run `uv run ruff check --fix` and `uv run ruff format` before committing

## Agent Workflow Recommendations

### For Bug Fixes

1. Read relevant code to understand the issue
2. Check for existing tests
3. Write a failing test first (TDD approach)
4. Implement the fix
5. Run full test suite
6. Check for similar issues elsewhere in codebase

### For New Features

1. Check `CLAUDE.md` for architecture patterns
2. Review existing similar features for patterns
3. Plan the implementation (UI, core logic, tests)
4. Implement with proper thread safety
5. Add comprehensive tests
6. Update documentation if needed

### For Security Changes

1. Review `src/core/sanitize.py` and `src/core/path_validation.py` for patterns
2. Apply defense-in-depth (sanitize at multiple layers)
3. Test with malicious inputs (ANSI escapes, Unicode bidi, newlines)
4. Verify file permissions for sensitive data
5. Check subprocess calls for injection vulnerabilities
