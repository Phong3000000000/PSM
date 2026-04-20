# Module JSON Map

This folder contains a generated JSON map for `M02_P0205`.

Files:
- `module_map.json`: module-level overview for fast agent loading.
- `module_map_stats.json`: compact counts and size hints.
- `details/*.json`: per-file extracted details for deeper lookup.
- `build_module_map.py`: generator script.

Recommended loading flow:
1. Load `module_map.json` first.
2. Read only the matching files in `details/` when a question needs deeper context.
3. Use `relations` in `module_map.json` to jump between models, views, security, and data files.

Regenerate:

```powershell
python structure\build_module_map.py
```
