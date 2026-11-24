"""
Germline CLI Module
===================

Command-line interface logic for germline database management.

This module provides the core logic for the `sadie germlines populate` command,
including provider downloads, version checking, progress tracking, and
post-download build pipeline.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .providers.base import normalize_species

logger = logging.getLogger(__name__)
console = Console()


CHECKPOINT_FILE = ".populate_checkpoint.json"
VERSION_FILE = "VERSION.json"


def get_provider(provider_name: str):
    """Get provider instance by name."""
    from .providers.imgt import IMGTProvider
    from .providers.ogrdb import OGRDBProvider
    from .providers.vdjbase import VDJbaseProvider

    providers = {
        "imgt": IMGTProvider,
        "ogrdb": OGRDBProvider,
        "vdjbase": VDJbaseProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    return providers[provider_name]()


def get_provider_data_dir(provider_name: str) -> Path:
    """Get the data directory for a provider."""
    base_dir = Path(__file__).parent / "sources"
    return base_dir / provider_name


def load_checkpoint(provider_name: str) -> Set[str]:
    """Load download checkpoint for a provider."""
    checkpoint_path = get_provider_data_dir(provider_name) / CHECKPOINT_FILE
    if checkpoint_path.exists():
        try:
            data = json.loads(checkpoint_path.read_text())
            return set(data.get("completed_species", []))
        except Exception:
            pass
    return set()


def save_checkpoint(provider_name: str, completed: Set[str], total: int):
    """Save download checkpoint."""
    checkpoint_path = get_provider_data_dir(provider_name) / CHECKPOINT_FILE
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(
        json.dumps(
            {
                "completed_species": list(completed),
                "total_species": total,
                "updated_at": datetime.now().isoformat(),
            },
            indent=2,
        )
    )


def clear_checkpoint(provider_name: str):
    """Clear download checkpoint after successful completion."""
    checkpoint_path = get_provider_data_dir(provider_name) / CHECKPOINT_FILE
    if checkpoint_path.exists():
        checkpoint_path.unlink()


def get_local_version(provider_name: str) -> Optional[dict]:
    """Get local version info for a provider."""
    version_path = get_provider_data_dir(provider_name) / VERSION_FILE
    if version_path.exists():
        try:
            return json.loads(version_path.read_text())
        except Exception:
            pass
    return None


def get_species_on_disk(provider_name: str) -> List[str]:
    """Species directories of a provider that hold at least one FASTA file."""
    data_dir = get_provider_data_dir(provider_name)
    if not data_dir.exists():
        return []
    return sorted(d.name for d in data_dir.iterdir() if d.is_dir() and d.name[0] not in "._" and any(d.glob("*.fasta")))


def save_version(provider_name: str, version: str, allele_counts: Optional[dict] = None):
    """Save version info after download.

    species_count is the number of species on disk, not of the last run; allele_counts
    (per-species, per-file counts the downloader saw) are merged into the stored ones.
    """
    version_path = get_provider_data_dir(provider_name) / VERSION_FILE
    version_path.parent.mkdir(parents=True, exist_ok=True)
    species = get_species_on_disk(provider_name)
    stored = (get_local_version(provider_name) or {}).get("allele_counts") or {}
    version_path.write_text(
        json.dumps(
            {
                "version": version,
                "downloaded_at": datetime.now().isoformat(),
                "provider": provider_name,
                "species_count": len(species),
                "allele_counts": {**stored, **(allele_counts or {})},
            },
            indent=2,
        )
    )


def get_current_version_string() -> str:
    """Get current version string based on year-month."""
    return f"release-{datetime.now().strftime('%Y%m')}"


def get_upstream_version_string(provider_name: str) -> str:
    """Return the current upstream version string for a provider.

    For OGRDB this is derived from the Zenodo publication date so the check
    reflects actual data releases rather than the calendar month.
    """
    if provider_name == "ogrdb":
        try:
            from .scripts.download_ogrdb import OGRDBDownloader

            return OGRDBDownloader().get_latest_version_string()
        except Exception:
            pass
    return get_current_version_string()


def is_up_to_date(provider_name: str) -> bool:
    """Check if provider data is up-to-date."""
    local = get_local_version(provider_name)
    if not local:
        return False

    current = get_upstream_version_string(provider_name)
    return local.get("version") == current


def get_all_provider_species(provider_name: str) -> List[str]:
    """Get all available species for a provider."""
    if provider_name == "imgt":
        from .scripts.download_imgt import SPECIES_MAP

        return list(SPECIES_MAP.keys())
    elif provider_name == "ogrdb":
        return ["human", "mouse"]
    elif provider_name == "vdjbase":
        provider = get_provider(provider_name)
        return provider.get_available_species() or ["human", "macaque"]
    return []


def populate_provider(
    provider_name: str,
    species: Optional[List[str]],
    force: bool,
    dry_run: bool,
    progress: Progress,
) -> dict:
    """
    Populate data for a single provider.

    Parameters
    ----------
    provider_name : str
        Provider name (imgt, ogrdb, vdjbase)
    species : List[str], optional
        Specific species to download, or None for all
    force : bool
        Force re-download even if up-to-date
    dry_run : bool
        Show what would be downloaded without downloading
    progress : Progress
        Rich progress instance

    Returns
    -------
    dict
        Results with species counts and status
    """
    all_species = get_all_provider_species(provider_name)
    target_species = list(dict.fromkeys(normalize_species(sp) for sp in species or all_species))

    if dry_run:
        console.print(f"[cyan]{provider_name}[/cyan]: Would download {len(target_species)} species")
        for sp in target_species:
            console.print(f"  - {sp}")
        return {"status": "dry_run", "species_count": len(target_species)}

    if not force and is_up_to_date(provider_name):
        console.print(f"[yellow]{provider_name}[/yellow]: Already up-to-date, skipping")
        return {"status": "skipped", "reason": "up-to-date"}

    completed = load_checkpoint(provider_name) if not force else set()
    remaining = [sp for sp in target_species if sp not in completed]

    if not remaining:
        console.print(f"[green]{provider_name}[/green]: All species already downloaded")
        clear_checkpoint(provider_name)
        return {"status": "complete", "species_count": len(target_species)}

    task = progress.add_task(f"[cyan]{provider_name}[/cyan]", total=len(target_species))

    if completed:
        progress.update(task, completed=len(completed))
        console.print(f"[yellow]Resuming from checkpoint: {len(completed)}/{len(target_species)} complete[/yellow]")

    results = {"status": "success", "downloaded": [], "failed": [], "skipped": list(completed)}

    provider = get_provider(provider_name)
    allele_counts: dict = {}

    for sp in remaining:
        progress.update(task, description=f"[cyan]{provider_name}[/cyan]: {sp}")
        started = time.time()
        species_dir = provider.data_dir / sp

        try:
            if provider_name == "imgt":
                from .scripts.download_imgt import IMGTDownloader

                # Past the up-to-date check a stale stamp means re-fetch: without force the
                # downloader keeps the files on disk and nothing new arrives.
                downloader = IMGTDownloader(output_dir=provider.data_dir)
                downloader.download([sp], force=True)
            elif provider_name == "ogrdb":
                from .scripts.download_ogrdb import OGRDBDownloader

                downloader = OGRDBDownloader(output_dir=provider.data_dir)
                downloader.download([sp])
                allele_counts.update(downloader.allele_counts)
            else:
                provider.download([sp])

            # Downloaded means this run wrote a FASTA: files of an earlier run do not count,
            # the downloaders log a failed fetch and return normally.
            # shortcut: one fetched file counts the whole species; upgrade if downloaders report per-file failures
            fasta_files = list(species_dir.glob("*.fasta")) if species_dir.exists() else []
            if not any(f.stat().st_mtime >= started for f in fasta_files):
                no_data = False
                if fasta_files:
                    reason = f"{sp}: nothing fetched in this run, files on disk are from an earlier download"
                elif provider_name == "imgt":
                    from .scripts.download_imgt import SPECIES_MAP
                    from .scripts.download_imgt import IMGTDownloader as _D

                    imgt_name = SPECIES_MAP.get(sp, sp)
                    reason = _D(output_dir=provider.data_dir).check_ig_unavailable_reason(imgt_name, sp)
                    # IMGT answered and lists the species without IG sequences (TR-only): not a failed fetch
                    no_data = reason.endswith(_D._IG_UNAVAILABLE_REASONS["tr_only"])
                else:
                    reason = f"{sp}: no sequences downloaded"
                logger.warning(f"{provider_name}: {reason}")
                if no_data:
                    console.print(f"[yellow]{reason}, skipped[/yellow]")
                else:
                    results["failed"].append({"species": sp, "error": reason})
            else:
                completed.add(sp)
                results["downloaded"].append(sp)
                save_checkpoint(provider_name, completed, len(target_species))

        except Exception as e:
            logger.error(f"Failed to download {sp} from {provider_name}: {e}")
            results["failed"].append({"species": sp, "error": str(e)})

        # A species without data leaves no empty directory behind (the IMGT downloader names it in lower snake case)
        for leftover in {species_dir, provider.data_dir / sp.lower().replace(" ", "_")}:
            if leftover.is_dir() and not any(leftover.iterdir()):
                leftover.rmdir()

        progress.advance(task)

    # Only stamp the version when at least one species produced real data
    if results["downloaded"] and not results["failed"]:
        clear_checkpoint(provider_name)
        version = get_upstream_version_string(provider_name)
        save_version(provider_name, version, allele_counts)
    elif results["failed"]:
        results["status"] = "partial" if results["downloaded"] else "failed"
        clear_checkpoint(provider_name)  # the retry advice is --force, which ignores the checkpoint
    elif not results["downloaded"]:
        results["status"] = "no data"

    results["species_count"] = len(results["downloaded"]) + len(results["skipped"])
    return results


def run_post_download_build(provider_name: str, species_list: List[str], progress: Progress):
    """
    Run post-download build pipeline.

    Builds BLAST databases, auxiliary files, and internal_data for downloaded species.

    Parameters
    ----------
    provider_name : str
        Provider name
    species_list : List[str]
        Species to build for
    progress : Progress
        Rich progress instance
    """
    if provider_name != "imgt":
        console.print(
            f"[yellow]{provider_name} sources changed; the databases Airr reads were not rebuilt. Run:[/yellow]"
        )
        console.print(f"sadie germlines rebuild {' '.join(f'-s {sp}' for sp in species_list)}", soft_wrap=True)
        return

    console.print("\n[bold]Running post-download build pipeline...[/bold]")

    task = progress.add_task("[cyan]Building databases...", total=4)

    try:
        from .scripts.build_aux_files import build_aux_file_for_species
        from .scripts.build_internal_data import build_internal_data_for_species
    except ImportError:
        console.print("[yellow]Build scripts not found, skipping post-download build[/yellow]")
        return

    progress.update(task, description="[cyan]Building auxiliary files...")
    for sp in species_list:
        try:
            build_aux_file_for_species(sp)
        except Exception as e:
            logger.warning(f"Failed to build aux file for {sp}: {e}")
    progress.advance(task)

    progress.update(task, description="[cyan]Building internal_data...")
    for sp in species_list:
        try:
            build_internal_data_for_species(sp)
        except Exception as e:
            logger.warning(f"Failed to build internal_data for {sp}: {e}")
    progress.advance(task)

    progress.update(task, description="[cyan]Building HMMs for renumbering...")
    try:
        from .renumbering_integration import LocalHMMBuilder

        hmm_builder = LocalHMMBuilder()
        hmm_count = 0
        for sp in species_list:
            for chain in ["H", "K", "L"]:
                try:
                    hmm_builder.get_hmm(sp, chain)
                    hmm_count += 1
                except Exception as e:
                    logger.debug(f"Could not build HMM for {sp} {chain}: {e}")
        if hmm_count > 0:
            console.print(f"[dim]Built {hmm_count} HMM models[/dim]")
    except ImportError:
        console.print("[yellow]HMM builder not available, skipping[/yellow]")
    progress.advance(task)

    progress.update(task, description="[cyan]Build complete")
    progress.advance(task)

    console.print("[green]Post-download build complete[/green]")


def validate_provider_data(provider_name: str) -> bool:
    """
    Validate downloaded provider data.

    Parameters
    ----------
    provider_name : str
        Provider name

    Returns
    -------
    bool
        True if validation passes
    """
    console.print(f"\n[bold]Validating {provider_name} data...[/bold]")

    provider = get_provider(provider_name)
    metadata = provider.get_metadata()

    if not metadata.species_available:
        console.print(f"[red]No species data found for {provider_name}[/red]")
        return False

    valid = True
    for species in metadata.species_available:
        if not provider.is_available(species):
            console.print(f"[red]Missing data for {species}[/red]")
            valid = False
            continue

        for segment in ["V", "D", "J"]:
            for chain in ["H", "K", "L"]:
                genes = provider.fetch_genes(species, segment, chain)
                if segment == "D" and chain != "H":
                    continue
                for gene in genes:
                    if not gene.name or not gene.sequence:
                        console.print(f"[red]Invalid gene in {species}/{segment}/{chain}[/red]")
                        valid = False
                        break

    if valid:
        console.print(f"[green]{provider_name} data validation passed[/green]")
    else:
        console.print(f"[red]{provider_name} data validation failed[/red]")

    return valid


def populate_germlines(
    provider: str,
    species: Optional[List[str]],
    force: bool,
    dry_run: bool,
):
    """
    Main entry point for germlines populate command.

    Parameters
    ----------
    provider : str
        Provider name or "all"
    species : List[str], optional
        Specific species to download
    force : bool
        Force re-download
    dry_run : bool
        Show what would happen without doing it
    """
    providers_to_run = []

    if provider == "all":
        providers_to_run = ["imgt", "ogrdb", "vdjbase"]
    else:
        providers_to_run = [provider]

    console.print("\n[bold]SADIE Germline Database Population[/bold]")
    console.print("=" * 50)

    if dry_run:
        console.print("[yellow]DRY RUN - no changes will be made[/yellow]\n")

    table = Table(title="Provider Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Species")

    for prov in providers_to_run:
        local_version = get_local_version(prov)
        status = "Up-to-date" if is_up_to_date(prov) else "Needs update"
        species_count = local_version.get("species_count", 0) if local_version else 0
        table.add_row(prov, status, str(species_count) if species_count else "Not downloaded")

    console.print(table)
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        all_results = {}

        for prov_name in providers_to_run:
            console.print(f"\n[bold]Processing {prov_name}...[/bold]")

            results = populate_provider(prov_name, species, force, dry_run, progress)
            all_results[prov_name] = results

            # Downloaded species are built even when other species failed; validation covers
            # the whole provider, so it only runs when no species failed
            downloaded = results.get("downloaded", [])
            if not dry_run and downloaded:
                run_post_download_build(prov_name, downloaded, progress)

                if not results.get("failed") and not validate_provider_data(prov_name):
                    console.print(f"[yellow]Warning: {prov_name} validation had issues[/yellow]")

    console.print("\n[bold]Summary[/bold]")
    console.print("=" * 50)

    summary_table = Table()
    summary_table.add_column("Provider", style="cyan")
    summary_table.add_column("Status")
    summary_table.add_column("Downloaded")
    summary_table.add_column("Failed")

    for prov_name, results in all_results.items():
        status = results.get("status", "unknown")
        downloaded = len(results.get("downloaded", []))
        failed = len(results.get("failed", []))

        status_style = (
            "green" if status == "success" else "yellow" if status in ["skipped", "dry_run", "no data"] else "red"
        )
        summary_table.add_row(
            prov_name,
            f"[{status_style}]{status}[/{status_style}]",
            str(downloaded),
            str(failed),
        )

    console.print(summary_table)

    total_failed = sum(len(r.get("failed", [])) for r in all_results.values())
    if total_failed > 0:
        console.print(f"\n[red]Warning: {total_failed} species failed to download[/red]")
        console.print("Re-run the command with --force to retry")
        raise SystemExit(1)


def get_all_downloaded_species() -> List[str]:
    """
    Discover all species with downloaded source data across all providers.

    Returns
    -------
    List[str]
        Sorted unique species names that have data in any provider
    """
    species = set()
    for provider_name in ["imgt", "ogrdb", "vdjbase", "custom"]:
        species.update(get_species_on_disk(provider_name))
    return sorted(species)


def rebuild_germlines(
    species: Optional[List[str]],
):
    """
    Rebuild germline databases from already-downloaded data (no downloading).

    Runs the same pipeline as ``sadie.germlines.update_databases(species, force=True)``:
    sources/ -> normalized/ -> igblast/database, aux_db and Ig/internal_data,
    which are the files the default Airr reads.

    Parameters
    ----------
    species : List[str], optional
        Specific species to rebuild, or None for all downloaded
    """
    from . import update_databases
    from .manager import GermlineManager

    all_downloaded = get_all_downloaded_species()

    if species:
        species = list(dict.fromkeys(normalize_species(sp) for sp in species))
        target = [sp for sp in species if sp in all_downloaded]
        failed = [sp for sp in species if sp not in all_downloaded]
        if failed:
            console.print(f"[red]Species not found locally: {', '.join(failed)}[/red]")
    else:
        target, failed = all_downloaded, []

    if not target:
        if not failed:
            console.print("[yellow]No downloaded germline data found. Run 'sadie germlines populate' first.[/yellow]")
        raise SystemExit(1)

    console.print("\n[bold]SADIE Germline Database Rebuild[/bold]")
    console.print("=" * 50)
    console.print(f"[dim]Rebuilding {len(target)} species from sources/ (no downloads)[/dim]\n")

    manager = GermlineManager()
    for sp in target:
        try:
            # The pipeline skips a segment without genes and would rebuild from stale normalized/ files
            if not any(manager.get_genes(sp, "V", chain) for chain in "HKL"):
                raise RuntimeError(f"no V genes could be read from sources/*/{sp}/, nothing rebuilt")
            update_databases(sp, force=True)
            console.print(f"  [green]{sp}[/green]: rebuilt successfully")
        except Exception as e:
            console.print(f"  [red]{sp}[/red]: failed - {e}")
            logger.error(f"Failed to rebuild {sp}: {e}")
            failed.append(sp)

    if failed:
        console.print(f"\n[red]Rebuild failed for: {', '.join(failed)}[/red]")
        raise SystemExit(1)
    console.print("\n[green]Rebuild complete[/green]")


# ---------------------------------------------------------------------------
# Click command definitions
# ---------------------------------------------------------------------------


@click.group(name="germlines", help="Germline database management commands.")
def germlines() -> None:
    pass


@germlines.command("populate")
@click.option(
    "--provider",
    "-p",
    default="all",
    type=click.Choice(["all", "imgt", "ogrdb", "vdjbase"], case_sensitive=False),
    show_default=True,
    help="Provider to populate.",
)
@click.option(
    "--species",
    "-s",
    multiple=True,
    help="Species to download (may be repeated). Defaults to all species for the provider.",
)
@click.option("--force", "-f", is_flag=True, default=False, help="Force re-download even if up-to-date.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be downloaded without doing it.")
def populate_cmd(provider: str, species: tuple, force: bool, dry_run: bool) -> None:
    """Download and update germline sequences from a provider."""
    populate_germlines(
        provider=provider,
        species=list(species) if species else None,
        force=force,
        dry_run=dry_run,
    )


@germlines.command("status")
def status_cmd() -> None:
    """Show download status for all germline providers."""
    table = Table(title="Germline Provider Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Version")
    table.add_column("Species")
    table.add_column("Up-to-date")

    for prov in ["imgt", "ogrdb", "vdjbase", "custom"]:
        local = get_local_version(prov)
        if local:
            version_str = local.get("version", "unknown")
            species_count = str(local.get("species_count", "?"))
            current = is_up_to_date(prov)
            status_str = "[green]yes[/green]" if current else "[yellow]no[/yellow]"
        else:
            version_str = "not downloaded"
            species_count = "-"
            status_str = "[red]no[/red]"
        table.add_row(prov, version_str, species_count, status_str)

    console.print(table)

    from .scripts.validate import check_allele_counts, format_count_report

    rows, findings = check_allele_counts()
    if rows:
        console.print("\nOGRDB allele counts per pipeline stage (sadie.germlines.scripts.validate.check_allele_counts)")
        console.print(format_count_report(rows, findings), markup=False, highlight=False, soft_wrap=True)
        if any(not r["ok"] for r in rows) or any(f["kind"] == "UNEXPLAINED" for f in findings):
            raise SystemExit(1)


@germlines.command("rebuild")
@click.option(
    "--species",
    "-s",
    multiple=True,
    help="Species to rebuild (may be repeated). Defaults to all downloaded species.",
)
def rebuild_cmd(species: tuple) -> None:
    """Rebuild the IgBLAST databases Airr reads from already-downloaded germline data.

    Runs the germline pipeline (sources/ -> normalized/ -> igblast/) with a forced
    rebuild, without re-downloading source FASTA files.
    """
    rebuild_germlines(species=list(species) if species else None)
