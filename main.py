"""pygbag entry point — pygbag executes assets/main.py inside the WASM
bundle, so this thin shim just imports databreach.py, which runs the
game at module load via its top-level asyncio.run(main()).
"""
import databreach  # noqa: F401
