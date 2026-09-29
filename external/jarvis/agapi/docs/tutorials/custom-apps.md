---
title: Building Custom Apps
---

# Building Custom Apps for AtomGPT.org

Add your own web application to the AtomGPT.org platform using the plugin system.

## Architecture

Every app has two files:

```
custom_routes/my_app.py      # FastAPI backend
custom_templates/my_app.html  # HTML frontend
```

## 1. Create the Backend

```python
# custom_routes/my_app.py

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from open_webui.utils.auth import get_current_user
from .shared import templates

router = APIRouter(tags=["MyCategory"])

class MyRequest(BaseModel):
    input_data: str

@router.get("/my_app", response_class=HTMLResponse)
async def my_app_home(request: Request):
    return templates.TemplateResponse("my_app.html", {"request": request})

@router.post("/my_app/compute")
async def my_app_compute(
    request: MyRequest,
    user=Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Your computation here
    return {"result": f"Processed: {request.input_data}"}
```

## 2. Create the Frontend

Use the dark theme template matching other AtomGPT apps.

## 3. Register in custom.py

```python
from .custom_routes import my_app
metered.include_router(my_app.router)
```

## 4. Add to apps.html

```javascript
{name:"My App", desc:"Description here",
 icon:"icon", href:"/my_app", cat:"explore",
 status:"new", accent:"#4da6ff",
 bg:"rgba(77,166,255,0.08)",
 tag:"Tag1 · Tag2"}
```

## Plugin System

For external contributors, use the plugin system:

1. Fork the [template repo](https://github.com/atomgptlab/atomgpt-app-template)
2. Edit `manifest.json`, `app.py`, `template.html`
3. Submit PR to community-apps repo

## Reference

See the AtomGPT.org developer guide for details.
