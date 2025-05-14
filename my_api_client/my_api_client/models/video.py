from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.clip import Clip


T = TypeVar("T", bound="Video")


@_attrs_define
class Video:
    """
    Attributes:
        video_id (str):
        youtube_url (str):
        title (str):
        date (str):
        duration_seconds (float):
        type_ (Union[None, Unset, str]):  Default: ''.
        partners (Union[Unset, list[str]]):
        positions (Union[Unset, list[str]]):
        notes (Union[None, Unset, str]):  Default: ''.
        labels (Union[Unset, list[str]]):
        clips (Union[Unset, list['Clip']]):
    """

    video_id: str
    youtube_url: str
    title: str
    date: str
    duration_seconds: float
    type_: Union[None, Unset, str] = ""
    partners: Union[Unset, list[str]] = UNSET
    positions: Union[Unset, list[str]] = UNSET
    notes: Union[None, Unset, str] = ""
    labels: Union[Unset, list[str]] = UNSET
    clips: Union[Unset, list["Clip"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        video_id = self.video_id

        youtube_url = self.youtube_url

        title = self.title

        date = self.date

        duration_seconds = self.duration_seconds

        type_: Union[None, Unset, str]
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        partners: Union[Unset, list[str]] = UNSET
        if not isinstance(self.partners, Unset):
            partners = self.partners

        positions: Union[Unset, list[str]] = UNSET
        if not isinstance(self.positions, Unset):
            positions = self.positions

        notes: Union[None, Unset, str]
        if isinstance(self.notes, Unset):
            notes = UNSET
        else:
            notes = self.notes

        labels: Union[Unset, list[str]] = UNSET
        if not isinstance(self.labels, Unset):
            labels = self.labels

        clips: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.clips, Unset):
            clips = []
            for clips_item_data in self.clips:
                clips_item = clips_item_data.to_dict()
                clips.append(clips_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "video_id": video_id,
                "youtube_url": youtube_url,
                "title": title,
                "date": date,
                "duration_seconds": duration_seconds,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_
        if partners is not UNSET:
            field_dict["partners"] = partners
        if positions is not UNSET:
            field_dict["positions"] = positions
        if notes is not UNSET:
            field_dict["notes"] = notes
        if labels is not UNSET:
            field_dict["labels"] = labels
        if clips is not UNSET:
            field_dict["clips"] = clips

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.clip import Clip

        d = dict(src_dict)
        video_id = d.pop("video_id")

        youtube_url = d.pop("youtube_url")

        title = d.pop("title")

        date = d.pop("date")

        duration_seconds = d.pop("duration_seconds")

        def _parse_type_(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        type_ = _parse_type_(d.pop("type", UNSET))

        partners = cast(list[str], d.pop("partners", UNSET))

        positions = cast(list[str], d.pop("positions", UNSET))

        def _parse_notes(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        notes = _parse_notes(d.pop("notes", UNSET))

        labels = cast(list[str], d.pop("labels", UNSET))

        clips = []
        _clips = d.pop("clips", UNSET)
        for clips_item_data in _clips or []:
            clips_item = Clip.from_dict(clips_item_data)

            clips.append(clips_item)

        video = cls(
            video_id=video_id,
            youtube_url=youtube_url,
            title=title,
            date=date,
            duration_seconds=duration_seconds,
            type_=type_,
            partners=partners,
            positions=positions,
            notes=notes,
            labels=labels,
            clips=clips,
        )

        video.additional_properties = d
        return video

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
