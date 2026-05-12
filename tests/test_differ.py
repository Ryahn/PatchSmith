from patcher.core.differ import diff_trees


def test_diff_trees_basic() -> None:
    old = {"a.txt": ("aa", 1), "b.txt": ("bb", 2)}
    new = {"a.txt": ("aa", 1), "b.txt": ("cc", 3), "c.txt": ("dd", 4)}
    dr = diff_trees(old, new)
    assert dr.unchanged == frozenset({"a.txt"})
    assert dr.changed == frozenset({"b.txt"})
    assert dr.new == frozenset({"c.txt"})
    assert dr.deleted == frozenset()


def test_diff_trees_deleted() -> None:
    old = {"x": ("1", 1)}
    new: dict[str, tuple[str, int]] = {}
    dr = diff_trees(old, new)
    assert dr.deleted == frozenset({"x"})
