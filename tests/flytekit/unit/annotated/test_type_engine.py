import os
import typing
from datetime import timedelta

from flytekit.annotated.type_engine import TypeEngine, ListTransformer, DictTransformer, SimpleTransformer, \
    PathLikeTransformer
from flytekit.models import types as model_types


def test_type_engine():
    t = int
    lt = TypeEngine.to_literal_type(t)
    assert lt.simple == model_types.SimpleType.INTEGER

    t = typing.Dict[str, typing.List[typing.Dict[str, timedelta]]]
    lt = TypeEngine.to_literal_type(t)
    assert lt.map_value_type.collection_type.map_value_type.simple == model_types.SimpleType.DURATION


def test_named_tuple():
    t = typing.NamedTuple("Outputs", [("x_str", str), ("y_int", int)])
    var_map = TypeEngine.named_tuple_to_variable_map(t)
    assert var_map.variables["x_str"].type.simple == model_types.SimpleType.STRING
    assert var_map.variables["y_int"].type.simple == model_types.SimpleType.INTEGER


def test_type_resolution():
    assert type(TypeEngine.get_transformer(typing.List[int])) == ListTransformer
    assert type(TypeEngine.get_transformer(typing.List)) == ListTransformer
    assert type(TypeEngine.get_transformer(list)) == ListTransformer

    assert type(TypeEngine.get_transformer(typing.Dict[str, int])) == DictTransformer
    assert type(TypeEngine.get_transformer(typing.Dict)) == DictTransformer
    assert type(TypeEngine.get_transformer(dict)) == DictTransformer

    assert type(TypeEngine.get_transformer(int)) == SimpleTransformer

    assert type(TypeEngine.get_transformer(os.PathLike)) == PathLikeTransformer
