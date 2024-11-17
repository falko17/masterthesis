import code
import json
import os
from collections import defaultdict
from math import ceil

import polars as pl
from polars import DataFrame, Datetime, Expr, String

from src.dtypes import (
    d_degree,
    d_dispersion,
    d_gender,
    d_know,
    d_knowide,
    d_playgames,
    d_time,
    d_time_alt,
    d_yesnolittle,
)


def clean_data(df: DataFrame) -> DataFrame:
    keep_cols = [
        "start",
        "end",
    ]
    rename_cols = {
        "gender": "Please enter your gender.",
        "age": "Please enter your age.",
        "degree": "What is your highest school or university degree?",
        "programming": "How long have you been programming?",
        "opensource": "How long have you been programming on bigger software projects (e.g., within a company, or open-source projects)?",
        "knowsee": "Do you know **SEE (_Software Engineering Experience_)**?",
        "knowvs": "Do you know **Visual Studio Code (VSCode)**?",
        "knowide": "Have you worked in IDEs (Integrated Developer Environments), such as Eclipse, VSCode, oder IntelliJ?",
        "knowgame": "Do you have experience with 3D video games for desktop PCs?",
        "knowspotbugs": "Have you ever used the program **SpotBugs** (previously FindBugs)?",
        "knowjabref": "Have you ever used the program **JabRef**?",
        "knowjava": "Can you use the programming language Java?",
        "a1_class1": '^<span style=""display:none"">sp?1b class</span>$',
        "a1_class2": '^<span style=""display:none"">sp?2b class</span>$',
        "a1_class3": '^<span style=""display:none"">sp?3b class</span>$',
        "a2_convention": "According to which convention were unit tests organized in SpotBugs?",
        "a2_centralized": "What is the full name of the root package (the topmost package) for test classes?",
        "a2_dispersed": "Name any of the dispersed test classes.",
        "a2_other": "Please specify how the unit tests are organized.",
        "a3_class": "What is the base class of **OptionalReturnNull**?",
        "a4_class1": '<span style=""display:none"">j1b class</span>',
        "a4_class2": '<span style=""display:none"">j2b class</span>',
        "a4_class3": '<span style=""display:none"">j3b class</span>',
        "a5_convention": "According to which convention were unit tests organized in JabRef?",
        "a5_centralized": "What is the full name of the root package (the topmost package) for test classes?_duplicated_0",
        "a5_dispersed": "Name any of the dispersed test classes._duplicated_0",
        "a5_other": "Please specify how the unit tests are organized._duplicated_0",
        "a6_class": "What is the base class of **GenderEditorViewModel**?",
        "see_comment": "Regarding SEE, do you have any other suggestions for improvement, things that you noticed, or general comments?",
        "vs_comment": "Regarding VSCode, do you have any other suggestions for improvement, things that you noticed, or general comments?",
        "general_comment": "Is there anything else you would like to mention regarding your participation or in general?",
        "id": "_uuid",
        "submission_time": "_submission_time",
    }
    # Format for values: Start time column, end time column(s) as regex
    # We will then choose the maximum of the end time columns
    time_cols = {
        "time_questionnaire": ("gender_update", "^(?:see|vscode)1ready1_update$")
    } | {k: (b, e) for (k, b, e) in map(task_time, range(1, 7))}

    result = df.filter(pl.col("_validation_status") == "Approved").select(
        [pl.col(x) for x in keep_cols]
        + [pl.col(v).alias(k) for k, v in rename_cols.items()]
        + [handle_times(*v).alias(k) for k, v in time_cols.items()]
        + [x for i in range(1, 7) for x in asq(i)]
        + sus_columns("SEE")
        + sus_columns("VSCode")
        + [(pl.col("end") - pl.col("start")).alias("total_time")]
    )
    asq_cols = {f"a{i}_asq_easy" for i in range(1, 7)} | {
        f"a{i}_asq_time" for i in range(1, 7)
    }
    sus_cols = {f"sus_{x.lower()}_{i}" for x in ("SEE", "VSCode") for i in range(1, 11)}
    expected_columns = (
        keep_cols
        | rename_cols.keys()
        | time_cols.keys()
        | asq_cols
        | sus_cols
        | {"total_time"}
    )
    assert (
        set(result.columns) == expected_columns
    ), f"Difference in expected columns: Unhandled {set(result.columns) - expected_columns} and missing {expected_columns - set(result.columns)}"

    overrides: dict = {
        "gender": d_gender,
        "degree": d_degree,
        "programming": d_time,
        "opensource": d_time_alt,
        "knowsee": d_know,
        "knowvs": d_knowide,
        "knowide": d_yesnolittle,
        "knowgame": d_playgames,
        "knowspotbugs": d_know,
        "knowjabref": d_know,
        "knowjava": d_yesnolittle,
        "a2_convention": d_dispersion,
        "a5_convention": d_dispersion,
    }

    return result.cast(overrides)


