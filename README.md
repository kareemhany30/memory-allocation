# Memory Allocation Project using Segmentation

Python/Pygame GUI for the operating systems memory allocation assignment.

## Features

- Configure total memory size.
- Add initial free partitions (holes) with starting address and size.
- Add processes one by one with any number of named segments.
- Allocate with First-Fit or Best-Fit.
- Reject a process if any segment cannot fit, with rollback of already-tested segments.
- Deallocate a whole process and merge released space with neighboring holes.
- Show a live memory layout, free partitions table, and segment table.

## Requirements

Use Python 3.10 to 3.13. Pygame may not have a Windows wheel yet for Python 3.14.

## Run

```bash
py -3.13 -m pip install -r requirements.txt
py -3.13 main.py
```

## Test

```bash
py -3.13 tests.py
```

## GitHub Upload

This folder is already initialized as a Git repository. To upload it:

```bash
git add .
git commit -m "Initial memory allocation pygame project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPOSITORY` with your GitHub details.
