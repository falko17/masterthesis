from itertools import product

import polars as pl
from colorama import Back, Fore, Style
from scipy.stats import (
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


def check_effects(sv, vs):
    # TODO: Maybe, to avoid concerns of p-hacking, use p=0.01 here?
    #
    # Check for effects of some IVs (experience, age, etc) on DVs.
    # MUST CHECK: programming, opensource, knowsee [sign. diff] and knowide, knowjava [important]
    print("\n=== EFFECTS ===")

    dv_categorical = [f"a{i}_c" for i in (2, 3, 5, 6)]
    dv_interval = (
        ["a1_c", "a4_c"]
        + [f"a{i}_time" for i in range(1, 7)]
        + [f"a{i}_asq_{kind}" for i in range(1, 7) for kind in ("time", "easy")]
    )

    sv = sv.with_columns(pl.col(pl.Duration).dt.total_seconds() / 60)
    vs = vs.with_columns(pl.col(pl.Duration).dt.total_seconds() / 60)

    # We would also like to output a correlation matrix for a heatmap visualization.
    # We will create a matrix per kind of correlation measure.
    # The columns will be the IV, then the DV, then the correlation measure.
    mat = pl.DataFrame(
        schema={
            "IV": pl.String,
            "DV": pl.String,
            "Correlation": pl.Float64,
            "p": pl.Float64,
        }
    )
    mat_total = mat.clone()

    # TODO: SUS

    # IVs:
    # We have interval and ordinal variables, separated in the two arrays.
    # We also have the categorical gender, but as there is only one non-male, we won't investigate this further.
    # DVs:
    # Time, Usability, and a1_c and a3_c are continuous variables (interval-scaled).
    # Other correctness values are categorical (with 2 categories).
    # According to (Khamis, 2008), we will use...
    # - Either Pearson or Spearman (if outliers) for Interval-Interval
    for key1, key2 in product(iv_interval, dv_interval):
        # TODO: Choose one or both
        corr_sv = spearmanr(sv[key1], sv[key2])
        corr_vs = spearmanr(vs[key1], vs[key2])
        mat = pl.concat(
            [
                mat,
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_sv",
                        "Correlation": corr_sv.statistic,
                        "p": corr_sv.pvalue,
                    },
                ),
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_vs",
                        "Correlation": corr_vs.statistic,
                        "p": corr_vs.pvalue,
                    },
                ),
            ]
        )
    # - Kendall's tau_b for Ordinal-Interval
    mat_total = pl.concat([mat_total, mat])
    mat = mat.clear()
    for key1, key2 in product(iv_ordinal, dv_interval):
        corr_sv = kendalltau(sv[key1], sv[key2])
        corr_vs = kendalltau(vs[key1], vs[key2])
        mat = pl.concat(
            [
                mat,
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_sv",
                        "Correlation": corr_sv.statistic,
                        "p": corr_sv.pvalue,
                    },
                ),
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_vs",
                        "Correlation": corr_vs.statistic,
                        "p": corr_vs.pvalue,
                    },
                ),
            ]
        )
    # write_dat("corr-ktau", mat)
    mat_total = pl.concat([mat_total, mat])
    mat = mat.clear()
    # - Point-biserial correlation coefficient (since we only have 2 categories) for Interval-Categorical
    for key1, key2 in product(iv_interval, dv_categorical):
        corr_sv = pointbiserialr(sv[key1], sv[key2])
        corr_vs = pointbiserialr(vs[key1], vs[key2])
        mat = pl.concat(
            [
                mat,
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_sv",
                        "Correlation": corr_sv.statistic,
                        "p": corr_sv.pvalue,
                    },
                ),
                pl.DataFrame(
                    {
                        "IV": key1,
                        "DV": key2 + "_vs",
                        "Correlation": corr_vs.statistic,
                        "p": corr_vs.pvalue,
                    },
                ),
            ]
        )
        # print_statistic(
        #     f"{key1} x {key2} (SV)", , True
        # )
        # print_statistic(
        #     f"{key1} x {key2} (VS)", pointbiserialr(vs[key1], vs[key2]), True
        # )
    # - Rank-biserial correlation coefficient for Ordinal-Categorical
    # for key1, key2 in product(iv_ordinal, dv_categorical):
    #     print_statistic(f"{key1} x {key2}", pointbiserialr(sv[key1], sv[key2]))
    #     print_statistic(f"{key1} x {key2}", pointbiserialr(vs[key1], vs[key2]))
    mat_total = pl.concat([mat_total, mat])

    mat_total = mat_total.filter(pl.col("p").is_not_nan())
    mat_total = mat_total.with_columns(
        p_adjusted=pl.Series(false_discovery_control(mat_total["p"], method="bh"))
    )
