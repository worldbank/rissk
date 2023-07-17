def normalize_column_name(s):
    """
    This function converts any string with capital letters to a string all lowercase with a "_" before any previously capital letter.

    Parameters:
    s (str): The string to convert.

    Returns:
    new_s (str): The converted string.
    """
    new_s = ""
    for i, char in enumerate(s):
        if char.isupper():
            # Add underscore only if it's not the first or last character
            if i != 0 and i != len(s)-1:
                new_s += "_"
            new_s += char.lower()
        else:
            new_s += char
    return new_s
