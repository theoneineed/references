# bib_manager.py
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
    This prevents showing cascading index shifts (e.g., if 1 item moves to the top,
    we don't flag the 99 items that shifted down by 1).
    """
    if not orig_ids: return []

    target_idx = {id_: i for i, id_ in enumerate(sorted_ids)}
    ranks = [target_idx[id_] for id_ in orig_ids]

    n = len(ranks)
    lengths = [1] * n
    parent = [-1] * n

    # Calculate Longest Increasing Subsequence
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

    # Any item NOT in the LIS is an item that was explicitly moved
    movements = []
    for i, id_ in enumerate(orig_ids):
        if i not in lis_indices:
            movements.append((id_, i + 1, target_idx[id_] + 1))

    return movements

def manage_bib():
    try:
        with open(BIB_FILE, 'r') as f:
            bib_database = bibtexparser.load(f)
    except FileNotFoundError:
        print(f"Error: {BIB_FILE} not found in the current directory.")
        sys.exit(1)

    current_entries = list(bib_database.entries)
    file_needs_write = False

    duplicates_log = []
    sorting_log = []

    # ---------------------------------------------------------
    # CHECK 1: Duplicates
    # ---------------------------------------------------------
    seen_ids = set()
    deduplicated_entries = []
    has_duplicates = False

    # Traverse backwards to keep the most recently added duplicate
    for i, entry in reversed(list(enumerate(current_entries))):
        if entry['ID'] not in seen_ids:
            seen_ids.add(entry['ID'])
            deduplicated_entries.append(entry)
        else:
            has_duplicates = True
            duplicates_log.append((entry['ID'], i + 1)) # 1-based index

    deduplicated_entries.reverse()
    duplicates_log.reverse() # Show top-to-bottom

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
    sorted_entries = sorted(current_entries, key=lambda x: x['ID'].lower())

    current_ids = [e['ID'] for e in current_entries]
    sorted_ids = [e['ID'] for e in sorted_entries]

    if current_ids != sorted_ids:
        print(f"\n[Notice] Your {BIB_FILE} is out of alphabetical order.")
        if get_user_approval("Would you like to automatically sort the entries alphabetically by tag? (y/n): "):
            sorting_log = get_sorting_movements(current_ids, sorted_ids)
            current_entries = sorted_entries
            file_needs_write = True
        else:
            print("Commit rejected: The .bib file must be alphabetically sorted.")
            sys.exit(1)

    # ---------------------------------------------------------
    # Write Updates and Output Diff Summary
    # ---------------------------------------------------------
    if file_needs_write:
        bib_database.entries = current_entries
        with open(BIB_FILE, 'w') as f:
            bibtexparser.dump(bib_database, f)

        print(f"\nSuccessfully updated {BIB_FILE}.")
        print("┌──────────────── SUMMARY OF CHANGES ────────────────┐")

        if duplicates_log:
            print("│ Duplicates Removed:")
            for id_, pos in duplicates_log:
                print(f"│   [-] {id_} (removed older copy from position {pos})")
            if sorting_log:
                print("│")

        if sorting_log:
            print("│ Sorting Adjustments (Out-of-place entries moved):")
            for id_, old_pos, new_pos in sorting_log:
                print(f"│   [~] {id_}: moved from pos {old_pos} -> pos {new_pos}")

        print("└────────────────────────────────────────────────────┘\n")

    sys.exit(0)

if __name__ == '__main__':
    manage_bib()