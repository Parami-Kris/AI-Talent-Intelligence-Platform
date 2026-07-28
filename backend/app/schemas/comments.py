from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    comment_text: str = Field(min_length=1)
    is_caution: bool = False


class CommentResponse(BaseModel):
    id: int
    comment_text: str
    is_caution: bool
    created_at: str


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
