# bib_manager.py
# code mostly written by gemini, under my supervision
import bibtexparser
import sys

BIB_FILE = 'allReferences.bib'

def get_user_approval(prompt_text):
    """Reads directly from the terminal to bypass Git hook stdin hijacking."""
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    with open('/dev/tty', 'r') as tty:
        response = tty.readline().strip().lower()
        return response == 'y'

def get_sorting_movements(orig_ids, sorted_ids):
    """
    Finds the minimal number of moved items using Longest Increasing Subsequence.
    This prevents showing cascading index shifts.
    """
    if not orig_ids: return []

    target_idx = {id_: i for i, id_ in enumerate(sorted_ids)}
    ranks = [target_idx[id_] for id_ in orig_ids]

    n = len(ranks)
    lengths = [1] * n
    parent = [-1] * n

    for i in range(n):
        for j in range(i):
            if ranks[i] > ranks[j] and lengths[i] < lengths[j] + 1:
                lengths[i] = lengths[j] + 1
                parent[i] = j

    max_idx = lengths.index(max(lengths)) if lengths else -1
    lis_indices = set()
    curr = max_idx
    while curr != -1:
        lis_indices.add(curr)
        curr = parent[curr]

    movements = []
    for i, id_ in enumerate(orig_ids):
        if i not in lis_indices:
            movements.append((id_, i + 1, target_idx[id_] + 1))

    return movements

def manage_bib():
    try:
        # v2 Syntax for parsing
        library = bibtexparser.parse_file(BIB_FILE)
    except Exception as e:
        print(f"Error: Could not read {BIB_FILE}. {e}")
        sys.exit(1)

    # In v2, data is stored as a list of Block objects in library.blocks.
    # We separate Entry objects from Comments/Strings to sort only the citations.
    other_blocks = [b for b in library.blocks if type(b).__name__ != 'Entry']
    current_entries = [b for b in library.blocks if type(b).__name__ == 'Entry']

    file_needs_write = False
    duplicates_log = []
    sorting_log = []

    # ---------------------------------------------------------
    # CHECK 1: Duplicates
    # ---------------------------------------------------------
    seen_keys = set()
    deduplicated_entries = []
    has_duplicates = False

    # Traverse backwards to keep the most recently added duplicate
    for i, entry in reversed(list(enumerate(current_entries))):
        if entry.key not in seen_keys:
            seen_keys.add(entry.key)
            deduplicated_entries.append(entry)
        else:
            has_duplicates = True
            duplicates_log.append((entry.key, i + 1))

    deduplicated_entries.reverse()
    duplicates_log.reverse()

    if has_duplicates:
        print(f"\n[Notice] Your {BIB_FILE} has duplicate entries.")
        if get_user_approval("Would you like to automatically keep the newest entry and remove the duplicates? (y/n): "):
            current_entries = deduplicated_entries
            file_needs_write = True
        else:
            print("Commit rejected: Duplicate entries must be resolved.")
            sys.exit(1)

    # ---------------------------------------------------------
    # CHECK 2: Alphabetical Order
    # ---------------------------------------------------------
    sorted_entries = sorted(current_entries, key=lambda x: x.key.lower())

    current_keys = [e.key for e in current_entries]
    sorted_keys = [e.key for e in sorted_entries]

    if current_keys != sorted_keys:
        print(f"\n[Notice] Your {BIB_FILE} is out of alphabetical order.")
        if get_user_approval("Would you like to automatically sort the entries alphabetically by tag? (y/n): "):
            sorting_log = get_sorting_movements(current_keys, sorted_keys)
            current_entries = sorted_entries
            file_needs_write = True
        else:
            print("Commit rejected: The .bib file must be alphabetically sorted.")
            sys.exit(1)

    # ---------------------------------------------------------
    # Write Updates and Output Diff Summary
    # ---------------------------------------------------------
    if file_needs_write:
        # Create a completely new Library object initialized with the merged blocks
        new_library = bibtexparser.Library(blocks=other_blocks + current_entries)

        # v2 Syntax for writing
        bibtexparser.write_file(BIB_FILE, new_library)

        print(f"\nSuccessfully updated {BIB_FILE}.")
        print("┌──────────────── SUMMARY OF CHANGES ────────────────┐")

        if duplicates_log:
            print("│ Duplicates Removed:")
            for key, pos in duplicates_log:
                print(f"│   [-] {key} (removed older copy from position {pos})")
            if sorting_log:
                print("│")

        if sorting_log:
            print("│ Sorting Adjustments (Out-of-place entries moved):")
            for key, old_pos, new_pos in sorting_log:
                print(f"│   [~] {key}: moved from pos {old_pos} -> pos {new_pos}")

        print("└────────────────────────────────────────────────────┘\n")

    sys.exit(0)

if __name__ == '__main__':
    manage_bib()