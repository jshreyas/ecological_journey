from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.video import Video


T = TypeVar("T", bound="Playlist")


@_attrs_define
class Playlist:
    """
    Attributes:
        name (str):
        videos (list['Video']):
    """

    name: str
    videos: list["Video"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        videos = []
        for videos_item_data in self.videos:
            videos_item = videos_item_data.to_dict()
            videos.append(videos_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "videos": videos,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.video import Video

        d = dict(src_dict)
        name = d.pop("name")

        videos = []
        _videos = d.pop("videos")
        for videos_item_data in _videos:
            videos_item = Video.from_dict(videos_item_data)

            videos.append(videos_item)

        playlist = cls(
            name=name,
            videos=videos,
        )

        playlist.additional_properties = d
        return playlist

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
