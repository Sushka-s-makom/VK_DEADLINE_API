from pydantic import BaseModel

from app.schemas.common import Timestamped


class VKCommunityCreate(BaseModel):
    title: str
    vk_group_id: int
    token_env_name: str
    is_active: bool = True


class VKCommunityRead(Timestamped):
    id: int
    title: str
    vk_group_id: int
    token_env_name: str
    is_active: bool
