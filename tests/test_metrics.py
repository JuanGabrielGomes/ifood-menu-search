from menusearch.metrics import hit_at_k, recall_at_k


def test_recall_total_quando_todos_os_relevantes_aparecem():
    assert recall_at_k(["a", "b", "x"], ["a", "b"], 5) == 1.0


def test_recall_parcial():
    assert recall_at_k(["a", "x", "y"], ["a", "b"], 5) == 0.5


def test_recall_limitado_por_k_quando_ha_muitos_relevantes():
    relevant = [f"r{i}" for i in range(12)]
    assert recall_at_k(relevant[:5], relevant, 5) == 1.0


def test_so_conta_o_top_k():
    assert recall_at_k(["x", "y", "a"], ["a"], 2) == 0.0


def test_hit():
    assert hit_at_k(["x", "a"], ["a"], 5) is True
    assert hit_at_k(["x", "y"], ["a"], 5) is False
