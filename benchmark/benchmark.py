import polars as pl
import code

from polars.dependencies import dataclasses

PROJECTS = {
    "aao": (5, "rust"),
    "bachelor": (5, "tex"),
    "dcaf": (5, "rust"),
    "jab": (3, "java"),
    "master": (5, "tex"),
    "spot": (3, "java"),
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
    index: int  # NOTE: 1-indexed

    @staticmethod
    def all() -> list["Variant"]:
        variants = []
        for project, (count, ls) in PROJECTS.items():
            for i in range(count):
                for kind in ("norm", "x"):
                    variants.append(
                        Variant(project=project, kind=kind, index=i + 1, ls=ls)
                    )
        return variants


def main():
    df = pl.DataFrame()
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
        df = pl.concat([df, pl.concat([results, metadata], how="horizontal")])

    # Then, aggregate along project and kind.
    df = df.group_by(pl.col("project", "kind", "ls")).agg(pl.mean(*COLKEYS))
    # Output collected data into one CSV.
    df = df.select(
        (pl.col(COLKEYS).dt.total_milliseconds() / 1000).round(2),
        pl.col("ls"),
        label=pl.col("project") + "-" + pl.col("kind"),
    )
    # Put label in front.
    df = df.select(pl.col("label", "ls", *COLKEYS))
    # Add misc column for unaccounted time.
    df = df.with_columns(
        (pl.col("LSP Total") - pl.sum_horizontal(set(COLKEYS) - {"LSP Total", "find"}))
        .round(2)
        .alias("LSP Miscellaneous")
    ).sort(pl.col("label"))
    # We need to separate these by language server, to make them better comparable.

    for ls in ["java", "rust", "tex"]:
        ls_df = df.filter(pl.col("ls") == ls)
        # if ls != "tex":
        #     # Minutes are better-suited here than seconds.
        #     code.interact(local=dict(globals(), **locals()))
        #     ls_df = ls_df.with_columns((pl.col(COLKEYS) / 60).round(2))
        print(f"Labels {ls.title()}:")
        indexes = []
        for i, variant in enumerate(ls_df["label"]):
            if i > 1:
                # We want to separate the next project by a bit.
                i += 1
            print(f"{i} ↦ {variant}")
            indexes.append(i)

        ls_df.drop("label", "ls").with_columns(index=pl.Series(indexes)).write_csv(
            f"{ls}.dat", separator="\t", include_header=True
        )


if __name__ == "__main__":
    main()
