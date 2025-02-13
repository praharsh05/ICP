from datetime import datetime

# Custom Dependencies
from common_utils.scripts.common_utilities import CommonLogging
logging = CommonLogging.get_logger()
# ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****


class CommonDataUtilities:

    @staticmethod
    def format_array_field(record, c_name, c_info):
        target_values_array = []
        array_values_info = c_info["nested"]["$items"]
        array_values_type = array_values_info["details"]["target_type"]

        if not (record[c_name] == "" or record[c_name] is None):

            if isinstance(record[c_name], list):
                source_values_array = record[c_name]
                for value in source_values_array:
                    if array_values_type == "string":

                        if not (value == "" or value is None):
                            target_values_array.append(str(value))
                        else:
                            target_values_array.append(None)

                    elif array_values_type == "double" or array_values_type == "float":

                        if not (value == "" or value is None):
                            target_values_array.append(float(value))
                        else:
                            target_values_array.append(None)

                    elif array_values_type == "integer" or array_values_type == "long":

                        if not (value == "" or value is None):
                            target_values_array.append(int(value))
                        else:
                            target_values_array.append(None)

                    elif array_values_type == "date":
                        if not (value == "" or value is None):
                            try:
                                array_values_target_format = array_values_info['details']['target_format']
                            except KeyError as ex:
                                array_values_target_format = "%Y-%m-%d"

                            if isinstance(value, datetime):
                                formatted_value = value.date()
                            else:
                                formatted_value = datetime.strptime(value, array_values_target_format).date()
                        else:
                            formatted_value = None
                        target_values_array.append(formatted_value)

                    elif array_values_type == "boolean":

                        if value.lower() == "true":
                            target_values_array.append(True)
                        elif value.lower() == "false":
                            target_values_array.append(False)
                        else:
                            raise Exception(
                                "Boolean data value is not as expected(should be in true/false),"
                                " column_name:%s, column_value:%s"
                                % (c_name, record[c_name]))

                    elif array_values_type == "struct":

                        if value is not None:
                            if isinstance(value, dict):

                                target_values_array.append(CommonDataUtilities.format_data(value,
                                                           array_values_info["nested"]))

                            else:
                                raise Exception("Struct data value is not as expected(should be dictionary)"
                                                " column_name:%s, column_value:%s"
                                                % (c_name, record[c_name]))
                    else:
                        if not (value == "" or value is None):
                            target_values_array.append(str(value))
                        else:
                            target_values_array.append(None)

            else:
                raise Exception("Array data value is not as expected(should be List)"
                                " column_name:%s, column_value:%s"
                                % (c_name, record[c_name]))

        else:
            target_values_array = None

        return target_values_array

    @staticmethod
    def type_cast_value(map_key, map_value, map_value_type, map_info):

        if map_value_type == "string":
            format_v = str(map_value)
        elif map_value_type == "double" or map_value_type == "float":
            format_v = float(map_value)
        elif map_value_type == "integer" or map_value_type == "long":
            format_v = int(map_value)

        elif map_value_type == "boolean":
            if not (map_value == "" or map_value is None):

                if str(map_value).lower() == "true":
                    format_v = True
                elif str(map_value).lower() == "false":
                    format_v = False
                else:
                    raise Exception("Boolean data value is not as expected(should be in true/false),"
                                    " map_key:%s, column_value:%s"
                                    % (map_key, map_value))
            else:
                format_v = None
        elif map_value_type == "date":
            if not (map_value == "" or map_value is None):

                try:
                    target_format = map_info['details']['target_format']
                except KeyError as ex:
                    target_format = "%Y-%m-%d"

                if isinstance(map_value, datetime):
                    format_v = map_value.date()
                else:
                    format_v = datetime.strptime(map_value, target_format).date()
            else:
                format_v = None

        elif map_value_type == "array":
            format_v = CommonDataUtilities.format_data(map_value, map_info["nested"])
        elif map_value_type == "struct":
            format_v = CommonDataUtilities.format_data(map_value, map_info["nested"])
        else:
            raise Exception("Map value type is not in predefined list,"
                            " value:%s, map_value_type:%s" % (map_value, map_value_type))

        return format_v

    @staticmethod
    def format_map_field(record, c_name, c_info):

        map_info = c_info["nested"]["$items"]
        map_key_type = map_info["details"]["target_key_type"]
        map_value_type = map_info["details"]["target_value_type"]

        final_map = {}
        if not (record[c_name] == "" or record[c_name] is None):

            if isinstance(record[c_name], dict):

                for map_key in record[c_name].keys():

                    if map_key_type == "string":
                        formatted_key = str(map_key)
                    else:
                        raise Exception("Map key type should be string, c_name:%s, map_key_type:%s"
                                        % (c_name, map_key_type))

                    final_map[formatted_key] = CommonDataUtilities.type_cast_value(
                        map_key, record[c_name][map_key], map_value_type, map_info)

            else:
                raise Exception("Map field is not of type dictionary,"
                                "c_name:%s, record[c_name]:%s" % (str(c_name), str(record[c_name])))

        else:
            final_map = None

        return final_map

    @staticmethod
    def format_data(record, table_schema):

        formatted_record = {}
        for c_name, c_info in table_schema.items():

            target_name = c_info['details']['target_name']
            target_type = c_info['details']['target_type']
            # formatted_record[target_name] = record[c_name]

            try:

                if target_type == "string":
                    formatted_record[target_name] = str(record[c_name]) \
                        if not (record[c_name] == "" or record[c_name] is None) else None

                elif target_type == "double" or target_type == "float":

                    formatted_record[target_name] = float(record[c_name]) \
                        if not (record[c_name] == "" or record[c_name] is None) else None

                elif target_type == "integer" or target_type == "long":
                    formatted_record[target_name] = int(record[c_name]) \
                        if not (record[c_name] == "" or record[c_name] is None) else None

                elif target_type == "date":
                    if not (record[c_name] == "" or record[c_name] is None):

                        try:
                            target_format = c_info['details']['target_format']
                        except KeyError as ex:
                            target_format = "%Y-%m-%d"

                        if isinstance(record[c_name], datetime):
                            formatted_record[target_name] = record[c_name].date()
                        else:
                            formatted_record[target_name] = datetime.strptime(record[c_name], target_format).date()

                    else:
                        formatted_record[target_name] = None

                elif target_type == "timestamp":
                    if not (record[c_name] == "" or record[c_name] is None):

                        try:
                            target_format = c_info['details']['target_format']
                        except KeyError as ex:
                            target_format = "%Y-%m-%d %H:%M:%S"

                        if isinstance(record[c_name], datetime):
                            formatted_record[target_name] = record[c_name]
                        else:
                            formatted_record[target_name] = datetime.strptime(record[c_name], target_format)

                    else:
                        formatted_record[target_name] = None

                elif target_type == "boolean":

                    if not (record[c_name] == "" or record[c_name] is None):

                        if str(record[c_name]).lower() == "true":
                            formatted_record[target_name] = True
                        elif str(record[c_name]).lower() == "false":
                            formatted_record[target_name] = False
                        else:
                            raise Exception("Boolean data value is not as expected(should be in true/false),"
                                            " column_name:%s, column_value:%s"
                                            % (c_name, record[c_name]))
                    else:
                        formatted_record[target_name] = None

                elif target_type == "struct":
                    if record[c_name] is not None:
                        if isinstance(record[c_name], dict):

                            formatted_record[target_name] = CommonDataUtilities.format_data(
                                record[c_name], c_info["nested"])

                        else:
                            raise Exception("Struct data value is not as expected(should be dictionary)"
                                            " column_name:%s, column_value:%s"
                                            % (c_name, record[c_name]))

                elif target_type == "array":

                    formatted_record[target_name] = CommonDataUtilities.format_array_field(record, c_name, c_info)

                elif target_type == "map":
                    formatted_record[target_name] = CommonDataUtilities.format_map_field(record, c_name, c_info)

                else:
                    err_msg = 'Data type mapping error, data type is not available in predefined list' \
                              'record: %s, column_name:%s, column_type %s ' % (
                                  str(record), str(c_name), str(target_type))
                    logging.error(err_msg)
                    raise Exception(err_msg)

            except Exception as e:
                err_msg = "Type conversion/ key issue,  error %s, record_column_name: %s, record_column_value: %s" \
                          % (str(e), str(c_name), record[c_name])
                logging.error(err_msg)
                raise Exception(err_msg)

        return formatted_record

    @staticmethod
    def generate_spark_array_schema(c_info):
        field = {"containsNull": True, "type": "array"}

        array_values_info = c_info["nested"]["$items"]
        array_values_type = array_values_info["details"]["target_type"]

        if array_values_type in ("string", "double", "float", "integer", "long", "boolean", "date", "timestamp"):
            field['elementType'] = array_values_type
        elif array_values_type == "struct":
            field["elementType"] = CommonDataUtilities.create_spark_schema(array_values_info["nested"])

        return field

    @staticmethod
    def generate_spark_map_field_schema(c_info):
        sub_field = {"valueContainsNull": True, "type": "map"}

        map_info = c_info["nested"]["$items"]
        map_key_type = map_info["details"]["target_key_type"]
        map_value_type = map_info["details"]["target_value_type"]

        if map_key_type == "string":
            sub_field['keyType'] = "string"
        else:
            raise Exception("Map key type is not string type, map_key_type:%s" % map_key_type)

        if map_value_type in ("string", "double", "float", "integer", "long", "boolean", "date"):
            sub_field['valueType'] = map_value_type
        elif map_value_type == "struct":
            sub_field['valueType'] = CommonDataUtilities.create_spark_schema(map_info["nested"])
        else:
            raise Exception("Map value type is not in the predefined list, map_key_type:%s" % map_value_type)

        return sub_field

    @staticmethod
    def create_spark_schema(table_schema):
        fields = []

        for c_name, c_info in table_schema.items():
            field = {}
            target_name = c_info['details']['target_name']
            target_type = c_info['details']['target_type']

            field['name'] = target_name
            field['nullable'] = True
            field['metadata'] = {}
            try:

                if target_type in ("string", "double", "float", "integer", "long", "boolean", "date", "timestamp"):
                    field['type'] = target_type
                elif target_type == "struct":

                    field['type'] = CommonDataUtilities.create_spark_schema(c_info["nested"])

                elif target_type == "array":
                    field['type'] = CommonDataUtilities.generate_spark_array_schema(c_info)
                    pass

                elif target_type == "map":
                    field['type'] = CommonDataUtilities.generate_spark_map_field_schema(c_info)

                else:
                    err_msg = 'Data type  error, data type is not available in predefined list' \
                              'column_nam: %s, column_type %s ' % (str(c_name), str(target_type))
                    logging.error(err_msg)
                    raise Exception(err_msg)
                fields.append(field)
            except Exception as e:
                err_msg = "Spark schema creation issue,  error %s, record_column_name: %s" % (str(e), str(c_name))
                logging.error(err_msg)
                raise Exception(err_msg)

        spark_schema = {"fields": fields, "type": "struct"}
        return spark_schema
    
    @staticmethod
    def parse_selected_columns(selected_columns, column_for_partitioning: str) -> str:
        columns = "*"
        if selected_columns is None or (isinstance(selected_columns, (str, list, tuple, dict, set)) and len(selected_columns) == 0):
                return columns
        if isinstance(selected_columns, dict):
            columns = ""
            if column_for_partitioning.lower() not in (key.lower() for key in selected_columns.keys()):
                columns = f"{column_for_partitioning}, "
            columns += ", ".join(selected_columns.keys())
        elif isinstance(selected_columns, list):
            columns = ""
            if column_for_partitioning.lower() not in (key.lower() for key in selected_columns):
                    columns = f"{column_for_partitioning}, "
            columns += ", ".join(selected_columns)

        return columns
