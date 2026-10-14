from collections.abc import Sequence
from typing import Any, Protocol, Self, cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql.base import ExecutableOption

from man.kit.pagination import PaginationParams


class ModelIDProtocol[ID_TYPE](Protocol):
    id: Mapped[ID_TYPE]


type Options = Sequence[ExecutableOption]


class RepositoryProtocol[M](Protocol):
    model: type[M]

    async def get_one(self, statement: Select[M]) -> M: ...

    async def get_one_or_none(self, statement: Select[M]) -> M | None: ...

    async def get_all(self, statement: Select[M]) -> Sequence[M]: ...

    async def get_by_id(self, id: Any) -> M | None: ...

    def get_base_statement(self) -> Select[M]: ...

    async def create(self, object: M, *, flush: bool = False) -> M: ...

    async def update(
        self,
        object: M,
        *,
        update_dict: dict[str, Any] | None = None,
        flush: bool = False,
    ) -> M: ...


class RepositoryBase[M: ModelIDProtocol[Any]]:
    model: type[M]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_one(self, statement: Select[M]) -> M:
        result = await self.session.execute(statement)
        return result.unique().scalar_one()

    async def get_one_or_none(self, statement: Select[M]) -> M | None:
        result = await self.session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def get_all(self, statement: Select[M]) -> Sequence[M]:
        result = await self.session.execute(statement)
        return result.scalars().unique().all()

    async def get_by_id(self, id: Any) -> M | None:
        statement = self.get_base_statement().where(self.model.id == id)
        return await self.get_one_or_none(statement)

    async def paginate(
        self,
        statement: Select[M],
        pagination: PaginationParams,
    ) -> tuple[list[M], int]:
        count_statement = select(func.count()).select_from(statement.subquery())

        count_result = await self.session.execute(count_statement)
        count = count_result.scalar_one()

        limit = cast(int, pagination.first if pagination.first else pagination.last)
        paginated_statement = statement.limit(limit)

        if pagination.first:
            paginated_statement = paginated_statement.order_by(self.model.id.desc())
        else:
            paginated_statement = paginated_statement.order_by(self.model.id.asc())

        if pagination.after:
            paginated_statement = paginated_statement.where(
                self.model.id < pagination.after
            )

        if pagination.before:
            paginated_statement = paginated_statement.where(
                self.model.id > pagination.before
            )

        results = await self.session.execute(paginated_statement)
        items = list(results.unique().scalars().all())

        return items, count

    def get_base_statement(self) -> Select[M]:
        return select(self.model)

    async def create(self, object: M, *, flush: bool = False) -> M:
        self.session.add(object)

        if flush:
            await self.session.flush()

        return object

    async def update(
        self,
        object: M,
        *,
        update_dict: dict[str, Any] | None = None,
        flush: bool = False,
    ) -> M:
        if update_dict is not None:
            for attr, value in update_dict.items():
                setattr(object, attr, value)

                try:
                    flag_modified(object, attr)
                except KeyError:
                    pass

        self.session.add(object)

        if flush:
            await self.session.flush()

        return object

    @classmethod
    def from_session(cls, session: AsyncSession) -> Self:
        return cls(session)


class RepositoryIDMixin[MODEL_ID: ModelIDProtocol[Any], ID_TYPE]:
    async def get_by_id(
        self: RepositoryProtocol[MODEL_ID], id: ID_TYPE, *, options: Options = ()
    ) -> MODEL_ID | None:
        statement = (
            self.get_base_statement().where(self.model.id == id).options(*options)
        )

        return await self.get_one_or_none(statement)
