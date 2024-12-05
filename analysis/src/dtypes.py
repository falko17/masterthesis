from collections import defaultdict

import polars as pl
from polars import Datetime

d_datetime = Datetime(time_zone="UTC")
d_gender = pl.Enum(["Female", "Male", "Other", "Prefer not to say"])
d_degree = pl.Enum(
    [
        "Still in school",
        "No degree",
        "Lower secondary school leaving certificate",
        "Intermediate school leaving certificate (e.g., Realschulabschluss)",
        "University of applied sciences entrance qualification (Fachabitur)",
        "General higher education entrance qualification (Abitur) [Also choose this if you have completed school but are not sure what to pick]",
        "Bachelor's degree",
        "Master's degree",
        "Doctoral degree",
    ]
)
d_time = pl.Enum(
    ["Never", "Less than 3 years", "3–9 years", "10–19 years", "20 years or more"]
)
d_time_alt = pl.Enum(
    ["Not yet", "Less than 3 years", "3–9 years", "10–19 years", "20 years or more"]
)
d_know = pl.Enum(
    ["No", "Heard of it", "Yes, I’ve used it", "Yes, I’ve developed (parts of) it"]
)
d_knowide = pl.Enum(["Heard of it", "Yes, I’ve used it", "Yes, it’s my main IDE", "No"])
d_playgames = pl.Enum(
    [
        "Yes, have played a lot",
        "Yes, have played a little",
        "Yes, but barely played",
        "No, never",
    ]
)
d_yesnolittle = pl.Enum(["Yes", "A little", "No, not really"])
d_dispersion = pl.Enum(
    [
        "Centralized: There is a single package hierarchy containing all test classes.",
        "Dispersed: The test classes are located in the same package as the tested classes.",
        "None: There are no unit tests.",
        "Other: Please specify manually.",
    ]
)

name_mappings = defaultdict(
    dict,
    {
        "degree": {
            "University of applied sciences entrance qualification (Fachabitur)": "Fachabitur",
            "General higher education entrance qualification (Abitur) [Also choose this if you have completed school but are not sure what to pick]": "Abitur",
        },
        "knowsee": {
            "Yes, I’ve used it": "Used it before",
            "Yes, I’ve developed (parts of) it": "Developed parts of it",
        },
        "knowvs": {
            "Yes, I’ve used it": "Used it before",
            "Yes, it’s my main IDE": "Is my main IDE",
        },
        "knowgame": {
            "Yes, have played a lot": "I play a lot",
            "Yes, have played a little": "I play a little",
            "Yes, but barely played": "I barely play",
            "No, never": "I never played",
        },
        "knowjabref": {
            "Yes, I’ve used it": "Used it before",
            "Yes, I’ve developed (parts of) it": "Developed parts of it",
        },
    },
)
