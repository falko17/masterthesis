import polars as pl
import code

from polars.dependencies import dataclasses

PROJECTS = {
    "aao": (5, "rust", 1250),
    "bachelor": (5, "tex", 46348),
    "dcaf": (5, "rust", 9940),
    "jab": (3, "java", 919),
    "master": (5, "tex", 24048),
    "spot": (3, "java", 16262),
}

NAMES = {
    "aao": "\\proptt{aaoffline}",
    "bachelor": "Bachelor's thesis",
    "dcaf": "\\proptt{dcaf-rs}",
    "jab": "JabRef",
    "master": "Master's thesis",
    "spot": "SpotBugs",
}

COLKEYS = {
    "LSP Nodes",
    "LSP Tree",
    "LSP Edges",
    "find",
    "LSP Diagnostics",
    "LSP Aggregate",
    "LSP Total",
}


@dataclasses.dataclass()
class Variant:
    project: str
    kind: str
    ls: str
    edges: int
    index: int  # NOTE: 1-indexed

    @staticmethod
    def all() -> list["Variant"]:
        variants = []
        for project, (count, ls, edges) in PROJECTS.items():
            for i in range(count):
                for kind in ("norm", "x"):
                    variants.append(
                        Variant(
                            project=project,
                            kind=kind,
                            index=i + 1,
                            ls=ls,
                            edges=edges,
                        )
                    )
        return variants


def main():
    original_df = pl.DataFrame()
    # Collect data from CSVs.
    for variant in Variant.all():
        filename = f"perf-{variant.project}-{variant.kind}{variant.index}.csv"
        results = pl.read_csv(filename, has_header=False).transpose()
        results = (
            results.rename(results.head(1).to_dicts().pop())[1:]
            .cast(pl.Float64)
            .cast(pl.Duration("ms"))
        )
        metadata = pl.from_dict(dataclasses.asdict(variant))
        original_df = pl.concat(
            [original_df, pl.concat([results, metadata], how="horizontal")]
        )

    # Then, aggregate along project and kind.
    df = original_df.group_by(pl.col("project", "kind", "ls", "edges")).agg(
        pl.mean(*COLKEYS),
        pl.max(*COLKEYS).name.suffix("_max"),
        pl.min(*COLKEYS).name.suffix("_min"),
    )
    # Output collected data into one CSV.
    df = df.with_columns(
        (pl.col(COLKEYS).dt.total_milliseconds() / 1000).round(4),
        label=pl.col("project") + "-" + pl.col("kind"),
    )
    # Put label in front.
    df = df.select(pl.col("label"), pl.exclude("label"))
    # Add misc column for unaccounted time.
    df = df.with_columns(
        (pl.col("LSP Total") - pl.sum_horizontal(set(COLKEYS) - {"LSP Total", "find"}))
        .round(4)
        .alias("LSP Miscellaneous")
    ).sort(pl.col("label"))
    # We need to separate these by language server, to make them better comparable.

    for ls in ["java", "rust", "tex"]:
        ls_df = df.filter(pl.col("ls") == ls)
        print(f"Labels {ls.title()}:")
        indexes = []
        for i, variant in enumerate(ls_df["label"]):
            if i > 1:
                # We want to separate the next project by a bit.
                i += 1
            print(f"{i} ↦ {variant}")
            indexes.append(i)

        ls_df.drop(
            "label", "ls", "edges", "project", "kind", "^.*_(max|min)$"
        ).with_columns(index=pl.Series(indexes)).write_csv(
            f"{ls}.dat", separator="\t", include_header=True
        )

    # Finally, we also want to show the advantage of the optimized version by number of edges.
    df = (
        original_df.sort("index")
        .pivot(
            "kind",
            values="LSP Total",
            index=["project", "edges", "index"],
            aggregate_function="first",
        )
        .with_columns(
            (
                1
                - pl.col("norm").dt.total_milliseconds()
                / pl.col("x").dt.total_milliseconds()
            ).alias("advantage")
        )
        .filter(pl.col("advantage") >= 0)
        .group_by("project")
        .agg(
            pl.col("edges").first(),
            pl.col("advantage").mean().round(4).alias("adv_mean"),
            (pl.col("advantage").mean() - pl.col("advantage").min())
            .round(4)
            .alias("adv_min"),
            (pl.col("advantage").max() - pl.col("advantage").mean())
            .round(4)
            .alias("adv_max"),
        )
        .with_columns(pl.col("project").replace_strict(NAMES))
    )
    # code.interact(local=dict(globals(), **locals()))
    df.sort(pl.col("edges")).write_csv(
        "advantage.dat", separator="\t", include_header=True
    )


if __name__ == "__main__":
    main()
