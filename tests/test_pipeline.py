import argparse
import csv
import json
import tempfile
import subprocess
import sys
import unittest
import sqlite3
import fiona
from contextlib import closing
from pathlib import Path
from shapely.geometry import LineString, box, shape
from pipeline.rules import category, sidewalk_sides, tag_rejection, reference_road
from pipeline.cli import measure, prepare, compute, publish, transform, TO_METRES, level
from pipeline.platforms import platform_access_ways
from pipeline.network import WalkingNetwork
from pipeline.export_gpkg import export_gpkg, line_geometry, properties
from pipeline.sync_gpkg import sync_gpkg
from pipeline.metrics import update_per_capita
from pipeline.refresh_metrics import refresh_gpkg
from pipeline.tagged import tagged_sidewalks
from pipeline.refresh_tagged import update_gpkg


class Metrics(unittest.TestCase):
    def test_units_categories_and_idempotence(self):
        result = {'population': 2000, 'total_km': 10,
                  'km': {'shared': 6, 'segregated': 2, 'unknown': 100}}
        self.assertTrue(update_per_capita(result))
        self.assertEqual(result['m_per_resident'], 5)
        self.assertEqual(result['shared_m_per_resident'], 3)
        self.assertEqual(result['segregated_m_per_resident'], 1)
        self.assertEqual(result['unknown_m_per_resident'], 50)
        self.assertFalse(update_per_capita(result))

    def test_invalid_or_missing_inputs_are_not_zero(self):
        for population in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                update_per_capita({'population': population})
        with self.assertRaises(KeyError):
            update_per_capita({'population': 10, 'total_km': 1, 'km': {'shared': 0}})


