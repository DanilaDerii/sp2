# README screenshots

Images referenced from the repository README. All six slots are filled; the
README has no broken image references.

| Filename | What it shows |
|---|---|
| `lm-studio-download.jpg` | The lmstudio.ai download page, showing the OS, architecture and version selectors. |
| `mcp-json-step1.jpg` | The Developer tab (terminal icon, far-left sidebar) and Local Server panel, with the `mcp.json` button circled. |
| `mcp-json-step2.jpg` | The Edit mcp.json dialog with the SP2 `lecture_sense_rag` entry. |
| `mcp-approve-prompt.jpg` | LM Studio's Add MCP Server dialog for `lecture_sense_rag`, opened at the end of setup. Shows "Override" rather than "Add" because the server already existed on this machine. |
| `mcp-server-added.jpg` | The confirmation that `lecture_sense_rag` was added. |
| `enable-tool-in-chat.jpg` | The Integrations panel (hammer icon) with `mcp/lecture-sense-rag` toggled on, plus a real `sp2_list_packs` call and its grounded answer. |

## If you replace or add one

On the dev machine (Hyprland), `Alt+S` is bound to `grimblast save area`, or
capture straight into place:

```bash
grimblast save area Documentation/screenshots/<filename>
```

Two things to check before committing a screenshot:

- **Visible chat content.** An answer that was not grounded in a course pack
  should never be presented as an example of SP2 working. An earlier capture
  had to be retaken because the model had invented statistics that appear
  nowhere in the pack.
- **Absolute paths.** `mcp-json-step2.jpg` shows real home-directory paths
  including a local username. That is intentional - it makes the example
  concrete - but crop or edit if a future capture would expose something
  more identifying.
