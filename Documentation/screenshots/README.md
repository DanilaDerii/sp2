# README screenshots

Images referenced from the repository README.

| Filename | Status | What it shows / should show |
|---|---|---|
| `enable-tool-in-chat.jpg` | **captured** | The Integrations panel (hammer icon) with `mcp/lecture-sense-rag` toggled on, plus a real `sp2_list_packs` call and its grounded answer. |
| `lm-studio-developer-mode.png` | not captured | The LM Studio mode selector with Developer selected. |
| `mcp-json-location.png` | not captured | LM Studio's MCP/integrations settings screen - the one with the "Edit mcp.json" button. A screenshot of the raw file adds nothing over the JSON block already in the README. |

The README currently shows broken image icons for the two that are missing.
Either capture them, or remove those two `![...]` lines until they exist.

## Capturing

On the dev machine (Hyprland), `Alt+S` is bound to `grimblast save area`, or
capture straight into place:

```bash
grimblast save area Documentation/screenshots/<filename>
```

Crop to the relevant panel rather than the whole screen, and check the visible
chat content before committing - an answer that was not grounded in a course
pack should not be presented as an example of SP2 working.
