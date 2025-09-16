from fastapi import APIRouter, Response

from api.deps import ProcessJobServiceDep

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/progress")
def process_progress(*, job_id: int, service: ProcessJobServiceDep):
    """Get processing progress"""
    return service.get_job_progress(job_id)


@router.get("/{job_id}/result", response_class=Response)
def process_result(*, job_id: int, service: ProcessJobServiceDep):
    """Get processing result"""
    result_path = service.get_job_result_path(job_id)

    if not result_path:
        return Response(
            content="Job not found or not completed",
            status_code=404,
            media_type="text/plain",
        )

    with open(result_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="application/octet-stream")
