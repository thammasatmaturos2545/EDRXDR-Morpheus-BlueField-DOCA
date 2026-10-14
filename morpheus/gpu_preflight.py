"""GPU/runtime preflight only. No Kafka consume and no inference."""

import os
import sys


def require_permission():
    if os.environ.get("GPU_PREFLIGHT_ALLOWED") != "1":
        raise RuntimeError(
            "GPU preflight not explicitly allowed"
        )


def main():
    require_permission()

    import torch
    import cupy
    import cudf

    count = torch.cuda.device_count()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one visible reserved GPU, got {count}"
        )

    name = torch.cuda.get_device_name(0)

    x = cupy.asarray([1.0, 2.0, 3.0])
    total = float(x.sum().get())

    if total != 6.0:
        raise RuntimeError("CuPy GPU check failed")

    frame = cudf.DataFrame({"x": [1, 2, 3]})

    if int(frame["x"].sum()) != 6:
        raise RuntimeError("cuDF GPU check failed")

    print("GPU preflight: PASS")
    print("python           :", sys.version.split()[0])
    print("torch            :", torch.__version__)
    print("CUDA available   :", torch.cuda.is_available())
    print("visible GPUs     :", count)
    print("GPU              :", name)
    print("CuPy             :", cupy.__version__)
    print("cuDF             :", cudf.__version__)
    print("Kafka consumed   : false")
    print("inference run    : false")


if __name__ == "__main__":
    main()
