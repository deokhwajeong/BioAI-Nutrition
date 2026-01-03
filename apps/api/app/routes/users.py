"""
apps/api/app/routes/users.py

User management routes for privacy features.
"""

from fastapi import APIRouter, status, HTTPException

router = APIRouter()

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """
    Schedule deletion of all data associated with a user. In a real implementation,
    this would enqueue a task to delete user data from the database and storage.
    """
    # TODO: integrate with data store to delete user data. For now, we just return 204.
    return None
