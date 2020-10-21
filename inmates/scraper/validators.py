def values_are_in_list(values_list):
    """Create a validator based on an allowed list"""

    def inner_value_is_in_list(instance, attribute, value):
        if not all([v in values_list for v in value]):
            raise ValueError(f"Provided value not in allowed list: {values_list}")

    return inner_value_is_in_list
