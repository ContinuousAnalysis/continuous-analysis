from git import Repo
from unidiff import PatchSet
import sys
from collections import defaultdict


def track_changes(repo_path: str, old_sha: str, new_sha: str):
    """
    Track the changes between two commits in a repository.
    """
    # Get the repository and the diff between the two commits
    repo = Repo(repo_path)
    diff_str = repo.git.diff(old_sha, new_sha, unified=0, find_renames=True)
    patch = PatchSet(diff_str)

    # Initialize the tracking data structures
    renames = {}  # New filename -> old filename
    offsets = {}  # File -> line number -> cumulative offset
    modified_lines = {}  # File -> set of line numbers
    added_lines = defaultdict(list)  # File -> list of (start, end) tuples in new file
    deleted_lines = defaultdict(list)  # File -> list of (start, end) tuples in old file
    modified_lines_old = defaultdict(list)  # File -> list of (start, end) tuples in old file
    modified_lines_new = defaultdict(list)  # File -> list of (start, end) tuples in new file

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

        # Initialize the tracking variables for the current hunk
        current_added_start = None
        current_added_end = None
        current_deleted_start = None
        current_deleted_end = None
        current_modified_old_start = None
        current_modified_old_end = None
        current_modified_new_start = None
        current_modified_new_end = None
        
        # Track the last deleted line to detect modifications
        last_deleted_line = None

        # Iterate over the hunks in the patched file
        # A hunk is a contiguous block of changes (additions/deletions)
        for hunk in patched_file:
            # Iterate over each line in the current hunk (can be added, removed, or unchanged)
            for line in hunk:
                if line.is_added:  # If the line was added
                    cumulative_offset += 1  # One more line in the file
                    if hasattr(line, 'target_line_no') and line.target_line_no:
                        file_modified_lines.add(line.target_line_no)  # Track added lines (they appear in the new version)
                        
                        # Track added line ranges
                        if current_added_start is None:
                            current_added_start = line.target_line_no
                        current_added_end = line.target_line_no
                        
                        # Check if this might be a modification (if we just had a deletion)
                        if last_deleted_line is not None:
                            # This could be a modification - track both old and new line ranges
                            if current_modified_old_start is None:
                                current_modified_old_start = current_deleted_start
                            current_modified_old_end = current_deleted_end
                            
                            if current_modified_new_start is None:
                                current_modified_new_start = current_added_start
                            current_modified_new_end = current_added_end
                        
                elif line.is_removed:
                    cumulative_offset -= 1  # One less line in the file
                    if hasattr(line, 'source_line_no') and line.source_line_no:
                        file_modified_lines.add(line.source_line_no)  # Track removed lines (they existed in the old version)
                        
                        # Track deleted line ranges
                        if current_deleted_start is None:
                            current_deleted_start = line.source_line_no
                        current_deleted_end = line.source_line_no
                        
                        # Store the last deleted line for potential modification detection
                        last_deleted_line = line.source_line_no
                        
                elif line.is_context:  # Context line (unchanged)
                    # If we have pending ranges, save them
                    if current_added_start is not None and current_added_end is not None:
                        added_lines[filename].append((current_added_start, current_added_end))
                        current_added_start = None
                        current_added_end = None
                    
                    if current_deleted_start is not None and current_deleted_end is not None:
                        deleted_lines[filename].append((current_deleted_start, current_deleted_end))
                        current_deleted_start = None
                        current_deleted_end = None
                        
                    if current_modified_old_start is not None and current_modified_old_end is not None:
                        modified_lines_old[filename].append((current_modified_old_start, current_modified_old_end))
                        current_modified_old_start = None
                        current_modified_old_end = None
                        
                    if current_modified_new_start is not None and current_modified_new_end is not None:
                        modified_lines_new[filename].append((current_modified_new_start, current_modified_new_end))
                        current_modified_new_start = None
                        current_modified_new_end = None
                    
                    # Reset modification tracking
                    last_deleted_line = None

            # At the end of each hunk, save any pending ranges
            if current_added_start is not None and current_added_end is not None:
                added_lines[filename].append((current_added_start, current_added_end))
                current_added_start = None
                current_added_end = None
            
            if current_deleted_start is not None and current_deleted_end is not None:
                deleted_lines[filename].append((current_deleted_start, current_deleted_end))
                current_deleted_start = None
                current_deleted_end = None
                
            if current_modified_old_start is not None and current_modified_old_end is not None:
                modified_lines_old[filename].append((current_modified_old_start, current_modified_old_end))
                current_modified_old_start = None
                current_modified_old_end = None
                
            if current_modified_new_start is not None and current_modified_new_end is not None:
                modified_lines_new[filename].append((current_modified_new_start, current_modified_new_end))
                current_modified_new_start = None
                current_modified_new_end = None
            
            # Reset modification tracking at the end of each hunk
            last_deleted_line = None

            # Store cumulative offset at the starting line of the hunk
            if hunk.source_start not in file_offsets:
                file_offsets[hunk.source_start] = 0
            file_offsets[hunk.source_start] = cumulative_offset  # Store cumulative offset at the starting line of the hunk

    # Create a comprehensive result structure
    detailed_changes = {
        'renames': renames,
        'offsets': offsets,
        'modified_lines': modified_lines,
        'added_lines': dict(added_lines),
        'deleted_lines': dict(deleted_lines),
        'modified_lines_old': dict(modified_lines_old),
        'modified_lines_new': dict(modified_lines_new)
    }

    # Return the detailed changes
    return detailed_changes

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
    changes = track_changes(repo_path, parent_sha, current_sha)
else:
    changes = {
        'renames': {},
        'offsets': {},
        'modified_lines': {},
        'added_lines': {},
        'deleted_lines': {},
        'modified_lines_old': {},
        'modified_lines_new': {}
    }

# Print the results for each file that had changes
for filename in changes['offsets']:
    print(f"\nFile: {filename}")
    print(f"  Offsets: {changes['offsets'][filename]}")  # Line number -> cumulative offset mapping
    print(f"  Modified lines: {changes['modified_lines'][filename]}")  # Set of changed line numbers
    
    # Print detailed line range information
    if filename in changes['added_lines']:
        print(f"  Added line ranges (new file): {changes['added_lines'][filename]}")
    if filename in changes['deleted_lines']:
        print(f"  Deleted line ranges (old file): {changes['deleted_lines'][filename]}")
    if filename in changes['modified_lines_old']:
        print(f"  Modified line ranges (old file): {changes['modified_lines_old'][filename]}")
    if filename in changes['modified_lines_new']:
        print(f"  Modified line ranges (new file): {changes['modified_lines_new'][filename]}")

# Print any file renames that occurred
if changes['renames']:
    print("\nRenamed files:")
    for new, old in changes['renames'].items():
        print(f"  {old} -> {new}")