class TaggedCoverage(unittest.TestCase):
    def test_summary_mode_preserves_lengths_without_exporting_audit(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential',sidewalk='both'),
              way(2,[(0,8),(100,8)],highway='footway'),
              way(3,[(0,-8),(100,-8)],highway='cycleway',foot='designated',segregated='no')]
        boundary=box(-50,-50,150,50)
        expected,audit=measure(boundary,ways)
        actual,no_audit=measure(boundary,ways,collect_audit=False)
        self.assertEqual(actual,expected)
        self.assertGreater(len(audit),0)
        self.assertEqual(no_audit,[])
    def remaining(self, road, paths):
        return list(tagged_sidewalks([road], paths, box(-500,-500,500,500),20,level))

    def test_bent_sidewalk_has_no_buffer_cap_gaps(self):
        road=way(1,[(0,0),(100,0)],highway='residential',sidewalk='left')
        paths=[(LineString([a,b]),{}) for a,b in zip([(0,10),(30,12),(60,9)],[(30,12),(60,9),(100,10)])]
        self.assertEqual(self.remaining(road,paths),[])

    def test_direction_and_opposite_side(self):
        path=(LineString([(0,10),(100,10)]),{})
        for coords,side in [([(0,0),(100,0)],'left'), ([(100,0),(0,0)],'right')]:
            road=way(1,coords,highway='residential',sidewalk=side)
            self.assertEqual(self.remaining(road,[path]),[])
            road[1]['sidewalk']='both'
            rows=self.remaining(road,[path])
            self.assertEqual(len(rows),1)
            self.assertNotEqual(rows[0][1],side)
            self.assertAlmostEqual(rows[0][2].length,100)

    def test_real_unmapped_gap_and_grade_are_preserved(self):
        road=way(1,[(0,0),(100,0)],highway='residential',sidewalk='left')
        paths=[(LineString([(0,10),(40,10)]),{}),(LineString([(60,10),(100,10)]),{})]
        self.assertAlmostEqual(sum(g.length for _,_,g in self.remaining(road,paths)),20)
        self.assertAlmostEqual(sum(g.length for _,_,g in self.remaining(road,[(LineString([(0,10),(100,10)]),{'layer':'1'})])),100)
        long_road=way(1,[(0,0),(200,0)],highway='residential',sidewalk='left')
        almost_complete=[(LineString([(0,10),(90,10)]),{}),(LineString([(110,10),(200,10)]),{})]
        self.assertAlmostEqual(sum(g.length for _,_,g in self.remaining(long_road,almost_complete)),20)
        short_unmapped=way(1,[(0,0),(5,0)],highway='residential',sidewalk='left')
        self.assertAlmostEqual(sum(g.length for _,_,g in self.remaining(short_unmapped,[])),5)

    def test_shared_and_unknown_do_not_reappear_as_tagged_sidewalks(self):
        for segregation in ('no', None):
            tags={'highway':'cycleway','foot':'designated'}
            if segregation:tags['segregated']=segregation
            stats,_=measure(box(-10,-50,110,50),[way(1,[(0,0),(100,0)],highway='residential',sidewalk='left'),way(2,[(0,8),(100,8)],**tags)])
            self.assertEqual(stats['tagged'],0)
            self.assertAlmostEqual(stats['shared' if segregation else 'unknown'],100)

    def test_saved_audit_paths_reproduce_direct_measure(self):
        boundary=box(10,-50,90,50)
        ways=[way(1,[(0,0),(100,0)],highway='residential',sidewalk='both'),
              way(2,[(0,8),(60,8)],highway='footway',footway='sidewalk'),
              way(3,[(0,-8),(100,-8)],highway='cycleway',foot='designated',segregated='no')]
        stats,audit=measure(boundary,ways)
        tags={oid:t for oid,t,_ in ways}
        paths=[(transform(TO_METRES,shape(f['geometry'])),tags[f['properties']['osm_id']]) for f in audit if f['properties']['category']!='tagged']
        refreshed=sum(g.length for _,_,g in tagged_sidewalks([ways[0]],paths,boundary,20,level))
        self.assertGreater(stats['tagged'],20)
        self.assertAlmostEqual(refreshed,stats['tagged'],places=5)

    def test_sukkavartaankatu_has_no_tagged_fragments(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/tampere_tagged_overlap.json').read_text(encoding='utf-8'))
        r=fixture['road']
        paths=[(shape(p['geometry']),p['tags']) for p in fixture['paths']]
        road=(r['id'],r['tags'],shape(r['geometry']))
        self.assertEqual(list(tagged_sidewalks([road],paths,road[2].buffer(100),20,level)),[])

def way(oid, coords, **tags):
    if tags.get('highway') in {'footway','cycleway','path'}:
        tags.setdefault('surface','asphalt')
    return oid,tags,LineString(coords)

class Rules(unittest.TestCase):
    def test_bus_exception_keeps_physical_street_reference(self):
        self.assertTrue(reference_road({'highway':'secondary','access':'no','bus':'yes','foot':'no'}))
        self.assertFalse(reference_road({'highway':'secondary','access':'no','bus':'no'}))
        self.assertFalse(reference_road({'highway':'secondary','access':'private','bus':'yes'}))
    def test_destination_access_respects_walking_override(self):
        self.assertEqual(tag_rejection({'highway':'footway','access':'destination'}),'jalankulku_vain_maaranpaahan')
        self.assertEqual(tag_rejection({'highway':'footway','foot':'destination','access':'yes'}),'jalankulku_vain_maaranpaahan')
        for foot in ['yes','designated','permissive','official']:
            self.assertEqual(category({'highway':'footway','access':'destination','foot':foot}),'footway')
        self.assertEqual(category({'highway':'footway','motor_vehicle':'destination'}),'footway')
        self.assertEqual(category({'highway':'residential','access':'destination','sidewalk':'both'}),'road')

    def test_sides_and_overrides(self):
        self.assertEqual(sidewalk_sides({'sidewalk':'both','sidewalk:left':'separate'}),(False,True))
        self.assertEqual(sidewalk_sides({'sidewalk':'left'}),(True,False))
        self.assertEqual(sidewalk_sides({'sidewalk:both':'yes'}),(True,True))
        self.assertEqual(sidewalk_sides({'sidewalk':'separate'}),(False,False))

    def test_combined_and_segregated(self):
        self.assertEqual(category({'highway':'cycleway','foot':'designated','segregated':'yes','surface':'asphalt'}),'segregated')
        self.assertEqual(category({'highway':'footway','bicycle':'designated','segregated':'no','foot':'designated'}),'shared')
        self.assertEqual(category({'highway':'cycleway','foot':'designated'}),'unknown')
        self.assertIsNone(category({'highway':'footway','access':'private'}))
        self.assertEqual(category({'highway':'footway','bicycle':'designated','segregated':'no'}),'shared')
        self.assertEqual(category({'highway':'footway','bicycle':'designated','segregated':'yes','surface':'paved'}),'segregated')

    def test_hard_surface_and_missing_sidewalk_tag(self):
        self.assertEqual(category({'highway':'footway','surface':'paving_stones'}),'footway')
        for surface in ['compacted','gravel','fine_gravel','ground','unpaved','asphalt;compacted']:
            self.assertIsNone(category({'highway':'footway','surface':surface}))
        self.assertIsNone(tag_rejection({'highway':'footway'}))
        self.assertEqual(category({'highway':'footway'}),'footway')
        exported=properties(36729304,{'highway':'footway','is_sidepath':'yes'})
        self.assertIsNone(exported['surface'])
        self.assertEqual(exported['pinnan_tila'],'oletus_asfaltti')
        self.assertEqual(exported['laskenta_pinta'],'asphalt')
        self.assertIsNone(category({'highway':'path','foot':'designated','surface':'asphalt'}))
        self.assertIsNone(category({'highway':'cycleway','foot':'designated','segregated':'yes','surface':'asphalt','footway:surface':'compacted'}))
        self.assertEqual(category({'highway':'footway','surface':'paving_stones','lit':'yes'}),'footway')

class Geometry(unittest.TestCase):
    def test_nasinlinnankatu_two_sided_offsets_are_complete(self):
        f=json.loads((Path(__file__).parent/'fixtures/tampere_nasinlinnankatu_offsets.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        platforms=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['platforms']]
        _,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways,platforms=platforms)
        counted=sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==197195792)
        self.assertAlmostEqual(counted,next(g.length for oid,t,g in ways if oid==197195792),delta=.02)

    def test_two_sided_midblock_repair_stays_in_standard_street_corridor(self):
        for offset,complete in [(18,True),(22,False)]:
            ways=[way(1,[(0,0),(200,0)],highway='residential'),
                  way(2,[(20,8),(60,8),(62,offset),(68,offset),(70,8),(150,8)],highway='footway')]
            stats,_=measure(box(-20,-20,220,50),ways)
            self.assertAlmostEqual(stats['footway'],ways[1][2].length if complete else 120,delta=.01)

    def test_tuulensuu_platform_access_does_not_hide_street_sidewalks(self):
        f=json.loads((Path(__file__).parent/'fixtures/tampere_tuulensuu_platforms.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        platforms=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['platforms']]
        excluded={};_,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways,platforms=platforms,platform_exclusions=excluded)
        for oid in [553272448,67295429]:
            counted=sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==oid)
            self.assertAlmostEqual(counted,next(g.length for i,t,g in ways if i==oid),delta=.03)
        for oid,pid in [(1538890560,849224795),(1538890557,849224794)]:
            self.assertEqual(excluded[oid],[pid])
            self.assertNotIn(oid,{row['properties']['osm_id'] for row in audit})

    def test_platform_access_requires_terminal_node_at_mapped_area(self):
        area=(10,{'public_transport':'platform'},box(40,3,70,7))
        base=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,10),(100,10)],highway='footway'),way(3,[(0,5),(0,10)],highway='footway')]
        path=way(4,[(0,5),(40,5)],highway='footway')
        ways=base+[path]
        self.assertEqual(platform_access_ways(ways,[area],WalkingNetwork(ways,level)),{4:[10]})
        for alternate in [way(4,[(0,5),(39.5,5)],highway='footway'),way(4,[(0,5),(40,5)],highway='footway',footway='sidewalk')]:
            ways=base+[alternate]
            self.assertEqual(platform_access_ways(ways,[area],WalkingNetwork(ways,level)),{})

    def test_through_footway_and_other_level_are_not_platform_access(self):
        ways=[way(1,[(0,5),(40,5)],highway='footway'),way(2,[(40,5),(100,5)],highway='footway')]
        area=(10,{'public_transport':'platform'},box(40,3,70,7))
        self.assertEqual(platform_access_ways(ways,[area],WalkingNetwork(ways,level)),{})
        ways=[way(1,[(0,5),(40,5)],highway='footway')]
        raised=(10,{'public_transport':'platform','level':'1'},area[2])
        self.assertEqual(platform_access_ways(ways,[raised],WalkingNetwork(ways,level)),{})
    def test_reported_tampere_bus_street_sidewalk(self):
        f=json.loads((Path(__file__).parent/'fixtures/tampere_insinoorinkatu_bus.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        _,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways)
        self.assertGreater(sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==1144968837),120)
        self.assertTrue(reference_road(next(tags for oid,tags,g in ways if oid==794251023)))

    def test_reported_tampere_corner_chains_and_long_way_gap(self):
        f=json.loads((Path(__file__).parent/'fixtures/tampere_corner_gaps.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        _,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways)
        lengths={oid:sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==oid) for oid in [42274329,88200539,1095271885]}
        self.assertGreater(lengths[42274329],594)
        for oid in [88200539,1095271885]:
            self.assertAlmostEqual(lengths[oid],next(g.length for i,t,g in ways if i==oid),delta=.02)

    def test_reported_hameenkatu_sidewalks(self):
        f=json.loads((Path(__file__).parent/'fixtures/tampere_hameenkatu_gaps.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        _,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways)
        for oid in [379163743,592800179]:
            counted=sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==oid)
            self.assertAlmostEqual(counted,next(g.length for i,t,g in ways if i==oid),delta=.03)

    def test_bus_only_street_has_separate_sidewalk(self):
        ways=[way(1,[(0,0),(100,0)],highway='secondary',access='no',bus='yes',foot='no'),
              way(2,[(0,8),(100,8)],highway='footway')]
        stats,_=measure(box(-20,-20,120,40),ways)
        self.assertAlmostEqual(stats['footway'],100)
    def test_reported_short_corner_link_between_real_sidewalks(self):
        f=json.loads((Path(__file__).parent/'fixtures/oulu_corner_link.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        _,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways)
        length=sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==1201123082)
        self.assertAlmostEqual(length,13.757,delta=0.003)

    def test_reported_sidewalk_junction_ends_are_complete(self):
        f=json.loads((Path(__file__).parent/'fixtures/oulu_sidewalk_ends.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        _,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways)
        for oid in [496915707,58521570,1201123080,1228692226]:
            raw=next(geom.length for i,tags,geom in ways if i==oid)
            counted=sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==oid)
            self.assertAlmostEqual(counted,raw,delta=0.02)

    def test_crossing_can_anchor_short_link_also_between_road_junctions(self):
        for intersection,expected in [(True,7.729),(False,7.729)]:
            ways=[way(1,[(0,0),(100,0),(200,0)],highway='residential'),
                  way(2,[(20,8),(95,8)],highway='footway'),
                  way(3,[(95,8),(99,9),(101,12)],highway='footway'),
                  way(5,[(101,12),(110,12)],highway='footway',footway='crossing')]
            if intersection:ways.append(way(4,[(100,0),(100,100)],highway='residential'))
            _,audit=measure(box(-20,-20,220,120),ways)
            length=sum(row['properties']['length_m'] for row in audit if row['properties']['osm_id']==3)
            self.assertAlmostEqual(length,expected,delta=.002)
            self.assertNotIn(5,{row['properties']['osm_id'] for row in audit})

    def test_crossing_proximity_without_shared_node_does_not_support_link(self):
        ways=[way(1,[(0,0),(100,0),(200,0)],highway='residential'),
              way(2,[(100,0),(100,100)],highway='residential'),
              way(3,[(20,8),(95,8)],highway='footway'),
              way(4,[(95,8),(99,9),(101,12)],highway='footway',footway='sidewalk'),
              way(5,[(101.1,12),(110,12)],highway='footway',footway='crossing')]
        _,audit=measure(box(-20,-20,220,120),ways)
        self.assertNotIn(4,{row['properties']['osm_id'] for row in audit})

    def test_unlabelled_one_ended_corner_spur_has_no_short_stub_exception(self):
        ways=[way(1,[(0,0),(100,0),(200,0)],highway='residential'),
              way(2,[(100,0),(100,100)],highway='residential'),
              way(3,[(20,8),(95,8)],highway='footway'),
              way(4,[(95,8),(99,9),(101,12)],highway='footway')]
        _,audit=measure(box(-20,-20,220,120),ways)
        self.assertNotIn(4,{row['properties']['osm_id'] for row in audit})

    def test_reported_isolated_estate_branch(self):
        f=json.loads((Path(__file__).parent/'fixtures/oulu_isolated_estate_branch.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        rejected={};_,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways,rejections=rejected)
        self.assertNotIn(115094353,{row['properties']['osm_id'] for row in audit})
        self.assertEqual(rejected['115094353'],'irrallinen_haara_hylatysta_reitista')

    def test_isolated_estate_branch_cannot_support_itself_via_way_splitting(self):
        ways=[way(1,[(0,0),(300,0)],highway='residential'),
              way(2,[(100,0),(100,10),(100,50)],highway='footway'),
              way(3,[(100,10),(130,10)],highway='footway'),way(4,[(130,10),(170,10)],highway='footway')]
        rejected={};stats,_=measure(box(-10,-10,310,100),ways,rejections=rejected)
        self.assertEqual(stats['footway'],0)
        for oid in [3,4]:self.assertEqual(rejected[str(oid)],'irrallinen_haara_hylatysta_reitista')

    def test_excursion_sampling_checks_between_original_vertices(self):
        ways=[way(1,[(-100,0),(0,0),(0,60),(100,60),(100,0),(200,0)],highway='residential'),
              way(2,[(0,8),(100,8)],highway='footway')]
        rejected={};stats,_=measure(box(-150,-50,250,100),ways,rejections=rejected)
        self.assertEqual(stats['footway'],0)
        self.assertEqual(rejected['2'],'ajoradasta_poikkeava_kokonaisreitti')

    def test_sidewalk_no_blocks_inference_without_using_a_farther_road(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential',sidewalk='no'),
              way(2,[(0,18),(100,18)],highway='residential'),
              way(3,[(0,5),(100,5)],highway='footway')]
        rejected={};stats,_=measure(box(-20,-30,120,50),ways,rejections=rejected)
        self.assertEqual(stats['footway'],0)
        self.assertEqual(rejected['3'],'ajoradan_puolella_ei_jalkakaytavaa')

    def test_sidewalk_no_honors_side_specific_override(self):
        ways=[way(1,[(0,0),(100,0)],**{'highway':'residential','sidewalk':'no','sidewalk:left':'separate'}),
              way(2,[(0,8),(100,8)],highway='footway'),way(3,[(0,-8),(100,-8)],highway='footway')]
        stats,audit=measure(box(-20,-30,120,30),ways)
        self.assertAlmostEqual(stats['footway'],100)
        self.assertEqual({f['properties']['osm_id'] for f in audit},{2})

    def test_explicit_sidewalk_is_stronger_than_conflicting_road_no(self):
        for explicit in [{'footway':'sidewalk'},{'is_sidepath':'yes'}]:
            ways=[way(1,[(0,0),(100,0)],highway='residential',sidewalk='no'),
                  way(2,[(0,8),(100,8)],highway='footway',**explicit)]
            stats,_=measure(box(-20,-30,120,30),ways)
            self.assertAlmostEqual(stats['footway'],100)

    def test_reported_estate_detours(self):
        f=json.loads((Path(__file__).parent/'fixtures/oulu_estate_detours.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        rejected={};_,audit=measure(transform(TO_METRES,shape(f['boundary'])),ways,rejections=rejected)
        included={row['properties']['osm_id'] for row in audit}
        for oid in [133019393,130751536,1206626750]:self.assertNotIn(oid,included)
        self.assertEqual(rejected['133019393'],'ajoradalta_sivuun_ja_takaisin')
        self.assertEqual(rejected['130751536'],'ajoradalta_sivuun_ja_takaisin')
        self.assertEqual(rejected['1206626750'],'sisaverkon_paattyva_katuosuma')

    def test_estate_detour_across_way_ids(self):
        ways=[way(1,[(-100,0),(0,0),(100,0),(300,0)],highway='residential'),
              way(2,[(0,0),(0,14)],highway='footway'),
              way(3,[(0,14),(100,14)],highway='footway'),
              way(4,[(100,14),(100,0)],highway='footway')]
        stats,_=measure(box(-150,-50,350,100),ways)
        self.assertEqual(stats['footway'],0)

    def test_real_sidewalk_between_junctions_keeps_road_connections(self):
        ways=[way(1,[(-100,0),(0,0),(100,0),(300,0)],highway='residential'),
              way(2,[(0,-50),(0,0),(0,50)],highway='residential'),
              way(3,[(100,-50),(100,0),(100,50)],highway='residential'),
              way(4,[(0,0),(0,14),(100,14),(100,0)],highway='footway')]
        stats,_=measure(box(-150,-100,350,100),ways)
        self.assertGreaterEqual(stats['footway'],100)

    def test_interior_dead_end_cannot_donate_a_street_side_fragment(self):
        ways=[way(1,[(0,0),(300,0)],highway='residential'),
              way(2,[(100,50),(100,10),(170,10)],highway='footway')]
        stats,_=measure(box(-10,-10,310,100),ways)
        self.assertEqual(stats['footway'],0)

    def test_destination_path_is_not_counted_or_a_blocker(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),
              way(970197335,[(0,5),(100,5)],highway='footway',access='destination'),
              way(3,[(0,10),(100,10)],highway='footway')]
        rejected={};stats,audit=measure(box(-10,-10,110,30),ways,rejections=rejected)
        self.assertAlmostEqual(stats['footway'],100)
        self.assertEqual(rejected['970197335'],'jalankulku_vain_maaranpaahan')
        self.assertEqual({f['properties']['osm_id'] for f in audit},{3})

    def test_reported_cemetery_network_spur(self):
        f=json.loads((Path(__file__).parent/'fixtures/oulu_cemetery_network.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in f['ways']]
        rejected={};_,a=measure(transform(TO_METRES,shape(f['boundary'])),ways,rejections=rejected)
        self.assertNotIn(1144437799,{row['properties']['osm_id'] for row in a})
        self.assertEqual(rejected['1144437799'],'sisaverkon_paattyva_katuosuma')

    def test_interior_network_terminal_spur_across_way_ids(self):
        ways=[way(1,[(0,0),(200,0)],highway='residential'),way(2,[(60,45),(60,8),(90,8)],highway='footway'),way(3,[(90,8),(130,8)],highway='footway'),way(4,[(30,45),(60,45),(90,45)],highway='footway')]
        stats,_=measure(box(-50,-50,250,150),ways)
        self.assertEqual(stats['footway'],0)

    def test_tangent_estate_branch_does_not_poison_street_sidewalk(self):
        ways=[way(1,[(0,0),(200,0)],highway='residential'),way(2,[(30,8),(100,8),(170,8)],highway='footway'),way(3,[(100,8),(100,45)],highway='footway'),way(4,[(70,45),(100,45),(130,45)],highway='footway')]
        stats,_=measure(box(-50,-50,250,150),ways)
        self.assertAlmostEqual(stats['footway'],140)

    def test_street_endpoint_alone_does_not_rescue_estate_route(self):
        ways=[way(1,[(0,0),(130,0)],highway='residential'),way(2,[(60,45),(60,8),(130,8)],highway='footway'),way(3,[(30,45),(60,45),(90,45)],highway='footway')]
        stats,_=measure(box(-50,-50,250,150),ways)
        self.assertEqual(stats['footway'],0)

    def test_deep_excursion_rejects_whole_route_across_way_boundaries(self):
        ways=[way(1,[(-100,0),(300,0)],highway='residential'),
              way(2,[(60,10),(100,10),(100,50)],highway='footway'),
              way(3,[(100,50),(160,50),(160,10)],highway='footway'),
              way(4,[(160,10),(220,10)],highway='footway')]
        rejected={};stats,_=measure(box(-150,-50,350,100),ways,rejections=rejected)
        self.assertEqual(stats['footway'],0)
        for oid in [2,3,4]:self.assertEqual(rejected[str(oid)],'ajoradasta_poikkeava_kokonaisreitti')

    def test_walking_junction_separates_street_spine_from_estate_access(self):
        ways=[way(1,[(-100,0),(300,0)],highway='residential'),
              way(2,[(30,10),(100,10),(200,10)],highway='footway'),
              way(3,[(100,10),(100,50)],highway='footway')]
        stats,_=measure(box(-150,-50,350,100),ways)
        self.assertAlmostEqual(stats['footway'],170)

    def test_reported_zigzag_property_path(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/oulu_zigzag_case.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in fixture['ways']]
        rejected={}
        _,audit=measure(transform(TO_METRES,shape(fixture['boundary'])),ways,rejections=rejected)
        self.assertNotIn(1272508397,{f['properties']['osm_id'] for f in audit})
        self.assertEqual(rejected['1272508397'],'jyrkat_kaanteet_katkaisevat_jakson')

    def test_zigzag_property_path_cannot_merge_matches_to_two_streets(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,0),(0,100)],highway='residential'),way(3,[(10,10),(12,10),(12,16),(22,16),(22,17)],highway='footway')]
        stats,_=measure(box(-50,-50,150,150),ways)
        self.assertEqual(stats['footway'],0)

    def test_genuine_street_corner_keeps_both_long_legs(self):
        ways=[way(1,[(0,0),(60,0)],highway='residential'),way(2,[(50,0),(50,60)],highway='residential'),way(3,[(0,8),(42,8),(42,50)],highway='footway')]
        stats,_=measure(box(-50,-50,150,150),ways)
        self.assertAlmostEqual(stats['footway'],84)

    def test_kirkkokatu_footway_with_implicit_walking_is_shared(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/kirkkokatu_parking_case.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in fixture['ways']]
        _,audit=measure(transform(TO_METRES,shape(fixture['boundary'])),ways)
        rows=[f['properties'] for f in audit if f['properties']['osm_id']==29107579]
        self.assertGreater(sum(f['length_m'] for f in rows),250)
        self.assertEqual({f['category'] for f in rows},{'shared'})

    def test_parking_aisle_is_not_a_walking_barrier(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,8),(100,8)],highway='service',service='parking_aisle'),way(3,[(0,18),(100,18)],highway='footway')]
        stats,_=measure(box(-50,-50,150,50),ways)
        self.assertAlmostEqual(stats['footway'],100)

    def test_reported_outer_property_footway(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/oulu_corridor_case.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in fixture['ways']]
        rejected={};removed=[]
        _,audit=measure(transform(TO_METRES,shape(fixture['boundary'])),ways,rejections=rejected,corridor_exclusions=removed)
        self.assertNotIn(1209361514,{f['properties']['osm_id'] for f in audit})
        self.assertEqual(rejected['1209361514'],'lahempi_jalankulkuvayla')
        self.assertTrue(any(row['osm_id']==1209361514 and 41672560 in row['blockers'] for row in removed))

    def test_non_countable_inner_walking_route_still_blocks(self):
        for inner in [way(2,[(0,7),(100,7)],highway='footway',surface='compacted'),way(2,[(0,7),(100,7)],highway='path',foot='designated',bicycle='designated',segregated='no')]:
            ways=[way(1,[(0,0),(100,0)],highway='residential'),inner,way(3,[(0,14),(100,14)],highway='footway')]
            stats,_=measure(box(-50,-50,150,50),ways)
            self.assertEqual(stats['footway'],0)

    def test_inner_combined_route_blocks_outer_footway(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,7),(100,7)],highway='cycleway',foot='designated',segregated='no'),way(3,[(0,14),(100,14)],highway='footway')]
        rejected={};removed=[]
        stats,_=measure(box(-50,-50,150,50),ways,rejections=rejected,corridor_exclusions=removed)
        self.assertEqual(stats['footway'],0)
        self.assertAlmostEqual(stats['shared'],100)
        self.assertEqual(rejected['3'],'lahempi_jalankulkuvayla')
        self.assertTrue(all(row['blockers']==[2] for row in removed))

    def test_unknown_segregation_also_blocks_outer_footway(self):
        ways=[way(1,[(100,0),(0,0)],highway='residential'),way(2,[(0,7),(100,7)],highway='cycleway',foot='designated'),way(3,[(0,14),(100,14)],highway='footway')]
        stats,_=measure(box(-50,-50,150,50),ways)
        self.assertEqual(stats['footway'],0)
        self.assertAlmostEqual(stats['unknown'],100)

    def test_cycleway_without_walking_designation_does_not_block(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,7),(100,7)],highway='cycleway',foot='no'),way(3,[(0,14),(100,14)],highway='footway')]
        stats,_=measure(box(-50,-50,150,50),ways)
        self.assertAlmostEqual(stats['footway'],100)

    def test_only_inner_same_side_footway_survives(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,7),(100,7)],highway='footway'),way(3,[(0,14),(100,14)],highway='footway'),way(4,[(0,-14),(100,-14)],highway='footway')]
        stats,audit=measure(box(-50,-50,150,50),ways)
        self.assertAlmostEqual(stats['footway'],200)
        self.assertNotIn(3,{f['properties']['osm_id'] for f in audit})

    def test_shadow_stops_at_blockers_end(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,7),(50,7)],highway='footway'),way(3,[(0,14),(100,14)],highway='footway')]
        _,audit=measure(box(-50,-50,150,50),ways)
        self.assertAlmostEqual(sum(f['properties']['length_m'] for f in audit if f['properties']['osm_id']==3),50)

    def test_living_street_and_nearby_footway_are_excluded(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,8),(100,8)],highway='living_street',sidewalk='both'),way(3,[(0,12),(100,12)],highway='footway')]
        stats,_=measure(box(-50,-50,150,50),ways)
        self.assertEqual(stats['footway']+stats['tagged'],0)

    def test_parallel_streets_do_not_shadow_each_others_sidewalks(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,30),(100,30)],highway='residential'),way(3,[(0,7),(100,7)],highway='footway'),way(4,[(0,23),(100,23)],highway='footway')]
        stats,_=measure(box(-50,-50,150,50),ways)
        self.assertAlmostEqual(stats['footway'],200)

    def test_reported_oulu_sidewalks(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/oulu_user_cases.json').read_text(encoding='utf-8'))
        ways=[(w['id'],w['tags'],transform(TO_METRES,shape(w['geometry']))) for w in fixture['ways']]
        _,audit=measure(transform(TO_METRES,shape(fixture['boundary'])),ways)
        lengths={oid:sum(f['properties']['length_m'] for f in audit if f['properties']['osm_id']==oid and f['properties']['category']=='footway') for oid in [47110040,50118180,50118181,36729304,89930891]}
        self.assertGreater(lengths[47110040],200)
        self.assertGreater(lengths[50118180],80)
        self.assertGreater(lengths[50118181],100)
        self.assertGreater(lengths[36729304],85)
        self.assertGreater(lengths[89930891],450)

    def test_export_omits_degenerate_geometry(self):
        self.assertIsNone(line_geometry(LineString([(0,0),(0,0)])))

    def test_both_sides_clipped_to_municipality(self):
        stats,_=measure(box(0,-50,50,50),[way(1,[(-50,0),(100,0)],highway='residential',sidewalk='both')])
        self.assertAlmostEqual(stats['tagged'],100)

    def test_proximity_direction_and_level(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,10),(100,10)],highway='footway'),way(3,[(0,40),(100,40)],highway='footway'),way(4,[(50,-15),(50,15)],highway='footway'),way(5,[(0,5),(100,5)],highway='footway',bridge='yes')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertAlmostEqual(stats['footway'],100)

    def test_deduplication_respects_opposite_side(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential',sidewalk='both'),way(2,[(0,10),(100,10)],highway='footway')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertAlmostEqual(stats['tagged'],100)
        self.assertAlmostEqual(stats['footway'],100)

    def test_shared_not_counted_as_footway(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,10),(100,10)],highway='cycleway',foot='designated',segregated='no')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertAlmostEqual(stats['shared'],100)
        self.assertEqual(stats['segregated']+stats['footway']+stats['tagged'],0)

    def test_nearby_fragment_of_deep_estate_route_is_rejected(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(0,10),(50,10),(50,50),(100,50)],highway='footway')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertEqual(stats['footway'],0)

    def test_short_property_spur_is_excluded(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),way(2,[(30,8),(38,8)],highway='footway')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertEqual(stats['footway'],0)

    def test_missing_surface_is_assumed_asphalt_but_compacted_is_excluded(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential'),
              (2,{'highway':'footway'},LineString([(0,8),(100,8)])),
              way(3,[(0,-8),(100,-8)],highway='footway',surface='compacted')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertAlmostEqual(stats['footway'],100)
        self.assertAlmostEqual(stats['assumed_asphalt'],100)

    def test_carriageway_foot_ban_does_not_exclude_sidewalk(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential',foot='no'),way(2,[(0,8),(100,8)],highway='footway')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertAlmostEqual(stats['footway'],100)

    def test_access_restriction_with_bus_exception_remains_reference(self):
        ways=[way(1,[(0,0),(100,0)],highway='residential',access='no',psv='yes'),way(2,[(0,8),(100,8)],highway='footway')]
        stats,_=measure(box(-100,-100,200,200),ways)
        self.assertAlmostEqual(stats['footway'],100)

class Integration(unittest.TestCase):
    def test_publish_rejects_old_method_before_labelling_output(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
            root=Path(temp)
            (root/'999.json').write_text(json.dumps({'signature':'old','method_version':'0.0.0'}),encoding='utf-8')
            with self.assertRaises(ValueError):
                publish(argparse.Namespace(results=str(root),output=str(root/'published.json')))
            self.assertFalse((root/'published.json').exists())

    def test_osm_to_static_dashboard(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
            root=Path(temp)
            pbf=root/'tiny.osm'
            pbf.write_text('''<osm version="0.6"><node id="1" lat="65" lon="25"/><node id="2" lat="65" lon="25.002"/><node id="3" lat="64.99" lon="24.99"/><node id="4" lat="64.99" lon="25.01"/><node id="5" lat="65.01" lon="25.01"/><node id="6" lat="65.01" lon="24.99"/><way id="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="sidewalk" v="both"/></way><way id="2"><nd ref="3"/><nd ref="4"/><nd ref="5"/><nd ref="6"/><nd ref="3"/></way><relation id="1"><member type="way" ref="2" role="outer"/><tag k="type" v="boundary"/><tag k="boundary" v="administrative"/><tag k="admin_level" v="8"/><tag k="ref" v="999"/><tag k="name" v="Testikunta"/></relation></osm>''',encoding='utf-8')
            cache=root/'cache.db'; boundaries=root/'boundaries.json'; pop=root/'pop.csv'; output=root/'results'
            subprocess.run([sys.executable,'-m','pipeline.cli','prepare','--cache',str(cache),'--pbf',str(pbf),'--boundaries',str(boundaries),'--osm-date','2026-01-01'],check=True,capture_output=True)
            pop.write_text('code,population,date,source\n999,1000,2025-12-31,test-fixture\n',encoding='utf-8')
            args=argparse.Namespace(cache=str(cache),boundaries=str(boundaries),population=str(pop),codes='999',output=str(output),force=False,distance=20)
            compute(args)
            publish(argparse.Namespace(results=str(output),output=str(root/'web.json')))
            data=json.loads((root/'web.json').read_text(encoding='utf-8'))
            row=data['municipalities'][0]
            self.assertFalse(data['demo']); self.assertEqual(row['rank_total_km'],1)
            self.assertTrue(.18 < row['total_km'] < .20)
            self.assertEqual(row['m_per_resident'],round(row['total_km'],4))
            self.assertEqual(row['shared_m_per_resident'],0)
            self.assertEqual(row['segregated_m_per_resident'],0)
            self.assertEqual(row['rank_shared_m_per_resident'],1)
            self.assertEqual(row['rank_segregated_m_per_resident'],1)
            self.assertTrue(row['map_path'].startswith('M'))
            compact_args=argparse.Namespace(results=str(output),output=str(root/'table.json'),table_only=True,csv_output=str(root/'table.csv'),expected_count=1)
            publish(compact_args)
            compact=json.loads((root/'table.json').read_text(encoding='utf-8'))
            self.assertNotIn('map_path',compact['municipalities'][0])
            self.assertNotIn('geometry',compact['municipalities'][0])
            self.assertEqual(compact['expected_count'],1)
            self.assertEqual(compact['osm']['osm_date'],row['osm']['osm_date'])
            with (root/'table.csv').open(encoding='utf-8-sig',newline='') as stream:
                csv_row=next(csv.DictReader(stream))
            self.assertEqual(float(csv_row['sidewalks_m_per_resident']),row['m_per_resident'])
            self.assertEqual(csv_row['unknown_m_per_resident'],'0.0')
            compact_args.expected_count=2
            with self.assertRaises(ValueError):
                publish(compact_args)
            gpkg=root/'inspection.gpkg'
            manifest=export_gpkg(output/'999.json',output/'999.segments.geojson',cache,gpkg)
            self.assertGreater(manifest['jalkakaytavat_ajoratatagit'],0)
            with closing(sqlite3.connect(gpkg)) as check:
                self.assertEqual(check.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(check.execute('SELECT COUNT(*) FROM gpkg_geometry_columns WHERE srs_id=3067').fetchone()[0],8)
                length=check.execute('SELECT SUM(pituus_m) FROM jalkakaytavat_ajoratatagit').fetchone()[0]
                self.assertAlmostEqual(length/1000,row['total_km'],places=5)
            # Simulate an older export, keep a reader open, and migrate in place.
            with closing(sqlite3.connect(gpkg)) as old:
                old.execute('ALTER TABLE kuntaraja DROP COLUMN yhdistetty_m_asukas')
                old.execute('ALTER TABLE kuntaraja DROP COLUMN eroteltu_m_asukas')
                old.commit()
            inode = gpkg.stat().st_ino
            result = json.loads((output/'999.json').read_text(encoding='utf-8'))
            with closing(sqlite3.connect(gpkg)) as reader:
                geom_before = reader.execute('SELECT geom FROM kuntaraja').fetchone()[0]
                refresh_gpkg(gpkg, result)
                self.assertEqual(reader.execute('SELECT yhdistetty_m_asukas,eroteltu_m_asukas FROM kuntaraja').fetchone(),(0,0))
                self.assertEqual(reader.execute('SELECT geom FROM kuntaraja').fetchone()[0],geom_before)
                mismatch = dict(result, code='998')
                with self.assertRaises(ValueError):
                    refresh_gpkg(gpkg, mismatch)
            self.assertEqual(gpkg.stat().st_ino,inode)
            with closing(sqlite3.connect(cache)) as source:
                tags_by_id={oid:json.loads(tags) for oid,tags in source.execute('SELECT id,tags FROM ways')}
            tagged=[f for f in json.loads((output/'999.segments.geojson').read_text(encoding='utf-8'))['features'] if f['properties']['category']=='tagged']
            with closing(sqlite3.connect(gpkg)) as reader:
                geometry_before=reader.execute('SELECT geom FROM kuntaraja').fetchone()[0]
                update_gpkg(gpkg,result,result,tagged,tags_by_id)
                self.assertEqual(reader.execute('SELECT COUNT(*) FROM jalkakaytavat_ajoratatagit').fetchone()[0],len(tagged))
                self.assertEqual(reader.execute('SELECT geom FROM kuntaraja').fetchone()[0],geometry_before)
                self.assertAlmostEqual(reader.execute('SELECT SUM(mukaan_m) FROM osm_ajoradat').fetchone()[0],sum(f['properties']['length_m'] for f in tagged))
            with fiona.open(gpkg,layer='jalkakaytavat_ajoratatagit') as features:
                self.assertEqual(features.crs.to_epsg(),3067)
                self.assertAlmostEqual(sum(shape(f['geometry']).length for f in features),result['km']['tagged']*1000,places=3)
            self.assertEqual(gpkg.stat().st_ino,inode)
            # A normal resumed compute must also enrich old results without measuring again.
            legacy = {key:value for key,value in result.items() if key not in
                      {'shared_m_per_resident','segregated_m_per_resident','metrics_version'}}
            (output/'999.json').write_text(json.dumps(legacy),encoding='utf-8')
            compute(args)
            self.assertEqual(json.loads((output/'999.json').read_text(encoding='utf-8')),result)
            before=(output/'999.json').stat().st_mtime_ns
            compute(args)
            self.assertEqual(before,(output/'999.json').stat().st_mtime_ns)
            staged=root/'staged.gpkg'
            export_gpkg(output/'999.json',output/'999.segments.geojson',cache,staged)
            with closing(sqlite3.connect(staged)) as source:
                source.execute('ALTER TABLE laskentatiedot ADD COLUMN test_note TEXT')
                source.execute("UPDATE laskentatiedot SET arvo='updated',test_note='new column' WHERE avain='kunta'")
                source.commit()
            with closing(sqlite3.connect(gpkg)) as reader:
                self.assertNotEqual(reader.execute("SELECT arvo FROM laskentatiedot WHERE avain='kunta'").fetchone()[0],'updated')
                sync_gpkg(staged,gpkg,root/'backup.gpkg')
                self.assertEqual(reader.execute("SELECT arvo,test_note FROM laskentatiedot WHERE avain='kunta'").fetchone(),('updated','new column'))

if __name__=='__main__':
    unittest.main()
