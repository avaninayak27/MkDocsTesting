# HIO Interface

The HIO (Host IO) Interface provides a RPC-like mechanism to call
functions on-chip from an application running on a host.

## Adding a new HIO method

### Adding a new group

As an example, assume we wish to add a `hio_demo` interface group,
with an `add` method.

1. Start by creating `script/hio/api/hio_demo.py`:

```python
"""
HIO Demo API specification
"""
from hio.base import message, uint32

class add(message):
    req   = [
        uint32("a"),
        uint32("b")
    ]
    rsp   = [
        uint32("q"),
    ]
```

This defines a HIO group (`hio_demo`) with one method (`add`) taking
two ints and returning one.

2. Add the `module name` and `group id` to the list in `hio_config.json` as below.
```json
{
    "hio_demo": {
        "group_id": 4,
        "header_file_path": "apu/middleware/hio/inc/api",
        "c_file_path": "apu/middleware/hio/src/api",
        "cogg_py_path": "scripts/hio/api",
        "enable": true
    }
}
```

### Note:

* The user can select which module to use by simply setting the enable attribute to `true`.
If enable is set to `false`, the module will not be active.


* From the Python side, this is all that's needed. The configuration in hio_config.json
will determine which modules are enabled or disabled. No additional changes are required
in the Python code itself.


## Running COG from makefile

After compilting of step 1 and step 2 you can build the header and source files by running the following commands:

1. Go to the ../../middelware/hio/ directory:

```shell
cd ../../middelware/hio
```

2. Clean up any previous build artifacts:

```shell
make clean
```

3. Run the make recog command to regenerate/updates HIO header and source files and run COG automatically:

```shell
make recog
```
4. Finally, build the new files:

```shell
make
```

## Note

* Whenever you modify the HIO specification (e.g., `hio_demo.py`), remember to regenerate the header and source files by running the COG script.