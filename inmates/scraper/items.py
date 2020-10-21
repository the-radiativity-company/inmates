import typing
from datetime import date

import attr

from .constants import RACE_VALUES
from .validators import values_are_in_list


@attr.s
class InmateItem:
    id: str = attr.ib(default="")
    name: str = attr.ib(default="")
    sex: typing.Optional[str] = attr.ib(default=None)
    race: typing.List[str] = attr.ib(
        validator=[values_are_in_list(RACE_VALUES)], factory=list
    )
    birth_date: typing.Optional[date] = attr.ib(default=None)
    height: typing.Optional[int] = attr.ib(default=None)
    weight: typing.Optional[int] = attr.ib(default=None)
    booking_date: typing.Optional[date] = attr.ib(default=None)
    start_date: typing.Optional[date] = attr.ib(default=None)
    end_date: typing.Optional[date] = attr.ib(default=None)
    charges: typing.List[str] = attr.ib(factory=list)
    bail_amount: typing.Optional[int] = attr.ib(default=None)
    extra: typing.Dict = attr.ib(factory=dict)
