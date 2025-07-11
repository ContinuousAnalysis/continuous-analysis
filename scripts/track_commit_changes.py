from git import Repo
from unidiff import PatchSet

import sys
from collections import defaultdict


"""
This script is used to track the changes between two commits in a repository.
It should return the following information:
- Any renames happened in the commit
- The line number offsets of the old file to the new file (used to get the corresponding line number of the new file from the old file)
- The new file changes (line ranges that were added/modified)

The line number offsets can be used to get the line number of the new file from the old file by subtracting the offset from the line number of the old file.
- line_number_new = line_number_old - offset

The new file changes can be filtered out the violations that are from the changed code which should always be considered as new violations.
"""

def track_changes(repo_path: str, old_sha: str, new_sha: str):
    """
    Track the changes between two commits in a repository.

    Args:
        repo_path: The path to the repository.
        old_sha: The SHA of the old commit.
        new_sha: The SHA of the new commit.

    Returns:
        A dictionary containing the changes between the two commits.
    """
    # Get the repository and the diff between the two commits
    repo = Repo(repo_path)
    diff_str = repo.git.diff(old_sha, new_sha, unified=0, find_renames=True)
    patch = PatchSet(diff_str)

    # Declare variables needed for tracking changes
    renames = {}  # Dictionary to track file renames (new filename -> old filename)
    offsets = {}  # Dictionary to track line number offsets of the old file to the new file (file -> line number -> cumulative offset)
    new_file_changes = defaultdict(list)  # Dictionary to track new file changes (file -> list of (start, end) tuples in new file)

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

        # Initialize the dict for tracking line number offsets of the old file to the new file
        file_offsets = offsets.setdefault(filename, {})

        # Initialize the cumulative offset for the current file
        cumulative_offset = 0

        # Iterate over the hunks (blocks of changes) in the patched file
        for hunk in patched_file:

            # Initialize the tracking variables for the current hunk
            current_new_start = None
            current_new_end = None

            # Iterate over each line in the current hunk (can be added, removed, or unchanged)
            for line in hunk:

                # If the line was added
                if line.is_added:
                    cumulative_offset += 1  # Add one more line to the cumulative offset
                    # Update the current new change range
                    if hasattr(line, 'target_line_no') and line.target_line_no:
                        if current_new_start is None:
                            current_new_start = line.target_line_no
                        current_new_end = line.target_line_no

                # If the line was removed
                elif line.is_removed:
                    cumulative_offset -= 1  # Subtract one line from the cumulative offset
                    # No need to update the current new change range as the line was removed from the old file
                    # This have no effect on the new file

                # If the line was unchanged
                elif line.is_context:
                    # Save the current new change range if it exists
                    if current_new_start is not None and current_new_end is not None:
                        new_file_changes[filename].append((current_new_start, current_new_end))
                        # Reset the current new change range
                        current_new_start = None
                        current_new_end = None

            # At the end of each hunk, save new changes if they exist
            if current_new_start is not None and current_new_end is not None:
                new_file_changes[filename].append((current_new_start, current_new_end))

            # Store cumulative offset at the starting line of the hunk
            # This can be used easily to get the line number of the new file from the old file
            file_offsets[hunk.source_start] = cumulative_offset

    # Format the changes into a comprehensive result structure
    detailed_changes = {
        'renames': renames,
        'offsets': offsets,
        'new_file_changes': dict(new_file_changes)
    }

    # Return the detailed changes
    return detailed_changes


# ================================
# Main function
# ================================


def main():
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
            'new_file_changes': {}
        }

    return changes


# ================================
# Script entry point for testing purposes
# Print the results for each file that had changes
# ================================


if __name__ == "__main__":
    # Get the changes between the current and parent commit
    changes = main()

    # Print any file renames that occurred
    if changes['renames']:
        print("\nRenamed files:")
        for new, old in changes['renames'].items():
            print(f"- {old} -> {new}")
        print()

    for filename in changes['offsets']:
        
        # Convert the filename to the original filename if it was renamed
        new_filename = filename
        old_filename = filename
        if changes['renames'].get(filename) is not None:
            old_filename = changes['renames'][filename]
            
        print(f"\nFile: {old_filename}:")
        print(f"- Offsets: {changes['offsets'][filename]}")

        if new_filename in changes['new_file_changes']:
            print(f"- New file changes: {changes['new_file_changes'][new_filename]}")