def task_time(task_num: int) -> tuple[str, str, str]:
    result_col = f"a{task_num}_time"
    task_inner_num = ((task_num - 1) % 3) + 1
    part_num = ceil(task_num / 3)
    assert part_num in (1, 2) and task_inner_num in range(1, 4)
    begin_col = f"^(?:see|vs|vscode){part_num}ready{task_inner_num}_update$"
    end_col = "^(?:"
    if task_inner_num == 1:
        end_col += f"[sv]{part_num}a1_m[1-3]b_name"
    elif task_inner_num == 2:
        end_col += f"[sv]{part_num}a2_a(?:conv|cent|disp|misc)"
    elif task_inner_num == 3:
        end_col += f"[sv]{part_num}a3_a"
    end_col += f"|(?:see|vs){part_num}done{task_inner_num})_update$"
    return (result_col, begin_col, end_col)


def handle_times(start: str, end: str) -> Expr:
    return pl.max_horizontal(end) - pl.col(start)


def sus_columns(app: str) -> list[Expr]:
    columns = (
        "I think that I would like to use {0} frequently.",
        "I found {0} unnecessarily complex.",
        "I thought {0} was easy to use.",
        "I think that I would need the support of a technical person to be able to use {0}.",
        "I found the various functions in {0} were well integrated.",
        "I thought there was too much inconsistency in {0}.",
        "I would imagine that most people would learn to use {0} very quickly.",
        "I found {0} very cumbersome to use.",
        "I felt very confident using {0}.",
        "I needed to learn a lot of things before I could get going with {0}.",
    )

    sus_cols = [
        pl.col(x.format(app))
        .cast(pl.String)
        .str.head(1)
        .str.to_integer()
        .alias(f"sus_{app.lower()}_{i+1}")
        for i, x in enumerate(columns)
    ]
    return sus_cols


def sus_total(df, app):
    # And then we add one for the actual SUS score.
    return df.with_columns(
        (
            2.5
            * (
                20
                + sum(
                    ((-1) ** (i + 1)) * pl.col(f"sus_{app.lower()}_{i}")
                    for i in range(1, 11)
                )
            )
        ).alias(f"sus_{app.lower()}")
    )


def asq(task_num: int) -> list[Expr]:
    if task_num == 1:
        dup_suffix = ""
    else:
        dup_suffix = f"_duplicated_{task_num-2}"
    return [
        pl.col(
            f"I am overall satisfied with how easy this task was to solve.{dup_suffix}"
        )
        .cast(pl.String)
        .str.head(1)
        .str.to_integer()
        .alias(f"a{task_num}_asq_easy"),
        pl.col(
            f"I am overall satisfied with how much time it took to solve this task.{dup_suffix}"
        )
        .cast(pl.String)
        .str.head(1)
        .str.to_integer()
        .alias(f"a{task_num}_asq_time"),
    ]


def set_correctness(df, name):
    if os.path.isfile(f"./correctness_values_{name}.json"):
        with open(f"./correctness_values_{name}.json") as f:
            values = json.load(f)
    else:
        # Prompt user interactively whether each value is correct.
        keys = [
            "a1_class1",
            "a1_class2",
            "a1_class3",
            "a2_convention",
            "a3_class",
            "a4_class1",
            "a4_class2",
            "a4_class3",
            "a5_convention",
            "a6_class",
        ]
        values = defaultdict(list)
        for key in keys:
            print(df[key])
            for i, value in enumerate(df[key]):
                if key.endswith("_convention"):
                    # Needs special treatment, we need to see what was entered for other nearby fields.
                    prefix = key.split("_")[0]
                    print(
                        df.select(
                            pl.col(
                                f"{prefix}_centralized",
                                f"{prefix}_dispersed",
                                f"{prefix}_other",
                            )
                        )[i].glimpse()
                    )
                print(f"{value} (#{i+1})")
                correct = input("Is this correct? [Y/n/x]: ")
                values[key].append("y" if correct == "" else correct)

        # === ANSWER KEY ===
        # Original FindBugs study by Wettel:
        # A1 = unit test dispersion (FB: Dispersed)
        # A4.1 = 3 classes with highest num methods (FB: AbstractFrameModelingVisitor, MainFrame, BugInstance/TypeFrameModelingVisitor)
        # SpotBugs:
        # 1) AbstractFrameModelingVisitor (198), BugInstance (165), TypeFrameModelingVisitor (126)
        # 2) EITHER centralized spotbugs-test, OR allow dispersed TestDataflowAnalysis OR none
        #    => SpotBugs detects tests (and "tests" things for bugs), so participants might have been confused due to that.
        # 3) BetterVisitor/Visitor
        # JabRef:
        # 4) BibTexParserTest (143), JabRefPreferences (136), AuthorListTest (127)
        # 5) Centralized: src.test.java.org.jabref (or src.test, or test)
        # 6) AbstractViewModel

        with open(f"./correctness_values_{name}.json", "w") as f:
            json.dump(values, f)

    def as_series(col):
        return pl.Series([x == "y" for x in values[col]], dtype=pl.Boolean)

    return df.with_columns(
        a1_c=sum(
            [as_series(x).cast(int) for x in ["a1_class1", "a1_class2", "a1_class3"]]
        ),
        a2_c=as_series("a2_convention"),
        a3_c=as_series("a3_class"),
        a4_c=sum(
            [as_series(x).cast(int) for x in ["a4_class1", "a4_class2", "a4_class3"]]
        ),
        a5_c=as_series("a5_convention"),
        a6_c=as_series("a6_class"),
    )
