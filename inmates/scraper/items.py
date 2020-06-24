import typing
from datetime import date

import attr

from .constants import RACE_VALUES


def values_are_in_list(values_list):
    """Create a validator based on an allowed list"""

    def inner_value_is_in_list(instance, attribute, value):
        if not all([v in values_list for v in value]):
            raise ValueError(f"Provided value not in allowed list: {values_list}")

    return inner_value_is_in_list


@attr.s
class InmateItem:
    id: str = attr.ib(default="")
    name: str = attr.ib(default="")
    race: typing.List[str] = attr.ib(
        validator=[values_are_in_list(RACE_VALUES)], factory=list
    )
    height: typing.Optional[int] = attr.ib(default=None)
    weight: typing.Optional[int] = attr.ib(default=None)
    start_date: typing.Optional[date] = attr.ib(default=None)
    end_date: typing.Optional[date] = attr.ib(default=None)
    extra: typing.Dict = attr.ib(factory=dict)
