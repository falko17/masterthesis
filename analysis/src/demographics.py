import code
from itertools import product

import polars as pl
from colorama import Back, Fore, Style
from scipy.stats import (
    combine_pvalues,
    false_discovery_control,
    fisher_exact,
    kendalltau,
    mannwhitneyu,
    pointbiserialr,
    spearmanr,
)

from .util import print_statistic, write_dat

# FIXME
iv_interval = [
    "age",
    # "start",
    # "end",
    "total_time",
    "time_questionnaire",
    # "submission_time",
]
iv_ordinal = [
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


def check_demographics(sv, vs):
    print("=== DEMOGRAPHICS ===")
    # First, check for significant differences between two groups in terms of:
    # age, gender, degree, programming, opensource, knowsee, knowvs, knowide, knowgame, knowspotbugs, knowjabref, knowjava, start/end/total_time

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
    print_statistic("Gender", fisher_exact(gender_table))

    # Warn if there is anyone not familiar with IDEs or Java.
    noide = pl.concat([sv, vs]).filter(pl.col("knowide") != "Yes")
    nojava = pl.concat([sv, vs]).filter(pl.col("knowjava") != "Yes")
    if not noide.is_empty():
        print(
            f"{Fore.YELLOW}! WARNING: {len(noide)} participants are not familiar with IDEs!{Style.RESET_ALL}"
        )
    if not nojava.is_empty():
        print(
            f"{Fore.YELLOW}! WARNING: {len(nojava)} participants are not familiar with Java!{Style.RESET_ALL}"
        )

    for key in iv_interval:
        print_statistic(
            key.replace("_", " ").capitalize(), mannwhitneyu(sv[key], vs[key])
        )

    for key in iv_ordinal:
        print_statistic(
            key.replace("_", " ").capitalize(),
            mannwhitneyu(sv[key].to_physical(), vs[key].to_physical()),
        )


def check_effects(sv, vs, both):
    # Check for effects of some IVs (experience, age, etc) on DVs.
    # MUST CHECK: programming, opensource, knowsee [sign. diff]
    iv_interval = ["age"]
    iv_ordinal = [
        "degree",
        "programming",
        "opensource",
        "knowsee",
        "knowvs",
        "knowgame",
        "knowspotbugs",
        "knowjabref",
    ]
    print("\n=== EFFECTS ===")

    def prepare_df(df, see_first):
        systems = ["vscode", "see"]
        if see_first:
            systems.reverse()
        return df.with_columns(pl.col(pl.Duration).dt.total_seconds() / 60).select(
            pl.col(iv_interval + iv_ordinal + ["id"]),
            # Aggregate along SEE/VS, else we have too many hypotheses to test.
            # This also makes analysis a bit easier, as we only have interval-scaled dependent variables.
            (
                pl.col("a1_c") / 3 + pl.col("a2_c").cast(int) + pl.col("a3_c").cast(int)
            ).alias(f"{systems[0]}_correctness"),
            (
                pl.col("a4_c") / 3 + pl.col("a5_c").cast(int) + pl.col("a6_c").cast(int)
            ).alias(f"{systems[1]}_correctness"),
            (pl.col("a1_time") + pl.col("a2_time") + pl.col("a3_time")).alias(
                f"{systems[0]}_time"
            ),
            (pl.col("a4_time") + pl.col("a5_time") + pl.col("a6_time")).alias(
                f"{systems[1]}_time"
            ),
            (
                pl.col("a1_asq_time") + pl.col("a2_asq_time") + pl.col("a3_asq_time")
            ).alias(f"{systems[0]}_asq_time"),
            (
                pl.col("a4_asq_time") + pl.col("a5_asq_time") + pl.col("a6_asq_time")
            ).alias(f"{systems[1]}_asq_time"),
            (
                pl.col("a1_asq_easy") + pl.col("a2_asq_easy") + pl.col("a3_asq_easy")
            ).alias(f"{systems[0]}_asq_easy"),
            (
                pl.col("a4_asq_easy") + pl.col("a5_asq_easy") + pl.col("a6_asq_easy")
            ).alias(f"{systems[1]}_asq_easy"),
        )

    dvs = ("correctness", "time", "asq_time", "asq_easy", "sus")
    df = pl.concat([prepare_df(sv, True), prepare_df(vs, False)], how="diagonal")
    # Add SUS scores.
    df = df.join(
        both.select(
            pl.col("sus_see").alias("see_sus"),
            pl.col("sus_vscode").alias("vscode_sus"),
            pl.col("id"),
        ),
        on="id",
    )
    # We would also like to output a correlation matrix for a heatmap visualization.
    # We will create a matrix per kind of correlation measure.
    # The columns will be the IV, then the DV, then the correlation measure.
    mat = pl.DataFrame(
        schema={
            "IV": pl.String,
            "DV": pl.String,
            "correlation": pl.Float64,
            "p": pl.Float64,
        }
    )
    mat_total = mat.clone()

    # IVs:
    # We have interval and ordinal variables, separated in the two arrays.
    # We also have the categorical gender, but as there is only one non-male, we won't investigate this further.
    # DVs:
    # Time, Usability, and Correctness are continuous variables (interval-scaled).
    # According to (Khamis, 2008), we will use...
    # - Either Pearson or Spearman (if outliers) for Interval-Interval
    for key1, key2 in product(iv_interval, dvs):
        # We choose Spearman here, as there are indeed some outliers.
        corr_see = spearmanr(df[key1], df[f"see_{key2}"])
        corr_vscode = spearmanr(df[key1], df[f"vscode_{key2}"])
        mat = pl.concat(
            [
                mat,
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_see",
                        "correlation": corr_see.statistic,
                        "p": corr_see.pvalue,
                    },
                ),
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_vscode",
                        "correlation": corr_vscode.statistic,
                        "p": corr_vscode.pvalue,
                    },
                ),
            ]
        )
    # - Kendall's tau_b for Ordinal-Interval
    mat_total = pl.concat([mat_total, mat])
    mat = mat.clear()
    for key1, key2 in product(iv_ordinal, dvs):
        corr_see = kendalltau(df[key1], df[f"see_{key2}"])
        corr_vscode = kendalltau(df[key1], df[f"vscode_{key2}"])
        mat = pl.concat(
            [
                mat,
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_see",
                        "correlation": corr_see.statistic,
                        "p": corr_see.pvalue,
                    },
                ),
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_vscode",
                        "correlation": corr_vscode.statistic,
                        "p": corr_vscode.pvalue,
                    },
                ),
            ]
        )
    mat_total = pl.concat([mat_total, mat])
    mat = mat.clear()

    mat_total = mat_total.filter(pl.col("p").is_not_nan())
    mat_total = mat_total.with_columns(
        p_adjusted=pl.Series(false_discovery_control(mat_total["p"], method="by"))
    ).with_columns(pl.col(pl.String).str.replace_all("_", "-"))

    code.interact(local=dict(globals(), **locals()))
    write_dat("corr", mat_total, violin=False)
