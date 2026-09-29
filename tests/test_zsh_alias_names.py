from chatup.setup.zsh import render_zsh_aliases


def test_pip_install_alias_rename_preserves_both_urls():
    lines = render_zsh_aliases().splitlines()
    assert 'alias tspip="pip install -i https://pypi.tuna.tsinghua.edu.cn/simple"' in lines
    assert "alias pypip='pip install -i https://pypi.python.org/simple'" in lines
    assert not any(line.startswith("alias pypi=") for line in lines)
