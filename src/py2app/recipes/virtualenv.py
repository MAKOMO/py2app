"""
virtualenv installs a wrapper for the real distutils into the
virtual environment. Ignore that wrapper, but go for the real
distutils instead

This recipe is rather compilicated and definitely not a
good model for other recipes!!!
"""
import imp
import os
import sys
import typing

from modulegraph.modulegraph import (
    CompiledModule,
    MissingModule,
    ModuleGraph,
    Node,
    Package,
    SourceModule,
    find_module,
)

from .. import build_app
from ._types import RecipeInfo


def retry_import(mf: ModuleGraph, m: Node) -> typing.Optional[Node]:
    """
    Try to reimport 'm', which should be a MissingModule
    """
    if "." in m.identifier:
        pname, partname = m.identifier.rsplit(".", 1)
        parent = mf.findNode(pname)
    else:
        parent = None
        partname = m.identifier

    # This is basically mf.find_module inlined and with a
    # check disabled.

    def fmod(
        name: str,
        path: typing.Optional[typing.List[str]],
        parent: typing.Optional[Node],
    ) -> typing.Tuple[
        typing.Optional[typing.IO], typing.Optional[str], typing.Tuple[str, str, int]
    ]:
        if path is None:
            if name in sys.builtin_module_names:
                return (None, None, ("", "", imp.C_BUILTIN))

            path = mf.path

        fp, buf, stuff = find_module(name, path)
        if buf:
            buf = os.path.realpath(buf)
        return (fp, buf, stuff)

    try:
        fp, pathname, stuff = fmod(
            partname, parent.packagepath if parent is not None else None, parent
        )
    except ImportError:
        return None

    if stuff[-1] == imp.PKG_DIRECTORY:
        m.__class__ = Package
    elif stuff[-1] == imp.PY_SOURCE:
        m.__class__ = SourceModule
    else:
        m.__class__ = CompiledModule

    m = mf._load_module(m.identifier, fp, pathname, stuff)

    if parent:
        mf.createReference(m, parent)
        parent[partname] = m
    return m


def check(cmd: "build_app.py2app", mf: ModuleGraph) -> typing.Optional[RecipeInfo]:
    m = mf.findNode("distutils")
    if m is None or m.filename is None:
        return None

    with open(m.filename) as fp:
        contents = fp.read()
    if "virtualenv" in contents:
        # This is the virtualenv version
        mos = mf.findNode("os")
        if mos is None or mos.filename is None:
            raise ValueError("Where is the os module")

        m.filename = os.path.join(
            os.path.dirname(mos.filename), "distutils", "__init__.py"
        )
        with open(m.filename) as fp:
            source = fp.read() + "\n"
        m.code = co = compile(source, m.filename, "exec")
        m.packagepath = [os.path.dirname(m.filename)]

        if mf.replace_paths:
            co = mf._replace_paths_in_code(co)

        # Recent versions of modulegraph made scan_code private,
        # temporarily call the private version.
        mf._scan_code(co, m)

        # That's not all there is to this, we need to look for
        # MissingModules in the distutils namespace as well and
        # try to import these again.
        for m in mf.flatten():
            if isinstance(m, MissingModule):
                if m.identifier.startswith("distutils."):
                    # A missing distutils package, retry
                    # importing it.
                    #
                    retry_import(mf, m)

    return {}
