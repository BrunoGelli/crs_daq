"""Physical geometry and explicit connector assignments for CERN 10x16 tiles."""

N_COLUMNS = 16
N_ROWS = 10
FIRST_POSITION = 11
PHYSICAL_ROOT_POSITIONS = frozenset((21, 61, 111, 151))

# These are programmed IDs used by the successful donor test.  In particular,
# ID 101 is not evidence that the third connector reaches physical position 101.
V2D_DONOR_ROOT_IDS = {25: 21, 26: 61, 27: 101, 28: 151}


def position_from_column_row(column, row):
    if not 0 <= column < N_COLUMNS or not 0 <= row < N_ROWS:
        raise ValueError(f"outside 10x16 tile: column={column}, row={row}")
    return FIRST_POSITION + N_ROWS * column + row


def column_row_from_position(position):
    offset = int(position) - FIRST_POSITION
    if not 0 <= offset < N_COLUMNS * N_ROWS:
        raise ValueError(f"outside 10x16 tile: position={position}")
    column, row = divmod(offset, N_ROWS)
    return column, row


def physical_neighbors(position):
    """Return cardinal neighbors without wrapping between columns."""
    column, row = column_row_from_position(position)
    neighbors = set()
    for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        next_column, next_row = column + dc, row + dr
        if 0 <= next_column < N_COLUMNS and 0 <= next_row < N_ROWS:
            neighbors.add(position_from_column_row(next_column, next_row))
    return neighbors


def validate_physical_links(links):
    """Reject declared chip-to-chip links that are not adjacent in the layout."""
    links = list(links)
    for source, target in links:
        if target not in physical_neighbors(source):
            raise ValueError(f"non-neighbor physical link {source}->{target}")
    return links


def validate_physical_root_assignment(root_map, live_channels):
    """Validate an operator-confirmed connector-to-physical-root assignment."""
    live_channels = set(live_channels)
    if set(root_map) != live_channels:
        raise ValueError(
            f"physical root map must cover exactly live channels {sorted(live_channels)}"
        )
    if not set(root_map.values()).issubset(PHYSICAL_ROOT_POSITIONS):
        raise ValueError("physical root IDs must be declared top-row root positions")
    if len(set(root_map.values())) != len(root_map):
        raise ValueError("physical root IDs must be unique")
    return dict(root_map)
