"""Data models for CCFDDL conference data.

This module contains dataclasses that represent the structure of conference data,
migrated from the Rust/WASM frontend (src/components/conf.rs).
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Rank:
    """Conference ranking information."""
    ccf: str
    core: Optional[str] = None
    thcpl: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rank":
        return cls(
            ccf=data.get("ccf", "N"),
            core=data.get("core"),
            thcpl=data.get("thcpl"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"ccf": self.ccf}
        if self.core is not None:
            result["core"] = self.core
        if self.thcpl is not None:
            result["thcpl"] = self.thcpl
        return result


@dataclass
class Timeline:
    """Timeline entry for a conference deadline."""
    deadline: str
    abstract_deadline: Optional[str] = None
    comment: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Timeline":
        return cls(
            deadline=data.get("deadline", ""),
            abstract_deadline=data.get("abstract_deadline"),
            comment=data.get("comment"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"deadline": self.deadline}
        if self.abstract_deadline is not None:
            result["abstract_deadline"] = self.abstract_deadline
        if self.comment is not None:
            result["comment"] = self.comment
        return result


@dataclass
class ConferenceYear:
    """Conference information for a specific year."""
    year: int
    id: str
    link: str
    timeline: list[Timeline]
    timezone: str
    date: str
    place: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConferenceYear":
        timeline_data = data.get("timeline", [])
        return cls(
            year=data.get("year", 0),
            id=data.get("id", ""),
            link=data.get("link", ""),
            timeline=[Timeline.from_dict(t) for t in timeline_data],
            timezone=data.get("timezone", "UTC"),
            date=data.get("date", ""),
            place=data.get("place", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "id": self.id,
            "link": self.link,
            "timeline": [t.to_dict() for t in self.timeline],
            "timezone": self.timezone,
            "date": self.date,
            "place": self.place,
        }


@dataclass
class Conference:
    """Conference data model matching the YAML schema."""
    title: str
    description: str
    sub: str
    rank: Rank
    dblp: str
    confs: list[ConferenceYear] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Conference":
        rank_data = data.get("rank", {})
        confs_data = data.get("confs", [])
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            sub=data.get("sub", ""),
            rank=Rank.from_dict(rank_data),
            dblp=data.get("dblp", ""),
            confs=[ConferenceYear.from_dict(c) for c in confs_data],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "sub": self.sub,
            "rank": self.rank.to_dict(),
            "dblp": self.dblp,
            "confs": [c.to_dict() for c in self.confs],
        }


@dataclass
class Category:
    """Conference category with Chinese and English names."""
    name: str
    name_en: str
    sub: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        return cls(
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            sub=data.get("sub", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "name_en": self.name_en,
            "sub": self.sub,
        }


CATEGORIES: list[Category] = [
    Category(name="计算机体系结构/并行与分布计算/存储系统", name_en="Computer Architecture", sub="DS"),
    Category(name="计算机网络", name_en="Network System", sub="NW"),
    Category(name="网络与信息安全", name_en="Network and System Security", sub="SC"),
    Category(name="软件工程/系统软件/程序设计语言", name_en="Software Engineering", sub="SE"),
    Category(name="数据库/数据挖掘/内容检索", name_en="Database", sub="DB"),
    Category(name="计算机科学理论", name_en="Computing Theory", sub="CT"),
    Category(name="计算机图形学与多媒体", name_en="Graphics", sub="CG"),
    Category(name="人工智能", name_en="Artificial Intelligence", sub="AI"),
    Category(name="人机交互与普适计算", name_en="Computer-Human Interaction", sub="HI"),
    Category(name="交叉/综合/新兴", name_en="Interdiscipline", sub="MX"),
]

SUB_TO_CATEGORY: dict[str, Category] = {cat.sub: cat for cat in CATEGORIES}

VALID_SUBS: set[str] = {cat.sub for cat in CATEGORIES}

VALID_CCF_RANKS: set[str] = {"A", "B", "C", "N"}


def get_category_by_sub(sub: str) -> Optional[Category]:
    """Get category by sub code."""
    return SUB_TO_CATEGORY.get(sub)


def get_all_subs() -> list[str]:
    """Get all valid sub codes."""
    return list(VALID_SUBS)


def is_valid_sub(sub: str) -> bool:
    """Check if sub code is valid."""
    return sub in VALID_SUBS


@dataclass
class AccYear:
    """Acceptance rate for a specific year."""
    year: int
    submitted: int
    accepted: int
    info: str
    rate: str
    source: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccYear":
        return cls(
            year=data.get("year", 0),
            submitted=data.get("submitted", 0),
            accepted=data.get("accepted", 0),
            info=data.get("str", ""),
            rate=data.get("rate", ""),
            source=data.get("source"),
        )


@dataclass
class ConfAccRate:
    """Acceptance rates for a conference."""
    title: str
    accept_rates: list[AccYear] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfAccRate":
        rates_data = data.get("accept_rates", [])
        return cls(
            title=data.get("title", ""),
            accept_rates=[AccYear.from_dict(r) for r in rates_data],
        )