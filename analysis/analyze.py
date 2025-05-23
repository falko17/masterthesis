import code
import json
import readline
from collections import defaultdict

import polars as pl
from colorama import init as colorama_init
from genericpath import isfile
from polars import DataFrame, Datetime, Expr, String
from scipy.special import os
from scipy.stats import fisher_exact, mannwhitneyu, wilcoxon

from src.cleanup import clean_data, set_correctness, sus_total
from src.demographics import check_demographics, check_effects
from src.dtypes import d_datetime, name_mappings
from src.util import print_comments, print_statistic, write_dat


def main():
    colorama_init()
    pl.Config().set_tbl_rows(1000)
    print("Analyzing evaluation results...\n")
    sv = pl.read_csv(
        "SEE-VSCode.csv",
        separator=";",
        try_parse_dates=True,
        schema_overrides={"s1a2_acent_update": d_datetime},
    )
    vs = pl.read_csv(
        "VSCode-SEE.csv",
        separator=";",
        try_parse_dates=True,
        schema_overrides={
            # Some of these are completely empty, but we need polars to know they are datetimes.
            "v1a2_acent_update": d_datetime,
            "v1a2_adisp_update": d_datetime,
            "v1a2_amisc_update": d_datetime,
            "s2a2_acent_update": d_datetime,
            "s2a2_adisp_update": d_datetime,
            "s2a2_amisc_update": d_datetime,
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

    # Reminder: SpotBugs first, then JabRef (for both SV and VS).
    # We choose Mann-Whitney U test for time/correctness/usability (no normal requirements, ordinal/interval DV, 2 independent groups in 1 IV).
    check_demographics(sv, vs)

    both = pl.concat([sv, vs])
    both = sus_total(sus_total(both, "SEE"), "VSCode")
    sv = set_correctness(sv, "sv").filter(
        pl.col("knowjava") != "No, not really", pl.col("knowide") != "No, not really"
    )
    vs = set_correctness(vs, "vs").filter(
        pl.col("knowjava") != "No, not really", pl.col("knowide") != "No, not really"
    )

    check_correctness(sv, vs)
    check_time(sv, vs)
    check_usability(sv, vs, both)
    check_effects(sv, vs, both)

    write_data(sv, vs, both)

    # Finally, print comments.
    for key in ["see_comment", "vs_comment", "general_comment"]:
        print_comments(key.split("_")[0].upper(), both.select(pl.col(key)))


def check_correctness(sv, vs):
    print("\n=== CORRECTNESS ===")
    # We use MWU here because these columns are numerical (but not normally distr.).
    for key in ["a1_c", "a4_c"]:
        print_statistic(f"A{key[1]} Correctness", mannwhitneyu(sv[key], vs[key]))
    # Other columns are booleans (correct vs not), so we create 2x2 contingency tables and
    # analyze those with Fisher's exact test. The tables look like this:
    #  ┌──────────────────┬───────────┐
    #  │         Group SV │ Group VS  │
    #  ├───────┬──────────┴───────────┤
    #  │ Right │    A          B      │
    #  │ Wrong │    C          D      │
    #  └───────┴──────────────────────┘
    for i in (2, 3, 5, 6):
        key = f"a{i}_c"
        table = [
            [
                len(sv.filter(pl.col(key))),
                len(vs.filter(pl.col(key))),
            ],
            [
                len(sv.filter(pl.col(key).not_())),
                len(vs.filter(pl.col(key).not_())),
            ],
        ]
        print_statistic(f"A{i} Correctness", fisher_exact(table))


def check_time(sv, vs):
    print("\n=== TIME ===")
    for i in range(1, 7):
        key = f"a{i}_time"
        if i in (1, 4):
            # At least 1 has to be correct.
            correct_sv = sv.filter(pl.col(f"a{i}_c") > 1)
            correct_vs = vs.filter(pl.col(f"a{i}_c") > 1)
        else:
            correct_sv = sv.filter(pl.col(f"a{i}_c"))
            correct_vs = vs.filter(pl.col(f"a{i}_c"))
        print_statistic(f"A{i} Time", mannwhitneyu(correct_sv[key], correct_vs[key]))


def check_usability(sv, vs, both):
    print("\n=== USABILITY ===")
    # ASQ first.
    for i in range(1, 7):
        for kind in ("easy", "time"):
            print_statistic(
                f"A{i} ASQ {kind.title()}",
                mannwhitneyu(sv[f"a{i}_asq_{kind}"], vs[f"a{i}_asq_{kind}"]),
            )

    # Then the SUS.
    print_statistic(
        "SUS (SEE vs VSCode)", wilcoxon(both["sus_see"], both["sus_vscode"])
    )


def write_data(sv, vs, both):
    demo_keys = [
        "age",
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
    for i, df in enumerate([sv, vs]):
        write_dat(
            f"alphabeta{i+1}",
            df.select(
                [pl.col(key).to_physical() for key in demo_keys]
                + [(pl.col("total_time").dt.total_minutes() / 60)]
            ),
        )
    # For bar charts:
    for key in demo_keys[1:]:
        write_dat(
            f"alphabeta-{key}",
            sv.group_by(key)
            .agg(pl.len())
            .join(vs.group_by(key).agg(pl.len()), on=key, how="full")
            .fill_null(0)
            .select(
                pl.col(key)
                .fill_null(pl.col(f"{key}_right"))
                .cast(str)
                .replace(name_mappings[key])
                .alias("label"),
                pl.col("len").alias("occ1"),
                pl.col("len_right").alias("occ2"),
            )
            .sort(pl.col("occ1") + pl.col("occ2"), descending=True),
            violin=False,
        )

    comp_keys = [
        f"a{i}_{suffix}" for i in range(1, 7) for suffix in ["asq_easy", "asq_time"]
    ]
    comp_keys_bool = [f"a{i}_c" for i in range(1, 7)]
    comp_keys_time = [f"a{i}_time" for i in range(1, 7)]

    # For bar charts again (correctness):
    for key in comp_keys_bool:
        write_dat(
            f"seevs-{key.replace('_', '-')}",
            sv.group_by(key)
            .agg(pl.len())
            .join(vs.group_by(key).agg(pl.len()), on=key, how="full")
            .fill_null(0)
            .select(
                pl.col(key)
                .fill_null(pl.col(f"{key}_right"))
                .cast(int)
                .alias("correct"),
                pl.col("len").alias("occ1"),
                pl.col("len_right").alias("occ2"),
            )
            .sort(pl.col("occ1") + pl.col("occ2"), descending=True),
            violin=False,
        )

    for i, df in enumerate([sv, vs]):
        write_dat(
            f"seevs{i+1}",
            df.select(
                [pl.col(key).to_physical() for key in comp_keys]
                # + [pl.col(key).cast(dtype=int) for key in comp_keys_bool]
                + [pl.col(key).dt.total_seconds() / 60 for key in comp_keys_time]
            ),
        )

    # SUS needs to be separate due to different number of rows.
    write_dat("seevs-sus1", both.select(pl.col("sus_see").alias("sus")))
    write_dat("seevs-sus2", both.select(pl.col("sus_vscode").alias("sus")))


if __name__ == "__main__":
    main()
