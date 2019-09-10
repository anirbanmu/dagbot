import json, jsonschema

# JSON encoding conversion taken from http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python/6633651#6633651
def _json_list_change_encode(l, encoding):
    encoded_list = []
    for v in l:
        if isinstance(v, str):
            v = v.encode(encoding)
        elif isinstance(v, list):
            v = _json_list_change_encode(v, encoding)
        elif isinstance(v, dict):
            v = _json_dict_change_encode(v, encoding)
        encoded_list.append(v)
    return encoded_list

def _json_dict_change_encode(d, encoding='utf-8'):
    encoded_dict = {}
    for k,v in d.items():
        if isinstance(k, str):
            k = k.encode(encoding)
        if isinstance(v, str):
            v = v.encode(encoding)
        elif isinstance(v, list):
            v = _json_list_change_encode(v, encoding)
        elif isinstance(v, dict):
            v = _json_dict_change_encode(v, encoding)
        encoded_dict[k] = v
    return encoded_dict

def json_encode(json_data, encoding):
    return _json_dict_change_encode(json_data, encoding) if isinstance(json_data, dict) else _json_list_change_encode(json_data, encoding)

def default_setting_jsonschema_validator(validator_class):
    validate_properties = validator_class.VALIDATORS['properties']

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if 'default' in subschema:
                instance.setdefault(property, subschema['default'])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return jsonschema.validators.extend(validator_class, {'properties': set_defaults})

def validate_load_schema(schema_path):
    with open(schema_path, 'r') as schema_file:
        schema = json.load(schema_file)
        jsonschema.Draft4Validator.check_schema(schema)
        return schema

def validate_default_json(schema_path, json_data, encoding):
    schema = validate_load_schema(schema_path)
    validator = default_setting_jsonschema_validator(jsonschema.Draft4Validator)
    validator(schema).validate(json_data) # Throws on error
    return json_data

def validate_load_default_json(schema_path, json_path, encoding):
    with open(json_path, 'r') as config_file:
        config = json.load(config_file)
        return validate_default_json(schema_path, config, encoding)
