from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Subject:
    id: int
    name: str
    code: Optional[str] = None


@dataclass
class Course:
    id: int
    subject_id: int
    name: str
    vk_code: Optional[str] = None
    sheet_id: Optional[str] = None
    sheet_range: Optional[str] = None


@dataclass
class Group:
    id: int
    peer_id: int
    course_id: int
    title: Optional[str] = None


@dataclass
class Deadline:
    id: int
    course_id: int
    title: str
    description: Optional[str]
    due_at: datetime


__all__ = ["Subject", "Course", "Group", "Deadline"]

