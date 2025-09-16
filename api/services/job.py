from threading import Thread
from typing import Dict, Optional

import msgpack
from sqlmodel import Session, select

from api.db import SessionLocal
from api.models import FileProjectLink, FileRead, ProcessJob
from api.utils import data_processor

from .file import FileService


class ProcessJobService:
    def __init__(self, session: Session):
        self.session = session

    def get_job(self, job_id: int) -> ProcessJob:
        """Get a process job by ID"""
        return self.session.get(ProcessJob, job_id)

    def get_job_progress(self, job_id: int) -> Dict:
        """Get job progress information"""
        job = self.get_job(job_id)
        if not job:
            return {"error": "Job not found"}

        return {
            "status": job.status,
            "progress": job.progress,
            "error": job.error,
        }

    def get_job_result_path(self, job_id: int) -> Optional[str]:
        """Get job result path if completed"""
        job = self.get_job(job_id)
        if job and job.status == "done" and job.result_path:
            return job.result_path
        return None

    def start_file_processing(self, project_id: int, file_id: int) -> int:
        """Start processing a single file in the background"""
        file_service = FileService(self.session)

        file_data = file_service.get_file(project_id, file_id)
        if not file_data:
            raise ValueError(
                f"File with id {file_id} not found in project {project_id}"
            )

        new_job = ProcessJob(
            project_id=project_id, file_id=file_id, status="pending", progress=0.0
        )
        self.session.add(new_job)
        self.session.commit()
        self.session.refresh(new_job)

        job_id = new_job.id

        thread = Thread(
            target=self._run_file_processing,
            args=(job_id, project_id, file_data),
            daemon=True,
        )
        thread.start()

        return job_id

    def _run_file_processing(self, job_id: int, project_id: int, file_data: FileRead):
        """Run the actual file processing in background thread"""
        with SessionLocal() as session:
            try:

                def progress_callback(progress: float):
                    progress = round(progress, 2)
                    self._update_job_progress(job_id, progress)

                self._update_job_status(job_id, "processing")

                processed_file_data = data_processor.process_data(
                    file_config=file_data,
                    progress_callback=progress_callback,
                )

                result_path = f"./data/astrovisio_files/project_{project_id}_file_{file_data.id}_processed.msgpack"

                data_dict = {
                    "columns": processed_file_data.columns,
                    "rows": processed_file_data.to_numpy().tolist(),
                }
                binary_data = msgpack.packb(data_dict, use_bin_type=True)

                with open(result_path, "wb") as f:
                    f.write(binary_data)

                with SessionLocal() as update_session:
                    statement = select(FileProjectLink).where(
                        FileProjectLink.project_id == project_id,
                        FileProjectLink.file_id == file_data.id,
                    )
                    file_link = update_session.exec(statement).first()
                    file_link.processed = True
                    file_link.processed_path = result_path
                    update_session.add(file_link)
                    update_session.commit()

                self._update_job_completion(job_id, result_path)

            except Exception as e:
                self._update_job_error(job_id, str(e))

                self._update_job_completion(job_id, result_path)

            except Exception as e:
                self._update_job_error(job_id, str(e))

    def _update_job_progress(self, job_id: int, progress: float):
        """Update job progress"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.progress = progress
                session.commit()

    def _update_job_status(self, job_id: int, status: str, progress: float = None):
        """Update job status and optionally progress"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                session.commit()

    def _update_job_completion(self, job_id: int, result_path: str):
        """Mark job as completed with result path"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.status = "done"
                job.progress = 1.0
                job.result_path = result_path
                session.commit()

    def _update_job_error(self, job_id: int, error_message: str):
        """Mark job as failed with error message"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.status = "error"
                job.progress = 1.0
                job.error = error_message
                session.commit()
