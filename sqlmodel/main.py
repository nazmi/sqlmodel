import weakref
from typing import (
    AbstractSet,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo as PydanticFieldInfo
from sqlalchemy import (
    Column,
    inspect,
)
from sqlalchemy.orm import (
    RelationshipProperty,
    declared_attr,
    registry,
    relationship,
)
from sqlalchemy.orm.attributes import set_attribute
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.instrumentation import is_instrumented
from sqlalchemy.sql.schema import MetaData

from .compat import (
    IS_PYDANTIC_V2,
    ModelMetaclass,
    NoArgAnyCallable,
    PydanticModelConfig,
    PydanticUndefined,
    PydanticUndefinedType,
    SQLModelConfig,
    class_dict_is_table,
    cls_is_table,
    get_annotations,
    get_column_from_field,
    get_config_value,
    get_model_fields,
    get_relationship_to,
    set_config_value,
    set_empty_defaults,
    set_fields_set,
)

if not IS_PYDANTIC_V2:
    from pydantic.errors import ConfigError, DictError
    from pydantic.main import validate_model
    from pydantic.utils import ROOT_KEY, Representation
else:
    from pydantic.v1.utils import ROOT_KEY, Representation


_T = TypeVar("_T")


def __dataclass_transform__(
    *,
    eq_default: bool = True,
    order_default: bool = False,
    kw_only_default: bool = False,
    field_descriptors: Tuple[Union[type, Callable[..., Any]], ...] = (()),
) -> Callable[[_T], _T]:
    return lambda a: a


class FieldInfo(PydanticFieldInfo):
    def __init__(self, default: Any = PydanticUndefined, **kwargs: Any) -> None:
        primary_key = kwargs.pop("primary_key", False)
        nullable = kwargs.pop("nullable", PydanticUndefined)
        foreign_key = kwargs.pop("foreign_key", PydanticUndefined)
        unique = kwargs.pop("unique", False)
        index = kwargs.pop("index", PydanticUndefined)
        sa_type = kwargs.pop("sa_type", PydanticUndefined)
        sa_column = kwargs.pop("sa_column", PydanticUndefined)
        sa_column_args = kwargs.pop("sa_column_args", PydanticUndefined)
        sa_column_kwargs = kwargs.pop("sa_column_kwargs", PydanticUndefined)
        if sa_column is not PydanticUndefined:
            if sa_column_args is not PydanticUndefined:
                raise RuntimeError(
                    "Passing sa_column_args is not supported when "
                    "also passing a sa_column"
                )
            if sa_column_kwargs is not PydanticUndefined:
                raise RuntimeError(
                    "Passing sa_column_kwargs is not supported when "
                    "also passing a sa_column"
                )
            if primary_key is not PydanticUndefined:
                raise RuntimeError(
                    "Passing primary_key is not supported when "
                    "also passing a sa_column"
                )
            if nullable is not PydanticUndefined:
                raise RuntimeError(
                    "Passing nullable is not supported when " "also passing a sa_column"
                )
            if foreign_key is not PydanticUndefined:
                raise RuntimeError(
                    "Passing foreign_key is not supported when "
                    "also passing a sa_column"
                )
            if unique is not PydanticUndefined:
                raise RuntimeError(
                    "Passing unique is not supported when also passing a sa_column"
                )
            if index is not PydanticUndefined:
                raise RuntimeError(
                    "Passing index is not supported when also passing a sa_column"
                )
            if sa_type is not PydanticUndefined:
                raise RuntimeError(
                    "Passing sa_type is not supported when also passing a sa_column"
                )
        super().__init__(default=default, **kwargs)
        self.primary_key = primary_key
        self.nullable = nullable
        self.foreign_key = foreign_key
        self.unique = unique
        self.index = index
        self.sa_type = sa_type
        self.sa_column = sa_column
        self.sa_column_args = sa_column_args
        self.sa_column_kwargs = sa_column_kwargs


class RelationshipInfo(Representation):
    def __init__(
        self,
        *,
        back_populates: Optional[str] = None,
        link_model: Optional[Any] = None,
        sa_relationship: Optional[RelationshipProperty] = None,  # type: ignore
        sa_relationship_args: Optional[Sequence[Any]] = None,
        sa_relationship_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if sa_relationship is not None:
            if sa_relationship_args is not None:
                raise RuntimeError(
                    "Passing sa_relationship_args is not supported when "
                    "also passing a sa_relationship"
                )
            if sa_relationship_kwargs is not None:
                raise RuntimeError(
                    "Passing sa_relationship_kwargs is not supported when "
                    "also passing a sa_relationship"
                )
        self.back_populates = back_populates
        self.link_model = link_model
        self.sa_relationship = sa_relationship
        self.sa_relationship_args = sa_relationship_args
        self.sa_relationship_kwargs = sa_relationship_kwargs


@overload
def Field(
    default: Any = PydanticUndefined,
    *,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    include: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    unique_items: Optional[bool] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_mutation: bool = True,
    regex: Optional[str] = None,
    discriminator: Optional[str] = None,
    repr: bool = True,
    primary_key: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    foreign_key: Any = PydanticUndefined,
    unique: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    nullable: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    index: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    sa_type: Union[Type[Any], PydanticUndefinedType] = PydanticUndefined,
    sa_column_args: Union[Sequence[Any], PydanticUndefinedType] = PydanticUndefined,
    sa_column_kwargs: Union[
        Mapping[str, Any], PydanticUndefinedType
    ] = PydanticUndefined,
    schema_extra: Optional[Dict[str, Any]] = None,
) -> Any:
    ...


@overload
def Field(
    default: Any = PydanticUndefined,
    *,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    include: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    unique_items: Optional[bool] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_mutation: bool = True,
    regex: Optional[str] = None,
    discriminator: Optional[str] = None,
    repr: bool = True,
    sa_column: Union[Column, PydanticUndefinedType] = PydanticUndefined,  # type: ignore
    schema_extra: Optional[Dict[str, Any]] = None,
) -> Any:
    ...


def Field(
    default: Any = PydanticUndefined,
    *,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    include: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    unique_items: Optional[bool] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_mutation: bool = True,
    regex: Optional[str] = None,
    discriminator: Optional[str] = None,
    repr: bool = True,
    primary_key: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    foreign_key: Any = PydanticUndefined,
    unique: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    nullable: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    index: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    sa_type: Union[Type[Any], PydanticUndefinedType] = PydanticUndefined,
    sa_column: Union[Column, PydanticUndefinedType] = PydanticUndefined,  # type: ignore
    sa_column_args: Union[Sequence[Any], PydanticUndefinedType] = PydanticUndefined,
    sa_column_kwargs: Union[
        Mapping[str, Any], PydanticUndefinedType
    ] = PydanticUndefined,
    schema_extra: Optional[Dict[str, Any]] = None,
) -> Any:
    current_schema_extra = schema_extra or {}
    field_info = FieldInfo(
        default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_items=min_items,
        max_items=max_items,
        unique_items=unique_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        discriminator=discriminator,
        repr=repr,
        primary_key=primary_key,
        foreign_key=foreign_key,
        unique=unique,
        nullable=nullable,
        index=index,
        sa_type=sa_type,
        sa_column=sa_column,
        sa_column_args=sa_column_args,
        sa_column_kwargs=sa_column_kwargs,
        **current_schema_extra,
    )
    return field_info


@overload
def Relationship(
    *,
    back_populates: Optional[str] = None,
    link_model: Optional[Any] = None,
    sa_relationship_args: Optional[Sequence[Any]] = None,
    sa_relationship_kwargs: Optional[Mapping[str, Any]] = None,
) -> Any:
    ...


@overload
def Relationship(
    *,
    back_populates: Optional[str] = None,
    link_model: Optional[Any] = None,
    sa_relationship: Optional[RelationshipProperty] = None,  # type: ignore
) -> Any:
    ...


def Relationship(
    *,
    back_populates: Optional[str] = None,
    link_model: Optional[Any] = None,
    sa_relationship: Optional[RelationshipProperty] = None,
    sa_relationship_args: Optional[Sequence[Any]] = None,
    sa_relationship_kwargs: Optional[Mapping[str, Any]] = None,
) -> Any:
    relationship_info = RelationshipInfo(
        back_populates=back_populates,
        link_model=link_model,
        sa_relationship=sa_relationship,
        sa_relationship_args=sa_relationship_args,
        sa_relationship_kwargs=sa_relationship_kwargs,
    )
    return relationship_info


@__dataclass_transform__(kw_only_default=True, field_descriptors=(Field, FieldInfo))
class SQLModelMetaclass(ModelMetaclass, DeclarativeMeta):
    __sqlmodel_relationships__: Dict[str, RelationshipInfo]
    if IS_PYDANTIC_V2:
        model_config: SQLModelConfig
        model_fields: Dict[str, FieldInfo]
    else:
        __config__: Type[SQLModelConfig]
        __fields__: Dict[str, FieldInfo]

    # Replicate SQLAlchemy
    def __setattr__(cls, name: str, value: Any) -> None:
        if get_config_value(cls, "table", False):
            DeclarativeMeta.__setattr__(cls, name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(cls, name: str) -> None:
        if get_config_value(cls, "table", False):
            DeclarativeMeta.__delattr__(cls, name)
        else:
            super().__delattr__(name)

    # From Pydantic
    def __new__(
        cls,
        name: str,
        bases: Tuple[Type[Any], ...],
        class_dict: Dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        relationships: Dict[str, RelationshipInfo] = {}
        dict_for_pydantic = {}
        original_annotations = get_annotations(class_dict)
        pydantic_annotations = {}
        relationship_annotations = {}
        for k, v in class_dict.items():
            if isinstance(v, RelationshipInfo):
                relationships[k] = v
            else:
                dict_for_pydantic[k] = v
        for k, v in original_annotations.items():
            if k in relationships:
                relationship_annotations[k] = v
            else:
                pydantic_annotations[k] = v
        dict_used = {
            **dict_for_pydantic,
            "__weakref__": None,
            "__sqlmodel_relationships__": relationships,
            "__annotations__": pydantic_annotations,
        }
        # Duplicate logic from Pydantic to filter config kwargs because if they are
        # passed directly including the registry Pydantic will pass them over to the
        # superclass causing an error
        allowed_config_kwargs: Set[str] = {
            key
            for key in dir(PydanticModelConfig)
            if not (
                key.startswith("__") and key.endswith("__")
            )  # skip dunder methods and attributes
        }
        config_kwargs = {
            key: kwargs[key] for key in kwargs.keys() & allowed_config_kwargs
        }
        if class_dict_is_table(class_dict, kwargs):
            set_empty_defaults(pydantic_annotations, dict_used)

        new_cls: Type["SQLModelMetaclass"] = super().__new__(
            cls, name, bases, dict_used, **config_kwargs
        )
        new_cls.__annotations__ = {
            **relationship_annotations,
            **pydantic_annotations,
            **new_cls.__annotations__,
        }

        def get_config(name: str) -> Any:
            config_class_value = get_config_value(new_cls, name, PydanticUndefined)
            if config_class_value is not PydanticUndefined:
                return config_class_value
            kwarg_value = kwargs.get(name, PydanticUndefined)
            if kwarg_value is not PydanticUndefined:
                return kwarg_value
            return PydanticUndefined

        config_table = get_config("table")
        if config_table is True:
            # If it was passed by kwargs, ensure it's also set in config
            set_config_value(new_cls, "table", config_table)
            for k, v in get_model_fields(new_cls).items():
                col = get_column_from_field(v)
                setattr(new_cls, k, col)
            # Set a config flag to tell FastAPI that this should be read with a field
            # in orm_mode instead of preemptively converting it to a dict.
            # This could be done by reading new_cls.model_config['table'] in FastAPI, but
            # that's very specific about SQLModel, so let's have another config that
            # other future tools based on Pydantic can use.
            set_config_value(
                new_cls, "read_from_attributes", True, v1_parameter="read_with_orm_mode"
            )

        config_registry = get_config("registry")
        if config_registry is not PydanticUndefined:
            config_registry = cast(registry, config_registry)
            # If it was passed by kwargs, ensure it's also set in config
            set_config_value(new_cls, "registry", config_table)
            setattr(new_cls, "_sa_registry", config_registry)  # noqa: B010
            setattr(new_cls, "metadata", config_registry.metadata)  # noqa: B010
            setattr(new_cls, "__abstract__", True)  # noqa: B010
        return new_cls

    # Override SQLAlchemy, allow both SQLAlchemy and plain Pydantic models
    def __init__(
        cls, classname: str, bases: Tuple[type, ...], dict_: Dict[str, Any], **kw: Any
    ) -> None:
        # Only one of the base classes (or the current one) should be a table model
        # this allows FastAPI cloning a SQLModel for the response_model without
        # trying to create a new SQLAlchemy, for a new table, with the same name, that
        # triggers an error
        base_is_table = any(cls_is_table(base) for base in bases)
        if cls_is_table(cls) and not base_is_table:
            for rel_name, rel_info in cls.__sqlmodel_relationships__.items():
                if rel_info.sa_relationship:
                    # There's a SQLAlchemy relationship declared, that takes precedence
                    # over anything else, use that and continue with the next attribute
                    setattr(cls, rel_name, rel_info.sa_relationship)  # Fix #315
                    continue
                ann = cls.__annotations__[rel_name]
                relationship_to = get_relationship_to(rel_name, rel_info, ann, cls)
                rel_kwargs: Dict[str, Any] = {}
                if rel_info.back_populates:
                    rel_kwargs["back_populates"] = rel_info.back_populates
                if rel_info.link_model:
                    ins = inspect(rel_info.link_model)
                    local_table = getattr(ins, "local_table")  # noqa: B009
                    if local_table is None:
                        raise RuntimeError(
                            "Couldn't find the secondary table for "
                            f"model {rel_info.link_model}"
                        )
                    rel_kwargs["secondary"] = local_table
                rel_args: List[Any] = []
                if rel_info.sa_relationship_args:
                    rel_args.extend(rel_info.sa_relationship_args)
                if rel_info.sa_relationship_kwargs:
                    rel_kwargs.update(rel_info.sa_relationship_kwargs)
                rel_value = relationship(relationship_to, *rel_args, **rel_kwargs)
                setattr(cls, rel_name, rel_value)  # Fix #315
            # SQLAlchemy no longer uses dict_
            # Ref: https://github.com/sqlalchemy/sqlalchemy/commit/428ea01f00a9cc7f85e435018565eb6da7af1b77
            # Tag: 1.4.36
            DeclarativeMeta.__init__(cls, classname, bases, dict_, **kw)
        else:
            ModelMetaclass.__init__(cls, classname, bases, dict_, **kw)


class_registry = weakref.WeakValueDictionary()  # type: ignore

default_registry = registry()


def _value_items_is_true(v: Any) -> bool:
    # Re-implement Pydantic's ValueItems.is_true() as it hasn't been released as of
    # the current latest, Pydantic 1.8.2
    return v is True or v is ...


_TSQLModel = TypeVar("_TSQLModel", bound="SQLModel")


class SQLModel(BaseModel, metaclass=SQLModelMetaclass, registry=default_registry):
    # SQLAlchemy needs to set weakref(s), Pydantic will set the other slots values
    __slots__ = ("__weakref__",)
    __tablename__: ClassVar[Union[str, Callable[..., str]]]
    __sqlmodel_relationships__: ClassVar[Dict[str, RelationshipProperty]]
    __name__: ClassVar[str]
    metadata: ClassVar[MetaData]
    __allow_unmapped__ = True  # https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-20-step-six

    if IS_PYDANTIC_V2:
        model_config = SQLModelConfig(from_attributes=True)
    else:

        class Config:
            orm_mode = True

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        new_object = super().__new__(cls)
        # SQLAlchemy doesn't call __init__ on the base class
        # Ref: https://docs.sqlalchemy.org/en/14/orm/constructors.html
        # Set __fields_set__ here, that would have been set when calling __init__
        # in the Pydantic model so that when SQLAlchemy sets attributes that are
        # added (e.g. when querying from DB) to the __fields_set__, this already exists
        set_fields_set(new_object, set())
        return new_object

    def __init__(__pydantic_self__, **data: Any) -> None:
        # Uses something other than `self` the first arg to allow "self" as a
        # settable attribute
        if IS_PYDANTIC_V2:
            old_dict = __pydantic_self__.__dict__.copy()
            super().__init__(**data)  # noqa
            __pydantic_self__.__dict__ = {**old_dict, **__pydantic_self__.__dict__}
            non_pydantic_keys = data.keys() - __pydantic_self__.model_fields
        else:
            values, fields_set, validation_error = validate_model(
                __pydantic_self__.__class__, data
            )
            # Only raise errors if not a SQLModel model
            if (
                not getattr(__pydantic_self__.__config__, "table", False)  # noqa
                and validation_error
            ):
                raise validation_error
            # Do not set values as in Pydantic, pass them through setattr, so SQLAlchemy
            # can handle them
            # object.__setattr__(__pydantic_self__, '__dict__', values)
            for key, value in values.items():
                setattr(__pydantic_self__, key, value)
            object.__setattr__(__pydantic_self__, "__fields_set__", fields_set)
            non_pydantic_keys = data.keys() - values.keys()

        for key in non_pydantic_keys:
            if key in __pydantic_self__.__sqlmodel_relationships__:
                setattr(__pydantic_self__, key, data[key])

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_sa_instance_state"}:
            self.__dict__[name] = value
            return
        else:
            # Set in SQLAlchemy, before Pydantic to trigger events and updates
            if get_config_value(self, "table", False) and is_instrumented(self, name):
                set_attribute(self, name, value)
            # Set in Pydantic model to trigger possible validation changes, only for
            # non relationship values
            if name not in self.__sqlmodel_relationships__:
                super().__setattr__(name, value)

    def __repr_args__(self) -> Sequence[Tuple[Optional[str], Any]]:
        # Don't show SQLAlchemy private attributes
        return [
            (k, v)
            for k, v in super().__repr_args__()
            if not (isinstance(k, str) and k.startswith("_sa_"))
        ]

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    if IS_PYDANTIC_V2:

        @classmethod
        def model_validate(
            cls: type[_TSQLModel],
            obj: Any,
            *,
            strict: bool | None = None,
            from_attributes: bool | None = None,
            context: dict[str, Any] | None = None,
        ) -> _TSQLModel:
            # Somehow model validate doesn't call __init__ so it would remove our init logic
            validated = super().model_validate(
                obj, strict=strict, from_attributes=from_attributes, context=context
            )
            return cls(**validated.model_dump(exclude_unset=True))

    else:

        @classmethod
        def from_orm(
            cls: Type[_TSQLModel], obj: Any, update: Optional[Dict[str, Any]] = None
        ) -> _TSQLModel:
            # Duplicated from Pydantic
            if not cls.__config__.orm_mode:  # noqa
                raise ConfigError(
                    "You must have the config attribute orm_mode=True to use from_orm"
                )
            obj = (
                {ROOT_KEY: obj}
                if cls.__custom_root_type__  # noqa
                else cls._decompose_class(obj)  # noqa
            )
            # SQLModel, support update dict
            if update is not None:
                obj = {**obj, **update}
            # End SQLModel support dict
            if not getattr(cls.__config__, "table", False):  # noqa
                # If not table, normal Pydantic code
                m: _TSQLModel = cls.__new__(cls)
            else:
                # If table, create the new instance normally to make SQLAlchemy create
                # the _sa_instance_state attribute
                m = cls()
            values, fields_set, validation_error = validate_model(cls, obj)
            if validation_error:
                raise validation_error
            # Updated to trigger SQLAlchemy internal handling
            if not getattr(cls.__config__, "table", False):  # noqa
                object.__setattr__(m, "__dict__", values)
            else:
                for key, value in values.items():
                    setattr(m, key, value)
            # Continue with standard Pydantic logic
            object.__setattr__(m, "__fields_set__", fields_set)
            m._init_private_attributes()  # noqa
            return m

        @classmethod
        def parse_obj(
            cls: Type[_TSQLModel], obj: Any, update: Optional[Dict[str, Any]] = None
        ) -> _TSQLModel:
            obj = cls._enforce_dict_if_root(obj)  # noqa
            # SQLModel, support update dict
            if update is not None:
                obj = {**obj, **update}
            # End SQLModel support dict
            return super().parse_obj(obj)

        # From Pydantic, override to enforce validation with dict
        @classmethod
        def validate(cls: Type[_TSQLModel], value: Any) -> _TSQLModel:
            if isinstance(value, cls):
                return (
                    value.copy()
                    if cls.__config__.copy_on_model_validation
                    else value  # noqa
                )

            value = cls._enforce_dict_if_root(value)
            if isinstance(value, dict):
                values, fields_set, validation_error = validate_model(cls, value)
                if validation_error:
                    raise validation_error
                model = cls(**value)
                # Reset fields set, this would have been done in Pydantic in __init__
                object.__setattr__(model, "__fields_set__", fields_set)
                return model
            elif cls.__config__.orm_mode:  # noqa
                return cls.from_orm(value)
            elif cls.__custom_root_type__:  # noqa
                return cls.parse_obj(value)
            else:
                try:
                    value_as_dict = dict(value)
                except (TypeError, ValueError) as e:
                    raise DictError() from e
                return cls(**value_as_dict)

        # From Pydantic, override to only show keys from fields, omit SQLAlchemy attributes
        def _calculate_keys(
            self,
            include: Optional[Mapping[Union[int, str], Any]],
            exclude: Optional[Mapping[Union[int, str], Any]],
            exclude_unset: bool,
            update: Optional[Dict[str, Any]] = None,
        ) -> Optional[AbstractSet[str]]:
            if include is None and exclude is None and not exclude_unset:
                # Original in Pydantic:
                # return None
                # Updated to not return SQLAlchemy attributes
                # Do not include relationships as that would easily lead to infinite
                # recursion, or traversing the whole database
                return (
                    self.__fields__.keys()  # noqa
                )  # | self.__sqlmodel_relationships__.keys()

            keys: AbstractSet[str]
            if exclude_unset:
                keys = self.__fields_set__.copy()  # noqa
            else:
                # Original in Pydantic:
                # keys = self.__dict__.keys()
                # Updated to not return SQLAlchemy attributes
                # Do not include relationships as that would easily lead to infinite
                # recursion, or traversing the whole database
                keys = (
                    self.__fields__.keys()  # noqa
                )  # | self.__sqlmodel_relationships__.keys()
            if include is not None:
                keys &= include.keys()

            if update:
                keys -= update.keys()

            if exclude:
                keys -= {k for k, v in exclude.items() if _value_items_is_true(v)}

            return keys
