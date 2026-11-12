"""Deduplicate road-side tags against separately mapped walking routes."""
import math

from shapely.geometry import LineString
from shapely.ops import substring
from shapely.strtree import STRtree

from .corridor import flat_lines
from .rules import sidewalk_sides

TAGGED_POLICY = {
    'coverage': 'longitudinal_projection_per_road_side',
    'max_angle_degrees': 30,
    'gap_tolerance_m': 1.0,
    'end_tolerance_m': 2.0,
    'near_complete_side_ratio': .85,
    'near_complete_gap_m': 15.0,
    'separate_categories': ['footway', 'segregated', 'shared', 'unknown'],
}


def tagged_sidewalks(roads, paths, boundary, distance, level):
    """Yield (road id, side, geometry) for tag lengths not mapped separately.

    Project each matched path fragment onto the local directed road segment.
    Adjacent fragments then meet at the same road coordinate, even when their
    headings differ. Buffer end caps cannot create tiny uncovered wedges.
    Merge coverage along the original road way, across its sampling boundaries.
    """
    records = [(line, tags) for geom, tags in paths for line in flat_lines(geom)]
    tree = STRtree([row[0] for row in records])
    cos_angle = math.cos(math.radians(TAGGED_POLICY['max_angle_degrees']))
    for oid, tags, road in roads:
        enabled = {side for side, yes in zip(('left', 'right'), sidewalk_sides(tags)) if yes}
        if not enabled:
            continue
        coverage = {side: [] for side in enabled}
        offset = 0.0
        for a, b in zip(road.coords, list(road.coords)[1:]):
            segment = LineString([a, b])
            length = segment.length
            if length <= 1e-8:
                continue
            ux, uy = (b[0]-a[0])/length, (b[1]-a[1])/length
            strip = segment.buffer(distance, cap_style=2)
            for raw_i in tree.query(strip):
                path, ptags = records[int(raw_i)]
                if level(tags) != level(ptags):
                    continue
                p, q = path.coords[0], path.coords[-1]
                dx, dy = q[0]-p[0], q[1]-p[1]
                norm = math.hypot(dx, dy)
                if norm <= 1e-8 or abs(ux*dx+uy*dy)/norm < cos_angle:
                    continue
                for clipped in flat_lines(path.intersection(strip)):
                    mid = clipped.interpolate(.5, normalized=True)
                    signed = ux*(mid.y-a[1])-uy*(mid.x-a[0])
                    if abs(signed) <= .25:
                        continue
                    side = 'left' if signed > 0 else 'right'
                    if side not in enabled:
                        continue
                    positions = [ux*(x-a[0])+uy*(y-a[1]) for x,y in clipped.coords]
                    start, end = max(0.0, min(positions)), min(length, max(positions))
                    if end-start > 1e-6:
                        coverage[side].append((offset+start, offset+end))
            offset += length
        for side in sorted(enabled):
            merged = []
            for start, end in sorted(coverage[side]):
                if merged and start <= merged[-1][1]+TAGGED_POLICY['gap_tolerance_m']:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            # A mapped sidewalk can curve around intersection corners while the
            # road's last few metres turn in another direction. Do not invent
            # short tag-only sidewalks in an otherwise mapped road side.
            near_complete = sum(end-start for start,end in merged) >= road.length*TAGGED_POLICY['near_complete_side_ratio']
            gap_limit = TAGGED_POLICY['near_complete_gap_m'] if near_complete else TAGGED_POLICY['gap_tolerance_m']
            end_limit = TAGGED_POLICY['near_complete_gap_m'] if near_complete else TAGGED_POLICY['end_tolerance_m']
            joined = []
            for start,end in merged:
                if joined and start-joined[-1][1] <= gap_limit:
                    joined[-1] = (joined[-1][0],end)
                else:
                    joined.append((start,end))
            merged = joined
            if merged:
                if merged[0][0] <= end_limit:
                    merged[0] = (0.0, merged[0][1])
                if road.length-merged[-1][1] <= end_limit:
                    merged[-1] = (merged[-1][0], road.length)
            cursor = 0.0
            for start, end in [*merged, (road.length, road.length)]:
                if start-cursor > 1e-6:
                    clipped = substring(road, cursor, start).intersection(boundary)
                    if clipped.length > 1e-6:
                        yield oid, side, clipped
                cursor = max(cursor, end)
