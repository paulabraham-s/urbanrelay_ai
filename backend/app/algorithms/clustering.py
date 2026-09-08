"""DBSCAN clustering (pure Python, dependency-free) used by the Delivery Wave agent.

Points are (lat, lng) tuples. A simple grid index bounds neighbour lookups.
"""

from app.algorithms.geo import haversine_m

_DEG_PER_M = 1.0 / 111_000.0


def _bucket_of(lat: float, lng: float, eps_m: float) -> tuple[int, int]:
    deg = eps_m * _DEG_PER_M
    return int(lat / deg), int(lng / deg)


def dbscan(points: list[tuple[float, float]], eps_m: float, min_pts: int = 3) -> list[int]:
    """Return cluster labels (-1 = noise) for each point."""
    n = len(points)
    labels = [-1] * n
    if n == 0:
        return labels

    buckets: dict[tuple[int, int], list[int]] = {}
    for i, (lat, lng) in enumerate(points):
        buckets.setdefault(_bucket_of(lat, lng, eps_m), []).append(i)

    def neighbors(i: int) -> list[int]:
        lat, lng = points[i]
        bx, by = _bucket_of(lat, lng, eps_m)
        result: list[int] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in buckets.get((bx + dx, by + dy), ()):
                    if j != i and haversine_m(lat, lng, *points[j]) <= eps_m:
                        result.append(j)
        return result

    cluster_id = 0
    for i in range(n):
        if labels[i] != -1:
            continue
        seed = neighbors(i)
        if len(seed) < min_pts:
            continue  # noise stays -1
        cluster_id += 1
        labels[i] = cluster_id
        queue = list(seed)
        while queue:
            j = queue.pop()
            if labels[j] != -1 and labels[j] != cluster_id:
                continue  # already claimed by another cluster
            labels[j] = cluster_id
            jn = neighbors(j)
            if len(jn) >= min_pts:
                for k in jn:
                    if labels[k] == -1:
                        labels[k] = cluster_id
                        queue.append(k)
    return labels


def cluster_centroid(points: list[tuple[float, float]], labels: list[int], cluster: int) -> tuple[float, float] | None:
    members = [p for p, lab in zip(points, labels) if lab == cluster]
    if not members:
        return None
    n = len(members)
    return sum(p[0] for p in members) / n, sum(p[1] for p in members) / n