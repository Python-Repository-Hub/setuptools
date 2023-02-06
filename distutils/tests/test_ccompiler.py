import os
import sys
import platform
import textwrap
import sysconfig

import pytest

from distutils import ccompiler


def _make_strs(paths):
    """
    Convert paths to strings for legacy compatibility.
    """
    if sys.version_info > (3, 8) and platform.system() != "Windows":
        return paths
    return list(map(os.fspath, paths))


@pytest.fixture
def c_file(tmp_path):
    c_file = tmp_path / 'foo.c'
    gen_headers = ('Python.h',)
    is_windows = platform.system() == "Windows"
    plat_headers = ('windows.h',) * is_windows
    all_headers = gen_headers + plat_headers
    headers = '\n'.join(f'#include <{header}>\n' for header in all_headers)
    payload = (
        textwrap.dedent(
            """
        #headers
        void PyInit_foo(void) {}
        """
        )
        .lstrip()
        .replace('#headers', headers)
    )
    c_file.write_text(payload)
    return c_file


def test_set_include_dirs(c_file):
    """
    Extensions should build even if set_include_dirs is invoked.
    In particular, compiler-specific paths should not be overridden.
    """
    compiler = ccompiler.new_compiler()
    python = sysconfig.get_paths()['include']
    compiler.set_include_dirs([python])
    compiler.compile(_make_strs([c_file]))

    # do it again, setting include dirs after any initialization
    compiler.set_include_dirs([python])
    compiler.compile(_make_strs([c_file]))


@pytest.mark.xfail('platform.system() == "Windows"')
def test_has_function_prototype():
    # Issue https://github.com/pypa/setuptools/issues/3648
    # Test prototype-generating behavior.

    compiler = ccompiler.new_compiler()

    # Every C implementation should have these.
    assert compiler.has_function('abort')
    assert compiler.has_function('exit')
    with pytest.deprecated_call(match='includes is deprecated'):
        # abort() is a valid expression with the <stdlib.h> prototype.
        assert compiler.has_function('abort', includes=['<stdlib.h>'])
    with pytest.deprecated_call(match='includes is deprecated'):
        # But exit() is not valid with the actual prototype in scope.
        assert not compiler.has_function('exit', includes=['<stdlib.h>'])
    # And setuptools_does_not_exist is not declared or defined at all.
    assert not compiler.has_function('setuptools_does_not_exist')
    with pytest.deprecated_call(match='includes is deprecated'):
        assert not compiler.has_function(
            'setuptools_does_not_exist', includes=['<stdio.h>']
        )
