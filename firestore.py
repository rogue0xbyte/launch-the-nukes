# Seeting up the framework (architecture) for GCP Firestore
from typing import Any, Dict, List, Optional
from datetime import datetime
from google.cloud import firestore
from enum import Enum
from dataclasses import dataclass

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    job_id: str
    user_id: str
    username: str
    prompt: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    progress: int = 0
    progress_message: str = "Queued"

class FirestoreJobStore:
    def __init__(self, project_id: str):
        # Initialize Firestore client for the GCP project
        self.db = firestore.Client(project=project_id)
        self.col = self.db.collection("jobs")

    def _doc_to_job(self, data) -> Job:
        d = data.to_dict()
        return Job(
            job_id=data.id,
            user_id=d["user_id"],
            username=d["username"],
            prompt=d["prompt"],
            status=JobStatus(d["status"]),
            created_at=d["created_at"],
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            result=d.get("result"),
            progress=d.get("progress", 0),
            progress_message=d.get("progress_message", "Queued"),
        )

    def create_job(self, job: Job) -> None:
        """
        Creating the document and setting it with the key value as the Job ID
        """
        self.col.document(job.job_id).set({
            "user_id": job.user_id,
            "username": job.username,
            "prompt": job.prompt,
            "status": job.status.value,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result": job.result,
            "progress": job.progress,
            "progress_message": job.progress_message,
        })

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Retrieve a job by its ID. Returns None if not found.
        """
        data = self.col.document(job_id).get()
        return self._doc_to_job(data) if data.exists else None

    def update_job(self, job_id: str, **fields) -> None:
        """
        Updating the Job Fields once the status changes from Queued to Completed
        Make the least use of this function to keep the system cost efficient and less queried on the DB
        """
        if "status" in fields and isinstance(fields["status"], JobStatus):
            fields["status"] = fields["status"].value
        self.col.document(job_id).update(fields)
    
    # This function has not been used yet but will be referenced once the Redis Implementation is limited to caching
    def list_jobs_for_user(self, user_id: str) -> List[Job]:
        q = (self.col.where("user_id", "==", user_id)
                   .order_by("created_at", direction=firestore.Query.DESCENDING))
        return [self._doc_to_job(s) for s in q.stream()]
