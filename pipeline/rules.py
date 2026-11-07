"""Explicit OSM tag rules. Geometry and length calculations use EPSG:3067."""
ROADS = set('primary secondary tertiary unclassified residential primary_link secondary_link tertiary_link'.split())
HARD_SURFACES = {'asphalt', 'paved', 'paving_stones', 'paving_stones:30', 'concrete',
                 'concrete:plates', 'concrete:lanes', 'sett', 'cobblestone',
                 'cobblestone:flattened', 'unhewn_cobblestone', 'bricks', 'tiles'}

def public(tags):
    return tags.get('access') not in {'private', 'no'} and tags.get('foot') not in {'private', 'no'} and tags.get('area') != 'yes'

def reference_road(tags):
    if tags.get('highway') not in ROADS or tags.get('area')=='yes' or tags.get('access')=='private':
        return False
    if tags.get('access')=='no':
        # A bus/cycle/destination street remains a physical street reference.
        allowed = {'yes','designated','permissive','destination','customers'}
        return any(tags.get(mode) in allowed for mode in ('foot','bicycle','psv','motor_vehicle','vehicle'))
    # foot=no applies to the carriageway, not to its separate sidewalks.
    return True

def sidewalk_sides(tags):
    defaults = {'both': (True, True), 'left': (True, False), 'right': (False, True)}.get(tags.get('sidewalk'), (False, False))
    both = tags.get('sidewalk:both')
    return tuple(tags.get('sidewalk:'+side, both if both is not None else ('yes' if default else 'no')) == 'yes' for side, default in zip(('left','right'), defaults))

def candidate_category(tags):
    """Broad candidate cache, with physical street references separate from foot access."""
    if tags.get('highway')=='living_street' and public(tags):
        return 'road_context'
    if reference_road(tags):
        return 'road'
    if not public(tags):
        return None
    highway = tags.get('highway')
    if highway not in {'footway', 'cycleway', 'path'} or tags.get('footway') in {'crossing', 'access_aisle'}:
        return None
    cycling = highway == 'cycleway' or tags.get('bicycle') == 'designated'
    if cycling:
        if highway!='footway' and tags.get('foot') != 'designated':
            return None
        return {'yes': 'segregated', 'no': 'shared'}.get(tags.get('segregated'), 'unknown')
    if highway == 'footway' or (highway == 'path' and tags.get('foot') == 'designated'):
        return 'footway'
    return None

def walking_surface(tags):
    return tags.get('footway:surface', tags.get('surface', '')).strip().lower()

def tag_rejection(tags):
    if tags.get('highway')=='living_street':
        return 'living_street_rajattu_pois'
    kind = candidate_category(tags)
    if kind is None:
        return 'tagisaanto'
    if kind == 'road':
        return None
    if tags.get('highway') == 'path':
        return 'highway_path'
    if tags.get('footway') == 'traffic_island':
        return 'liikennesaareke'
    if kind in {'shared', 'unknown'}:
        return None
    surface = walking_surface(tags)
    if not surface:
        return None  # User-specified default: an unrecorded surface is asphalt.
    if not all(value.strip() in HARD_SURFACES for value in surface.split(';')):
        return 'ei_hyvaksytty_kova_pinta'
    return None

def category(tags):
    return None if tag_rejection(tags) else candidate_category(tags)
