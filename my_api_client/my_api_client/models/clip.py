from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Clip")


@_attrs_define
class Clip:
    """
    Attributes:
        start (int):
        end (int):
        type_ (str):
        description (str):
        labels (list[str]):
        title (str):
        partners (list[str]):
    """

    start: int
    end: int
    type_: str
    description: str
    labels: list[str]
    title: str
    partners: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        start = self.start

        end = self.end

        type_ = self.type_

        description = self.description

        labels = self.labels

        title = self.title

        partners = self.partners

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "start": start,
                "end": end,
                "type": type_,
                "description": description,
                "labels": labels,
                "title": title,
                "partners": partners,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        start = d.pop("start")

        end = d.pop("end")

        type_ = d.pop("type")

        description = d.pop("description")

        labels = cast(list[str], d.pop("labels"))

        title = d.pop("title")

        partners = cast(list[str], d.pop("partners"))

        clip = cls(
            start=start,
            end=end,
            type_=type_,
            description=description,
            labels=labels,
            title=title,
            partners=partners,
        )

        clip.additional_properties = d
        return clip

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
