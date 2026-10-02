"""Build the pjsua2 Python extension with MSVC against a Visual Studio build of pjproject.

pjproject's own setup.py drives `make` (MSYS2/MinGW). This one links the single
libpjproject-*-Release-Dynamic.lib that pjproject-vs14.sln produces, so the
extension matches the official CPython (MSVC, dynamic CRT) that PySide6 needs.

Run from the directory holding pjsua2_wrap.cpp and pjsua2.py (SWIG output), with
PJDIR pointing at the pjproject checkout:

    python setup_pjsua2.py bdist_wheel
"""

import glob
import os

from setuptools import Extension, setup

PJDIR = os.environ["PJDIR"]

include_dirs = [os.path.join(PJDIR, part, "include") for part in ("pjlib", "pjlib-util", "pjmedia", "pjsip", "pjnath")]

libraries_found = glob.glob(os.path.join(PJDIR, "lib", "libpjproject-x86_64-x64-vc*-Release-Dynamic.lib"))
if len(libraries_found) != 1:
    raise SystemExit(f"expected exactly one libpjproject Release-Dynamic library, found {libraries_found}")

setup(
    name="pjsua2",
    version=os.environ.get("PJ_VERSION", "0"),
    description="pjsua2 Python binding (voice2fritz Windows build)",
    py_modules=["pjsua2"],
    ext_modules=[
        Extension(
            "_pjsua2",
            ["pjsua2_wrap.cpp"],
            include_dirs=include_dirs,
            # Same defines pjproject-vs14-common-config.props uses for x64 desktop builds.
            define_macros=[("WIN64", None), ("PJ_WIN64", "1"), ("PJ_M_X86_64", "1")],
            extra_objects=libraries_found,
            libraries=[
                "ws2_32", "mswsock", "iphlpapi", "winmm", "ole32", "oleaut32", "uuid",
                "advapi32", "user32", "gdi32", "dsound", "dxguid", "strmiids",
            ],
            extra_compile_args=["/EHsc", "/bigobj"],
        )
    ],
)
