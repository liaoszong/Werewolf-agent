from werewolf_eval.ablation.arms import Arm, layout_for, CANONICAL_MULTISET

def test_layout_is_canonical_multiset_and_paired_by_index():
    a = Arm(label="baseline", prompt_version="prompt_v1", n_games=4, seed_base=1000)
    b = Arm(label="b1", prompt_version="prompt_v2", n_games=4, seed_base=1000)
    for i in range(4):
        la, lb = layout_for(a, i), layout_for(b, i)
        assert la == lb, "paired arms must share layout per index"
        assert sorted(la.values()) == sorted(CANONICAL_MULTISET)
        assert set(la) == {"p1","p2","p3","p4","p5","p6"}

def test_seed_for_index_is_seed_base_plus_index():
    a = Arm(label="x", prompt_version="prompt_v1", n_games=3, seed_base=2000)
    assert [a.seed_for(i) for i in range(3)] == [2000, 2001, 2002]
