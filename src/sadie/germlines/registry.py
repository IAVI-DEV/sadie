"""
Species Registry
================

Single source of truth for all species name mappings used across the
germlines module.  Every other module should import from here rather
than define its own tables.

Directions
----------
*  ALIASES       – user-visible aliases and Latin binomials → canonical slug
*  TO_IMGT       – slug → IMGT V-QUEST directory name
*  TO_VDJBASE    – slug → VDJbase API display name
*  FROM_OGRDB    – OGRDB Latin name → slug
*  TAXONOMY_IDS  – slug → NCBI Taxonomy ID string
*  TO_LATIN      – slug → G3-style Latin name (Genus_species)

Computed reverses (derived at class definition time):
*  FROM_IMGT     – IMGT directory name → slug
*  TO_OGRDB      – slug → OGRDB Latin name
*  FROM_VDJBASE  – VDJbase API display name → slug
*  FROM_TAXON    – NCBI Taxonomy ID string → slug
"""


class SpeciesRegistry:
    # ------------------------------------------------------------------
    # Edge 1 — user input → canonical slug
    # ------------------------------------------------------------------
    ALIASES: dict[str, str] = {
        # common alternate names for macaque
        "rhesus_macaque": "macaque",
        "rhesus_monkey": "macaque",
        "rhesus": "macaque",
        # other common aliases used across sources and tools
        "cynomolgus_monkey": "cynomolgus",
        "crab-eating_macaque": "crab_eating_macaque",
        "sus_scrofa": "pig",
        "bos_taurus": "cow",
        "canis_familiaris": "dog",
        "felis_catus": "cat",
        "oryctolagus_cuniculus": "rabbit",
        "mus_musculus": "mouse",
        "rattus_norvegicus": "rat",
        "homo_sapiens": "human",
        "danio_rerio": "zebrafish",
        "oncorhynchus_mykiss": "rainbow_trout",
        "salmo_salar": "atlantic_salmon",
        "gallus_gallus": "chicken",
    }

    # ------------------------------------------------------------------
    # Edge 2 — slug → provider-specific names
    # ------------------------------------------------------------------

    # IMGT V-QUEST directory name  (Genus_species[_strain])
    TO_IMGT: dict[str, str] = {
        "human": "Homo_sapiens",
        "mouse": "Mus_musculus",
        "mouse_c57bl6j": "Mus_musculus_C57BL6J",
        "rat": "Rattus_norvegicus",
        "rabbit": "Oryctolagus_cuniculus",
        "macaque": "Macaca_mulatta",
        "cynomolgus": "Macaca_fascicularis",
        "dog": "Canis_lupus_familiaris",
        "cat": "Felis_catus",
        "pig": "Sus_scrofa",
        "cow": "Bos_taurus",
        "sheep": "Ovis_aries",
        "goat": "Capra_hircus",
        "horse": "Equus_caballus",
        "chicken": "Gallus_gallus",
        "alpaca": "Vicugna_pacos",
        "camel": "Camelus_dromedarius",
        "zebrafish": "Danio_rerio",
        "gorilla": "Gorilla_gorilla_gorilla",
        "chimpanzee": "Pan_troglodytes",
        "orangutan_sumatran": "Pongo_abelii",
        "orangutan_bornean": "Pongo_pygmaeus",
        "ferret": "Mustela_putorius_furo",
        "mink": "Neogale_vison",
        "dolphin": "Tursiops_truncatus",
        "platypus": "Ornithorhynchus_anatinus",
        "atlantic_salmon": "Salmo_salar",
        "rainbow_trout": "Oncorhynchus_mykiss",
        "atlantic_cod": "Gadus_morhua",
        "channel_catfish": "Ictalurus_punctatus",
        "lemur": "Lemur_catta",
        "owl_monkey": "Aotus_nancymaae",
        "naked_mole_rat": "Heterocephalus_glaber",
    }

    # VDJbase API display name
    TO_VDJBASE: dict[str, str] = {
        "human": "Human",
        "macaque": "Rhesus Macaque",
        "mouse": "Mouse",
    }

    # ------------------------------------------------------------------
    # Edge 3 — provider-specific names → slug
    # ------------------------------------------------------------------

    # OGRDB uses Latin names with spaces (e.g., "Homo sapiens")
    FROM_OGRDB: dict[str, str] = {
        "Homo sapiens": "human",
        "Mus musculus": "mouse",
        "Macaca mulatta": "macaque",
        "Rattus norvegicus": "rat",
        "Canis lupus familiaris": "dog",
        "Oryctolagus cuniculus": "rabbit",
    }

    # ------------------------------------------------------------------
    # Taxonomy IDs (slug → NCBI Taxonomy ID string)
    # ------------------------------------------------------------------
    TAXONOMY_IDS: dict[str, str] = {
        "human": "9606",
        "mouse": "10090",
        "macaque": "9544",
        "rat": "10116",
        "dog": "9615",
        "rabbit": "9986",
    }

    # ------------------------------------------------------------------
    # G3-style Latin names (slug → Genus_species with underscores)
    # ------------------------------------------------------------------
    TO_LATIN: dict[str, str] = {
        "human": "Homo_sapiens",
        "mouse": "Mus_musculus",
        "rat": "Rattus_norvegicus",
        "rabbit": "Oryctolagus_cuniculus",
        "dog": "Canis_lupus_familiaris",
        "cat": "Felis_catus",
        "macaque": "Macaca_mulatta",
        "alpaca": "Vicugna_pacos",
        "cynomolgus": "Macaca_fascicularis",
        "pig": "Sus_scrofa",
        "cow": "Bos_taurus",
        "sheep": "Ovis_aries",
        "goat": "Capra_hircus",
        "horse": "Equus_caballus",
        "chicken": "Gallus_gallus",
        "camel": "Camelus_dromedarius",
        "zebrafish": "Danio_rerio",
        "gorilla": "Gorilla_gorilla_gorilla",
        "chimpanzee": "Pan_troglodytes",
        "orangutan_sumatran": "Pongo_abelii",
        "orangutan_bornean": "Pongo_pygmaeus",
    }

    # ------------------------------------------------------------------
    # Computed reverses (derived at class definition time)
    # ------------------------------------------------------------------
    FROM_IMGT: dict[str, str] = {v: k for k, v in TO_IMGT.items()}
    TO_OGRDB: dict[str, str] = {v: k for k, v in FROM_OGRDB.items()}
    FROM_VDJBASE: dict[str, str] = {v: k for k, v in TO_VDJBASE.items()}
    FROM_TAXON: dict[str, str] = {v: k for k, v in TAXONOMY_IDS.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def normalize(cls, name: str) -> str:
        """Resolve a user-supplied name to its canonical slug.

        Unknown names are returned unchanged so callers can handle them
        (raise BadDataSet, BadNumberingArgument, etc.) with their own
        error types.
        """
        return cls.ALIASES.get(name, name)
