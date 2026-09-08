from app.algorithms.clustering import cluster_centroid, dbscan


def test_dbscan_finds_two_clusters():
    # two dense groups ~1 km apart, one far-away noise point
    points = []
    for i in range(6):
        points.append((17.4840 + i * 0.0008, 78.4080))  # cluster A (spacing ~89 m)
    for i in range(5):
        points.append((17.4960 + i * 0.0008, 78.4140))  # cluster B
    points.append((17.5200, 78.4400))  # noise

    labels = dbscan(points, eps_m=300, min_pts=3)
    clusters = set(labels)
    assert -1 in clusters  # noise exists
    assert len(clusters) - 1 == 2  # two real clusters


def test_dbscan_singletons_are_noise():
    points = [(17.48, 78.40), (17.49, 78.41), (17.50, 78.42)]
    labels = dbscan(points, eps_m=200, min_pts=3)
    assert all(l == -1 for l in labels)


def test_centroid():
    points = [(17.48, 78.40), (17.481, 78.401), (17.479, 78.399)]
    labels = dbscan(points, eps_m=500, min_pts=2)
    c = cluster_centroid(points, labels, 1)
    assert c is not None
    assert abs(c[0] - 17.48) < 0.002
    assert abs(c[1] - 78.40) < 0.002