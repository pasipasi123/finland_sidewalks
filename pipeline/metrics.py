"""Population-normalized indicators derived from already measured street lengths."""
import math

METRICS_VERSION = '1.1.0'
PER_CAPITA = {
    'shared_m_per_resident': 'shared',
    'segregated_m_per_resident': 'segregated',
    'unknown_m_per_resident': 'unknown',
}


def update_per_capita(result):
    """Enrich a municipal result in place; return whether any fields changed.

    Unknown segregation is deliberately excluded from both cycling indicators.
    The segregated walking length already belongs to the sidewalk total.
    Geometry provenance and its method version remain unchanged.
    """
    population = result['population']
    if not math.isfinite(population) or population <= 0:
        raise ValueError('Asukaskohtainen laskenta vaatii positiivisen väestöluvun')
    values = {'m_per_resident': result['total_km']}
    values.update({field: result['km'][kind] for field, kind in PER_CAPITA.items()})
    if any(not math.isfinite(length) or length < 0 for length in values.values()):
        raise ValueError('Pituuksien on oltava äärellisiä ja epänegatiivisia')
    metrics = {field: round(length * 1000 / population, 4) for field, length in values.items()}
    metrics['metrics_version'] = METRICS_VERSION
    changed = any(result.get(field) != value for field, value in metrics.items())
    result.update(metrics)
    return changed
