import code

import polars as pl
from polars import DataFrame, Datetime, Expr, String
from scipy.stats import fisher_exact, mannwhitneyu

from src.cleanup import clean_data

P_VALUE = 0.05


def main():
    print("Analyzing evaluation results...")
    sv = pl.read_csv(
        "SEE-VSCode.csv",
        separator=";",
        try_parse_dates=True,
        schema_overrides={"s1a2_acent_update": Datetime(time_zone="UTC")},
    )
    vs = pl.read_csv(
        "VSCode-SEE.csv",
        separator=";",
        try_parse_dates=True,
        schema_overrides={
            # Some of these are completely empty, but we need polars to know they are datetimes.
            "v1a2_acent_update": Datetime(time_zone="UTC"),
            "v1a2_adisp_update": Datetime(time_zone="UTC"),
            "v1a2_amisc_update": Datetime(time_zone="UTC"),
            "s2a2_acent_update": Datetime(time_zone="UTC"),
            "s2a2_adisp_update": Datetime(time_zone="UTC"),
            "s2a2_amisc_update": Datetime(time_zone="UTC"),
        },
    )
    # Unfortunately, I made a bad naming choice when constructing the VSCode/SEE order form.
    # In SEE/VSCode, the A1 cols for spotbugs are named spXb, for JabRef jXb.
    # However, for some reason in VSCode/SEE the ones for spotbugs are sXb and the ones for JabRef spXb.
    # This is not easily salvageable in the single clean_data run below, so we rename these beforehand.
    vs = vs.rename(
        {
            f'<span style=""display:none"">sp{i}b class</span>': f'<span style=""display:none"">j{i}b class</span>'
            for i in range(1, 4)
        }
    )
    sv = clean_data(sv)
    vs = clean_data(vs)

    # Reminder: SpotBugs first, then JabRef (for both).
    # We choose Mann-Whitney U test for time/correctness/usability (no normal requirements, ordinal/interval DV, 2 independent groups in 1 IV).
    # Then, if we have time for that, check for effects of some IVs (experience, age, etc) on DVs.
    # MUST CHECK: programming, opensource, knowsee [sign. diff] and knowide, knowjava [important]
    #
    # Also, first, check for significant differences between two groups in terms of:
    # age, gender, degree, programming, opensource, knowsee, knowvs, knowide, knowgame, knowspotbugs, knowjabref, knowjava, start/end/total_time
    code.interact(local=dict(globals(), **locals()))
    check_demographics(sv, vs)


def check_demographics(sv, vs):
    interval = ["age", "start", "end", "total_time"]
    ordinal = [
        "degree",
        "programming",
        "opensource",
        "knowsee",
        "knowvs",
        "knowide",
        "knowgame",
        "knowspotbugs",
        "knowjabref",
        "knowjava",
    ]

    # No normal distr. can be assumed for any of these, so we use Mann-Whitney for ordinal and interval data,
    # and Fisher's exact test for categorical data with 2 levels (gender in this case).

    # We build a 2x2 contingency table:
    #  ┌──────────────┬───────────┐
    #  │     Group SV │ Group VS  │
    #  ├───┬──────────┴───────────┤
    #  │ M │    A          B      │
    #  │ F │    C          D      │
    #  └───┴──────────────────────┘
    gender_table = [
        [
            len(sv.filter(pl.col("gender") == "Male")),
            len(vs.filter(pl.col("gender") == "Male")),
        ],
        [
            len(sv.filter(pl.col("gender") == "Female")),
            len(vs.filter(pl.col("gender") == "Female")),
        ],
    ]
    print(
        f"Gender: {fisher_exact(gender_table)}"
    )  # returns infinity because we have a 0 in group SV, oh well.

    # Warn if there is anyone not familiar with IDEs or Java.
    noide = pl.concat([sv, vs]).filter(pl.col("knowide") != "Yes")
    nojava = pl.concat([sv, vs]).filter(pl.col("knowjava") != "Yes")
    if not noide.is_empty():
        print(f"! WARNING: {len(noide)} participants are not familiar with IDEs!")
    if not nojava.is_empty():
        print(f"! WARNING: {len(nojava)} participants are not familiar with Java!")

    for key in interval:
        print_u_result(
            key.replace("_", " ").capitalize(), mannwhitneyu(sv[key], vs[key])
        )

    for key in ordinal:
        print_u_result(
            key.replace("_", " ").capitalize(),
            mannwhitneyu(sv[key].to_physical(), vs[key].to_physical()),
        )


def print_u_result(name, res):
    text = ""
    if res.pvalue < P_VALUE:
        text += "!!! SIGNIFICANT !!! "

    text += f"{name}: U = {res.statistic} (p = {res.pvalue})"
    print(text)


if __name__ == "__main__":
    main()
