from typing import Any

from omegaconf import MISSING, Container, DictConfig, ListConfig, Node, ValueNode
from omegaconf.errors import ConfigTypeError, InterpolationToMissingValueError
from omegaconf.nodes import InterpolationResultNode

from ._utils import (
    _DEFAULT_MARKER_,
    _ensure_container,
    _get_value,
    is_primitive_container,
    is_structured_config,
)


def _resolve_container_value(cfg: Container, key: Any, strict=True) -> None:
    node = cfg._get_child(key)
    assert isinstance(node, Node)
    if node._is_interpolation():
        try:
            resolved = node._dereference_node()
        except InterpolationToMissingValueError:
            if strict:
                node._set_value(MISSING)
        else:
            if isinstance(resolved, Container):
                _resolve(resolved, strict=strict)
            if isinstance(resolved, InterpolationResultNode):
                resolved_value = _get_value(resolved)
                if is_primitive_container(resolved_value) or is_structured_config(
                    resolved_value
                ):
                    resolved = _ensure_container(resolved_value)
            if isinstance(resolved, Container) and isinstance(node, ValueNode):
                cfg[key] = resolved
            else:
                node._set_value(_get_value(resolved))
    else:
        _resolve(node, strict=strict)


def _resolve(cfg: Node, strict=True) -> Node:
    assert isinstance(cfg, Node)
    if cfg._is_interpolation():
        try:
            resolved = cfg._dereference_node()
        except InterpolationToMissingValueError:
            if strict:
                cfg._set_value(MISSING)
        else:
            cfg._set_value(resolved._value())

    if isinstance(cfg, DictConfig):
        for k in cfg.keys():
            _resolve_container_value(cfg, k, strict=strict)

    elif isinstance(cfg, ListConfig):
        for i in range(len(cfg)):
            _resolve_container_value(cfg, i, strict=strict)

    return cfg


def select_value(
    cfg: Container,
    key: str,
    *,
    default: Any = _DEFAULT_MARKER_,
    throw_on_resolution_failure: bool = True,
    throw_on_missing: bool = False,
    absolute_key: bool = False,
) -> Any:
    node = select_node(
        cfg=cfg,
        key=key,
        throw_on_resolution_failure=throw_on_resolution_failure,
        throw_on_missing=throw_on_missing,
        absolute_key=absolute_key,
    )

    node_not_found = node is None
    if node_not_found or node._is_missing():
        if default is not _DEFAULT_MARKER_:
            return default
        else:
            return None

    return _get_value(node)


def select_node(
    cfg: Container,
    key: str,
    *,
    throw_on_resolution_failure: bool = True,
    throw_on_missing: bool = False,
    absolute_key: bool = False,
) -> Any:
    try:
        # for non relative keys, the interpretation can be:
        # 1. relative to cfg
        # 2. relative to the config root
        # This is controlled by the absolute_key flag. By default, such keys are relative to cfg.
        if not absolute_key and not key.startswith("."):
            key = f".{key}"

        cfg, key = cfg._resolve_key_and_root(key)
        _root, _last_key, node = cfg._select_impl(
            key,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )
    except ConfigTypeError:
        return None

    return node
