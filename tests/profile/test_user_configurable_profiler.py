import pandas as pd
import pytest

import great_expectations as ge
from great_expectations.data_context.util import file_relative_path
from great_expectations.profile.user_configurable_profiler import (
    UserConfigurableProfiler,
)


@pytest.fixture()
def cardinality_dataset():
    df = pd.DataFrame(
        {
            "col_none": [None for i in range(0, 1000)],
            "col_one": [0 for i in range(0, 1000)],
            "col_two": [i % 2 for i in range(0, 1000)],
            "col_very_few": [i % 10 for i in range(0, 1000)],
            "col_few": [i % 50 for i in range(0, 1000)],
            "col_many": [i % 100 for i in range(0, 1000)],
            "col_very_many": [i % 500 for i in range(0, 1000)],
            "col_unique": [i for i in range(0, 1000)],
        }
    )
    batch_df = ge.dataset.PandasDataset(df)

    return batch_df


@pytest.fixture()
def titanic_dataset():
    df = ge.read_csv(file_relative_path(__file__, "../test_sets/Titanic.csv"))
    batch_df = ge.dataset.PandasDataset(df)

    return batch_df


@pytest.fixture()
def possible_expectations_set():
    return {
        "expect_table_columns_to_match_ordered_list",
        "expect_table_row_count_to_be_between",
        "expect_column_values_to_be_in_type_list",
        "expect_column_values_to_not_be_null",
        "expect_column_values_to_be_null",
        "expect_column_proportion_of_unique_values_to_be_between",
        "expect_column_min_to_be_between",
        "expect_column_max_to_be_between",
        "expect_column_mean_to_be_between",
        "expect_column_median_to_be_between",
        "expect_column_quantile_values_to_be_between",
        "expect_column_values_to_be_in_set",
        "expect_column_values_to_be_between",
        "expect_column_values_to_be_unique",
    }


@pytest.fixture()
def full_config_cardinality_dataset_no_semantic_types():
    return {
        "primary_or_compound_key": ["col_unique"],
        "ignored_columns": [
            "col_one",
        ],
        "value_set_threshold": "unique",
        "table_expectations_only": False,
        "excluded_expectations": ["expect_column_values_to_not_be_null"],
    }


@pytest.fixture()
def full_config_cardinality_dataset_with_semantic_types():
    return {
        "semantic_types": {
            "numeric": ["col_few", "col_many", "col_very_many"],
            "value_set": ["col_one", "col_two", "col_very_few"],
        },
        "primary_or_compound_key": ["col_unique"],
        "ignored_columns": [
            "col_one",
        ],
        "value_set_threshold": "unique",
        "table_expectations_only": False,
        "excluded_expectations": ["expect_column_values_to_not_be_null"],
    }


def get_set_of_columns_and_expectations_from_suite(suite):
    columns = {
        i.kwargs.get("column") for i in suite.expectations if i.kwargs.get("column")
    }
    expectations = {i.expectation_type for i in suite.expectations}

    return columns, expectations


def test__initialize_cache_with_metadata_no_config(
    cardinality_dataset,
):
    cache = UserConfigurableProfiler._initialize_cache_with_metadata(
        cardinality_dataset,
    )
    assert cache.get("primary_or_compound_key") == []
    assert cache.get("ignored_columns") == []
    assert not cache.get("value_set_threshold")
    assert not cache.get("table_expectations_only")
    assert cache.get("excluded_expectations") == []


def test__initialize_cache_with_metadata_full_config_no_semantic_types(
    cardinality_dataset, full_config_cardinality_dataset_no_semantic_types
):
    cache = UserConfigurableProfiler._initialize_cache_with_metadata(
        cardinality_dataset, full_config_cardinality_dataset_no_semantic_types
    )
    assert cache.get("primary_or_compound_key") == ["col_unique"]
    assert cache.get("ignored_columns") == [
        "col_one",
    ]
    assert cache.get("value_set_threshold") == "unique"
    assert not cache.get("table_expectations_only")
    assert cache.get("excluded_expectations") == ["expect_column_values_to_not_be_null"]

    assert "col_one" not in cache.keys()


