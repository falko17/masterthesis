import polars as pl
from colorama import Back, Fore, Style
from KDEpy.bw_selection import improved_sheather_jones

P_VALUE = 0.05


def print_statistic(name, res, onlysig=False):
    text = ""
    sig = res.pvalue < P_VALUE
    if sig:
        text += f"{Fore.RED}!!! SIGNIFICANT !!!{Fore.RESET} "
    text += f"{name}: {res.statistic} (p = {Fore.RED if sig else Fore.RESET}{res.pvalue}{Fore.RESET})"
    if not onlysig or sig:
        print(text)


def print_comments(name, comments):
    print(f"\n{Style.BRIGHT}{name} comments:{Style.RESET_ALL}")
    for comment in comments.iter_rows():
        if comment[0] is not None and len(comment[0]) > 0:
            assert len(comment) == 1
            print(f"- {comment[0]}")


def write_dat(name: str, df: pl.DataFrame):
    df = df.rename(lambda x: x.replace("_", "-")).with_columns(
        pl.col(pl.Float64, pl.Float32).round(4)
    )
    print(f"\n{Style.BRIGHT}Optimal bandwidth (ISJ) for {name}.dat:{Style.RESET_ALL}")
    for col in df.iter_columns():
        try:
            bw = improved_sheather_jones(col.to_numpy().reshape(-1, 1).astype(float))
            print(f"{col.name}: {Fore.BLUE}{bw}{Fore.RESET}")
        except ValueError:
            print(f"No convergence for {col.name}.")
    print()
    df.write_csv(f"dat/{name}.dat", separator="\t")
