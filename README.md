# voice2fritz

SIP softphone for FRITZ!Box.

## Setup

`voice2fritz` requires `pjsua2` (PJSIP's Python bindings), which is not
distributed on PyPI. Build PJSIP from source with Python bindings enabled
(see https://docs.pjsip.org/en/latest/pjsua2/building.html), then ensure
the resulting `pjsua2` module is importable from your virtualenv (e.g. by
copying/symlinking the built `.so`/`.py` files into the venv's
`site-packages`, or setting `PYTHONPATH`).
