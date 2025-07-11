from git import Repo
from unidiff import PatchSet
import sys

def track_changes(repo_path: str, old_sha: str, new_sha: str):
    """
    Track the changes between two commits in a repository.
    """
    # Get the repository and the diff between the two commits
    repo = Repo(repo_path)
    diff_str = repo.git.diff(old_sha, new_sha, unified=0, find_renames=True)
    patch = PatchSet(diff_str)

    # Initialize the data structures
    renames = {}
    offsets = {}
    modified_lines = {}

    # Iterate over the patched files
    for patched_file in patch:
        # Get the old and new filenames
        old_file = patched_file.source_file.lstrip('a/')
        new_file = patched_file.target_file.lstrip('b/')

        # Record renames (if the file has been renamed)
        if old_file != new_file:
            renames[new_file] = old_file

        # Use the new filename for tracking (or old if not renamed)
        filename = new_file if old_file != new_file else old_file

        # Initialize the data structures for the checking file
        file_offsets = offsets.setdefault(filename, {})
        file_modified_lines = modified_lines.setdefault(filename, set())
        cumulative_offset = 0

        # Iterate over the hunks in the patched file
        # A hunk is a contiguous block of changes (additions/deletions)
        for hunk in patched_file:
            # Iterate over each line in the current hunk (can be added, removed, or unchanged)
            for line in hunk:
                if line.is_added:  # If the line was added
                    cumulative_offset += 1  # One more line in the file
                    if hasattr(line, 'target_line_no') and line.target_line_no:
                        file_modified_lines.add(line.target_line_no)  # Track added lines (they appear in the new version)
                elif line.is_removed:
                    cumulative_offset -= 1  # One less line in the file
                    if hasattr(line, 'source_line_no') and line.source_line_no:
                        file_modified_lines.add(line.source_line_no)  # Track removed lines (they existed in the old version)

            # Store cumulative offset at the starting line of the hunk
            if hunk.source_start not in file_offsets:
                file_offsets[hunk.source_start] = 0
            file_offsets[hunk.source_start] = cumulative_offset  # Store cumulative offset at the starting line of the hunk

    # Return the data structures
    return renames, offsets, modified_lines

# Get the project path and sha of the current commit from the command line
# Usage: python filter_new_violations.py <repo_path> <current_commit_sha>
repo_path = sys.argv[1]
current_sha = sys.argv[2]

# Get the parent sha of the current commit
# This allows us to compare the current commit with its immediate predecessor
repo = Repo(repo_path)
commit = repo.commit(current_sha)
parent_sha = commit.parents[0].hexsha if commit.parents else None

# Print the project info for debugging
print(f"Project path: {repo_path}")
print(f"Current SHA: {current_sha}")
print(f"Parent SHA: {parent_sha}")

# Track the changes between the current and parent commit
# If there's no parent (initial commit), use empty data structures
if parent_sha:
    renames, offsets, modified_lines = track_changes(repo_path, parent_sha, current_sha)
else:
    renames, offsets, modified_lines = {}, {}, {}

# Print the results for each file that had changes
for f in offsets:
    print(f"File: {f}")
    print(f"  Offsets: {offsets[f]}")  # Line number -> cumulative offset mapping
    print(f"  Modified lines: {modified_lines[f]}")  # Set of changed line numbers

# Print any file renames that occurred
if renames:
    print("Renamed files:")
    for new, old in renames.items():
        print(f"  {old} -> {new}")