def test__initialize_cach_with_metadata_with_semantic_types(
    cardinality_dataset, full_config_cardinality_dataset_with_semantic_types
):
    cache = UserConfigurableProfiler._initialize_cache_with_metadata(
        cardinality_dataset, full_config_cardinality_dataset_with_semantic_types
    )

    assert not cache.get("col_one")

    assert cache.get("col_none") == {
        "cardinality": "none",
        "type": "numeric",
        "semantic_types": [],
    }
    assert cache.get("col_two") == {
        "cardinality": "two",
        "type": "int",
        "semantic_types": ["value_set"],
    }
    assert cache.get("col_very_few") == {
        "cardinality": "very_few",
        "type": "int",
        "semantic_types": ["value_set"],
    }
    assert cache.get("col_few") == {
        "cardinality": "few",
        "type": "int",
        "semantic_types": ["numeric"],
    }
    assert cache.get("col_many") == {
        "cardinality": "many",
        "type": "int",
        "semantic_types": ["numeric"],
    }
    assert cache.get("col_very_many") == {
        "cardinality": "very_many",
        "type": "int",
        "semantic_types": ["numeric"],
    }
    assert cache.get("col_unique") == {
        "cardinality": "unique",
        "type": "int",
        "semantic_types": [],
    }


def test__validate_config():
    bad_keyword = {"bad_keyword": 100}
    with pytest.raises(AssertionError) as e:
        UserConfigurableProfiler._validate_config(bad_keyword)
    assert e.value.args[0] == "Parameter bad_keyword from config is not recognized."

    bad_param_type_ignored_columns = {"ignored_columns": "col_name"}
    with pytest.raises(AssertionError) as e:
        UserConfigurableProfiler._validate_config(bad_param_type_ignored_columns)
    assert (
        e.value.args[0]
        == "Config parameter ignored_columns must be formatted as a <class 'list'> rather than a <class 'str'>."
    )

    bad_param_type_table_expectations_only = {"table_expectations_only": "True"}
    with pytest.raises(AssertionError) as e:
        UserConfigurableProfiler._validate_config(
            bad_param_type_table_expectations_only
        )
    assert (
        e.value.args[0]
        == "Config parameter table_expectations_only must be formatted as a <class 'bool'> rather than a <class 'str'>."
    )


def test__validate_semantic_types_dict(
    cardinality_dataset, full_config_cardinality_dataset_with_semantic_types
):
    bad_semantic_types_dict_type = {"semantic_types": {"value_set": "few"}}
    cache = UserConfigurableProfiler._initialize_cache_with_metadata(
        dataset=cardinality_dataset, config=bad_semantic_types_dict_type
    )
    with pytest.raises(AssertionError) as e:
        UserConfigurableProfiler._validate_semantic_types_dict(
            cardinality_dataset, bad_semantic_types_dict_type, cache
        )
    assert e.value.args[0] == (
        "Entries in semantic type dict must be lists of column names e.g. "
        "{'semantic_types': {'numeric': ['number_of_transactions']}}"
    )


def test_build_suite_no_config(titanic_dataset, possible_expectations_set):
    suite = UserConfigurableProfiler.build_suite(titanic_dataset)
    expectations_from_suite = {i.expectation_type for i in suite.expectations}

    assert expectations_from_suite.issubset(possible_expectations_set)
    assert len(suite.expectations) == 48


def test_build_suite_with_config(titanic_dataset, possible_expectations_set):
    config = {
        "ignored_columns": ["Survived", "Unnamed: 0"],
        "excluded_expectations": ["expect_column_mean_to_be_between"],
        "primary_or_compound_key": ["Name"],
        "table_expectations_only": False,
        "value_set_threshold": "very_few",
    }

    suite = UserConfigurableProfiler.build_suite(dataset=titanic_dataset, config=config)
    (
        columns_with_expectations,
        expectations_from_suite,
    ) = get_set_of_columns_and_expectations_from_suite(suite)

    columns_expected_in_suite = {"Name", "PClass", "Age", "Sex", "SexCode"}
    assert columns_with_expectations == columns_expected_in_suite
    assert expectations_from_suite.issubset(possible_expectations_set)
    assert "expect_column_mean_to_be_between" not in expectations_from_suite
    assert len(suite.expectations) == 29


def test_build_suite_with_semantic_types_dict(
    cardinality_dataset,
    possible_expectations_set,
    full_config_cardinality_dataset_with_semantic_types,
):
    suite = UserConfigurableProfiler.build_suite(
        cardinality_dataset, full_config_cardinality_dataset_with_semantic_types
    )
    (
        columns_with_expectations,
        expectations_from_suite,
    ) = get_set_of_columns_and_expectations_from_suite(suite)

    assert "column_one" not in columns_with_expectations
    assert "expect_column_values_to_not_be_null" not in expectations_from_suite
    assert expectations_from_suite.issubset(possible_expectations_set)
    assert len(suite.expectations) == 34

    value_set_expectations = [
        i
        for i in suite.expectations
        if i.expectation_type == "expect_column_values_to_be_in_set"
    ]
    value_set_columns = {i.kwargs.get("column") for i in value_set_expectations}

    assert len(value_set_columns) == 2
    assert value_set_columns == {"col_two", "col_very_few"}
