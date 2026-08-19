# Managed Run Workspace

Read this file before creating any generated or temporary artifact.

## Create

Create exactly one workspace for the task:

```text
python scripts/manage_run_workspace.py create
```

Keep the returned absolute `run_dir` in memory. Store every candidate, unlettered master, retry, reference board, mask, and review crop inside it. Never place source images or the final deliverable in this directory. Keep prompts and decisions in memory, run backend commands synchronously, and do not create prompt, score, PID, stdout, stderr, or log files.

## Finish

Write the approved final image to a user-facing path outside `run_dir`, verify it there, and then clean the workspace:

```text
python scripts/manage_run_workspace.py cleanup --run-dir <absolute-run-dir>
```

Run cleanup after success or failure. After an interrupted task resumes, make cleanup the first action before any new generation. The command is intentionally limited to a direct child of the system temporary directory with a matching private marker. Cleanup first claims the directory exclusively, atomically moves it to a private cleanup name, and validates it again before recursive deletion. Concurrent cleanup therefore removes the workspace at most once, while a path replaced by a symbolic link or Windows junction is refused. Do not bypass these safety checks or replace them with a broad recursive deletion command. If cleanup refuses a path, leave the files in place and report the exact refusal.
