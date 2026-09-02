import pandas as pd


def encode_input(df, encoders):

    categorical_columns = [

        "State",
        "City",
        "Region_Type",
        "Renovation_Type",
        "Quality_Grade",
        "Material_Quality",
        "Waterproofing_Required",
        "Season"

    ]

    for column in categorical_columns:

        df[column] = encoders[column].transform(
            df[column].astype(str)
        )

    return df