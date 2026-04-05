"""
Preview server: serves generated websites directly from the database.
Each lead's website is accessible at /preview/{lead_id}/{slug}

This means ALL previews run from one single Railway deployment —
no separate project per website.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from database.connection import get_session
from database.models import Lead, Website, Deployment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/preview/{lead_id}", response_class=HTMLResponse)
@router.get("/preview/{lead_id}/{slug}", response_class=HTMLResponse)
def serve_preview(lead_id: int, slug: str = ""):
    session = get_session()
    try:
        lead = session.query(Lead).get(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Preview not found")

        website = (
            session.query(Website)
            .filter(Website.lead_id == lead_id)
            .order_by(Website.version.desc())
            .first()
        )
        if not website or not website.html_content:
            raise HTTPException(status_code=404, detail="Website not yet built")

        deployment = (
            session.query(Deployment)
            .filter(
                Deployment.lead_id == lead_id,
                Deployment.is_active == True,
            )
            .first()
        )
        if not deployment:
            raise HTTPException(
                status_code=404,
                detail="Preview not published",
            )

        tracking_pixel = f"""
        <script>
        fetch('/api/preview/{lead_id}/view', {{method:'POST'}}).catch(()=>{{}});
        </script>
        """
        html = website.html_content.replace("</body>", f"{tracking_pixel}</body>")

        return HTMLResponse(content=html)
    finally:
        session.close()


@router.get("/preview/{lead_id}/raw", response_class=HTMLResponse)
def serve_raw_preview(lead_id: int):
    """Serves the raw HTML without tracking — for internal QA."""
    session = get_session()
    try:
        website = (
            session.query(Website)
            .filter(Website.lead_id == lead_id)
            .order_by(Website.version.desc())
            .first()
        )
        if not website or not website.html_content:
            raise HTTPException(status_code=404, detail="Website not found")
        return HTMLResponse(content=website.html_content)
    finally:
        session.close()
