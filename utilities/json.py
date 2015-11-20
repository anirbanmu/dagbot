import jsonschema

# JSON encoding conversion taken from http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python/6633651#6633651
def _json_list_change_encode(l, encoding):
    encoded_list = []
    for v in l:
        if isinstance(v, unicode):
            v = v.encode(encoding)
        elif isinstance(v, list):
            v = _json_list_change_encode(v, encoding)
        elif isinstance(v, dict):
            v = _json_dict_change_encode(v, encoding)
        encoded_list.append(v)
    return encoded_list

def _json_dict_change_encode(d, encoding='utf-8'):
    encoded_dict = {}
    for k,v in d.iteritems():
        if isinstance(k, unicode):
            k = k.encode(encoding)
        if isinstance(v, unicode):
            v = v.encode(encoding)
        elif isinstance(v, list):
            v = _json_list_change_encode(v, encoding)
        elif isinstance(v, dict):
            v = _json_dict_change_encode(v, encoding)
        encoded_dict[k] = v
    return encoded_dict

def json_encode(json_dict, encoding):
    return _json_dict_change_encode(json_dict, encoding)

def default_setting_jsonschema_validator(validator_class):
    validate_properties = validator_class.VALIDATORS['properties']

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.iteritems():
            if 'default' in subschema:
                instance.setdefault(property, subschema['default'])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return jsonschema.validators.extend(validator_class, {'properties': set_defaults})