from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, UploadFile
from fastapi import HTTPException, status
from fastapi import Request


router = APIRouter()


def _pm(request: Request):
    return request.app.state.plugin_manager


@router.get("/plugins")
def list_plugins(pm=Depends(_pm)):
    all_names = pm.discover()
    loaded = list(pm.loaded.keys())
    return {"available": all_names, "loaded": loaded}


@router.post("/plugins/{name}/enable")
def enable_plugin(name: str, pm=Depends(_pm)):
    try:
        pm.load(name)
        return {"status": "enabled", "name": name}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/plugins/{name}/disable")
def disable_plugin(name: str, pm=Depends(_pm)):
    pm.disable(name)
    return {"status": "inactive", "name": name}


@router.post("/plugins/{name}/reload")
def reload_plugin(name: str, pm=Depends(_pm)):
    pm.reload(name)
    return {"status": "reloaded", "name": name}


@router.post("/plugins/install")
def install_plugin(file: UploadFile, pm=Depends(_pm)):
    # Save upload to a temp file
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip uploads are supported")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / file.filename
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Extract safely to staging
            staging = Path(tmpdir) / "staging"
            staging.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(tmp_path) as zf:
                for member in zf.infolist():
                    # prevent path traversal
                    dest = staging / member.filename
                    dest_abs = dest.resolve()
                    if not str(dest_abs).startswith(str(staging.resolve())):
                        raise HTTPException(
                            status_code=400, detail="Invalid archive paths"
                        )
                    if member.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as out:
                            shutil.copyfileobj(src, out)

            # Find plugin root (dir containing plugin.py)
            candidates = [p.parent for p in staging.rglob("plugin.py")]
            candidates = [c for c in candidates if (c / "plugin.py").exists()]
            if len(candidates) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Archive must contain exactly one plugin root with plugin.py",
                )
            plugin_root = candidates[0]
            name = plugin_root.name

            # Install into plugins/<name>
            dest_dir = Path(pm.plugins_dir) / name
            if dest_dir.exists():
                raise HTTPException(
                    status_code=409, detail=f"Plugin '{name}' already exists"
                )
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(plugin_root, dest_dir)

            # loading it
            pm.load(name)
            return {"status": "installed", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
