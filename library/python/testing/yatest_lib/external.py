from __future__ import absolute_import

import copy

from . import tools


def apply(func, value):
    """
    Applies func to every possible member of value
    :param value: could be either a primitive object or a complex one (list, dicts)
    :param func: func to be applied
    :return:
    """
    def _apply(func, value, value_path):
        if value_path is None:
            value_path = []

        if isinstance(value, list) or isinstance(value, tuple):
            res = []
            for ind, item in enumerate(value):
                path = copy.copy(value_path)
                path.append(ind)
                res.append(_apply(func, item, path))
        elif isinstance(value, dict):
            if is_external(value):
                # this is a special serialized object pointing to some external place
                res = func(value, value_path)
            else:
                res = {}
                for key, val in sorted(value.items(), key=lambda dict_item: dict_item[0]):
                    path = copy.copy(value_path)
                    path.append(key)
                    res[key] = _apply(func, val, path)
        else:
            res = func(value, value_path)
        return res
    return _apply(func, value, None)


def serialize(value):
    """
    Serialize value to json-convertible object
    Ensures that all components of value can be serialized to json
    :param value: object to be serialized
    """
    def _serialize(val, _):
        if val is None:
            return val
        if isinstance(val, basestring):
            return tools.to_utf8(val)
        if type(val) in [int, float, bool, long]:
            return val
        if is_external(val):
            return dict(val)
        raise ValueError("Cannot serialize value '{}' of type {}".format(val, type(val)))
    return apply(_serialize, value)


def is_external(value):
    return isinstance(value, dict) and "uri" in value.keys()


class ExternalSchema(object):
    File = "file"
    SandboxResource = "sbr"
    Delayed = "delayed"
    HTTP = "http"


class CanonicalObject(dict):
    def __iter__(self):
        raise TypeError("Iterating canonical object is not implemented")


class ExternalDataInfo(object):

    def __init__(self, data):
        assert is_external(data)
        self._data = data

    def __str__(self):
        type_str = "File" if self.is_file else "Sandbox resource"
        return "{}({})".format(type_str, self.path)

    def __repr__(self):
        return str(self)

    @property
    def uri(self):
        return self._data["uri"]

    @property
    def checksum(self):
        return self._data.get("checksum")

    @property
    def is_file(self):
        return self.uri.startswith(ExternalSchema.File)

    @property
    def is_sandbox_resource(self):
        return self.uri.startswith(ExternalSchema.SandboxResource)

    @property
    def is_delayed(self):
        return self.uri.startswith(ExternalSchema.Delayed)

    @property
    def is_http(self):
        return self.uri.startswith(ExternalSchema.HTTP)

    @property
    def path(self):
        assert self.uri.count("://") == 1, self.uri
        _, path = self.uri.split("://")
        return path

    @property
    def size(self):
        return self._data.get("size")

    def serialize(self):
        return self._data

    @classmethod
    def _serialize(cls, schema, path, checksum=None, attrs=None):
        res = CanonicalObject({"uri": "{}://{}".format(schema, path)})
        if checksum:
            res["checksum"] = checksum
        if attrs:
            res.update(attrs)
        return res

    @classmethod
    def serialize_file(cls, path, checksum=None, diff_tool=None, local=False, diff_file_name=None, diff_tool_timeout=None, size=None):
        attrs = {}
        if diff_tool:
            attrs["diff_tool"] = diff_tool
        if local:
            attrs["local"] = local
        if diff_file_name:
            attrs["diff_file_name"] = diff_file_name
        if diff_tool_timeout:
            attrs["diff_tool_timeout"] = diff_tool_timeout
        if size is not None:
            attrs["size"] = size
        return cls._serialize(ExternalSchema.File, path, checksum, attrs=attrs)

    @classmethod
    def serialize_resource(cls, id, checksum=None):
        return cls._serialize(ExternalSchema.SandboxResource, id, checksum)

    @classmethod
    def serialize_delayed(cls, upload_id, checksum):
        return cls._serialize(ExternalSchema.Delayed, upload_id, checksum)

    def get(self, key, default=None):
        return self._data.get(key, default)
