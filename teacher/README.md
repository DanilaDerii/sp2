# SP2 Teacher Builder

Local teacher-side app for building course packs from source materials.

Current v1 backend flow:

```text
PDF -> Docling extraction -> chunks -> all-minilm embeddings -> pack files -> zip
```

Run the API shell from this directory:

```bash
uvicorn backend.app:app --reload
```

The pack contract is still documented in the root `project_log/` files.
