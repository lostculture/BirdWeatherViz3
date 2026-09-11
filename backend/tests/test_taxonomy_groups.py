"""
Tests for nocturnal taxonomy grouping.

The case that matters most here is bats. The eBird taxonomy only covers birds,
so every bat row arrives with order and family NULL — a classifier that reads
only those columns reports zero bats on a database that plainly contains them.
These tests pin the scientific-name fallback that fixes it, at all four ranks
BirdWeather reports.
"""

import pytest

from app.services import taxonomy_groups as tg


# (scientific_name, expected group) — exactly the shapes seen in real
# BirdWeather data, where the detector resolves to whatever rank it can.
BAT_ROWS = [
    ("Chiroptera", "bats"),                  # order
    ("Vespertilionidae", "bats"),            # family
    ("Myotis", "bats"),                      # genus
    ("Lasiurus", "bats"),                    # genus
    ("Lasionycteris", "bats"),               # genus
    ("Corynorhinus", "bats"),                # genus
    ("Eptesicus fuscus", "bats"),            # species
    ("Lasiurus cinereus", "bats"),
    ("Lasiurus borealis", "bats"),
    ("Myotis septentrionalis", "bats"),
    ("Lasionycteris noctivagans", "bats"),
    ("Corynorhinus rafinesquii", "bats"),
    ("Perimyotis subflavus", "bats"),
    # Elsewhere in the world.
    ("Pipistrellus pipistrellus", "bats"),
    ("Nyctalus noctula", "bats"),
    ("Rhinolophus ferrumequinum", "bats"),
    ("Tadarida brasiliensis", "bats"),
]


class TestBatsWithoutTaxonomyColumns:
    """Bats carry no order/family at all, so the name has to carry them."""

    @pytest.mark.parametrize("scientific_name,expected", BAT_ROWS)
    def test_classified_from_scientific_name_alone(self, scientific_name, expected):
        assert tg.classify(None, None, scientific_name) == expected

    def test_column_only_call_still_finds_nothing(self):
        # Documents the original bug: without the name, a bat is invisible.
        assert tg.classify(None, None) is None

    def test_populated_order_still_wins(self):
        assert tg.classify("Chiroptera", None, "Eptesicus fuscus") == "bats"


class TestBirds:
    """Owls and nightjars normally have columns, but names must work too."""

    @pytest.mark.parametrize(
        "order,family,name,expected",
        [
            ("Strigiformes", "Strigidae", "Strix varia", "owls"),
            ("Strigiformes", "Tytonidae", "Tyto alba", "owls"),
            (None, None, "Megascops asio", "owls"),
            (None, None, "Strigidae", "owls"),
            ("Caprimulgiformes", "Caprimulgidae", "Chordeiles minor", "nightjars"),
            (None, None, "Antrostomus vociferus", "nightjars"),
            (None, None, "Caprimulgidae", "nightjars"),
        ],
    )
    def test_classified(self, order, family, name, expected):
        assert tg.classify(order, family, name) == expected

    @pytest.mark.parametrize(
        "order,family,name",
        [
            ("Passeriformes", "Turdidae", "Turdus migratorius"),
            ("Passeriformes", "Cardinalidae", "Cardinalis cardinalis"),
            ("Accipitriformes", "Accipitridae", "Accipiter cooperii"),
            ("Piciformes", "Picidae", "Dryobates villosus"),
            (None, None, "Amblycorypha oblongifolia"),  # a katydid
            (None, None, "Aves sp."),
        ],
    )
    def test_day_birds_and_others_are_not_nocturnal(self, order, family, name):
        assert tg.classify(order, family, name) is None


class TestGroupDefinitions:
    def test_every_group_has_a_taxa_set_covering_its_ranks(self):
        for key, spec in tg.GROUPS.items():
            assert spec["taxa"], key
            assert spec["orders"] <= spec["taxa"]
            assert spec["families"] <= spec["taxa"]
            assert spec["genera"] <= spec["taxa"]

    def test_taxa_sets_do_not_overlap_between_groups(self):
        # An overlap would make classify() order-dependent and unpredictable.
        seen: dict = {}
        for key, spec in tg.GROUPS.items():
            for taxon in spec["taxa"]:
                assert taxon not in seen, f"{taxon} in both {seen.get(taxon)} and {key}"
                seen[taxon] = key

    def test_all_taxa_are_lowercase(self):
        # group_filter and classify both lowercase before comparing.
        for spec in tg.GROUPS.values():
            for taxon in spec["taxa"]:
                assert taxon == taxon.lower()

    def test_nocturnal_groups_matches_group_keys(self):
        assert set(tg.NOCTURNAL_GROUPS) == set(tg.GROUPS)

    def test_unknown_group_is_rejected(self):
        with pytest.raises(ValueError):
            tg.group_filter("moths")


class TestCaseAndWhitespace:
    @pytest.mark.parametrize(
        "name", ["chiroptera", "CHIROPTERA", "  Chiroptera  ", "Myotis  lucifugus"]
    )
    def test_tolerated(self, name):
        assert tg.classify(None, None, name) == "bats"

    def test_empty_inputs(self):
        assert tg.classify(None, None, None) is None
        assert tg.classify("", "", "") is None
