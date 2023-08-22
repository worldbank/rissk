

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


def get_file_parts(filename):
    # Remove ".zip" and split by "_"
    filename_parts = filename[:-4].split("_")
    if len(filename_parts) < 4:
        raise ValueError(f"ERROR: {filename} Not a valid Survey Solutions export file.")

    version, file_format, interview_status = filename_parts[-3:]
    try:
        version = int(version)
    except ValueError:
        raise ValueError(f"ERROR: {filename} Not a valid Survey Solutions export file. Version not found.")
    questionnaire = "_".join(filename_parts[:-3])
    # Test input file has the correct name
    if file_format not in ["Tabular", "STATA", "SPSS", "Paradata"]:
        raise ValueError(f"ERROR: {filename} Not a valid Survey Solutions export file. Export type not found")

    if interview_status not in ["Approved", "InterviewerAssigned", "ApprovedBySupervisor", "ApprovedByHQ", "All", 'ApprovedByHeadquarters']:
        raise ValueError(f"ERROR: {filename} Not a valid Survey Solutions export file. Interview status not found.")

    file_format = file_format if file_format == 'Paradata' else 'Tabular'
    return questionnaire, version, file_format, interview_status


def assign_type(df, dtypes):
    for column in dtypes.index:
        df[column] = df[column].astype(dtypes[column])
    return df