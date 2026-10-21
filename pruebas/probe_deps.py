import importlib
for m in ["fastapi","uvicorn","httpx","pydantic"]:
    try:
        mod = importlib.import_module(m)
        print("  OK  ", m, getattr(mod, "__version__", "?"))
    except Exception as e:
        print("  FALLA", m, type(e).__name__, e)
