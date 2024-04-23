"""Main methods for the import_statistics integration."""

import os
import zoneinfo

import pandas as pd

from homeassistant.core import ServiceCall
import pytz
import custom_components.import_statistics.helpers as helpers
from custom_components.import_statistics.helpers import _LOGGER
from custom_components.import_statistics.const import ATTR_DECIMAL, ATTR_TIMEZONE_IDENTIFIER, ATTR_DELIMITER

def prepare_data_to_import(file_path: str, call: ServiceCall) -> dict:
    """Prepare data to import statistics from a file.

    Args:
        file_path: Path to the file with the data to be imported.
        call: The call data containing the necessary information.

    Returns:
        A dictionary containing the imported statistics.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If there is an implementation error.

    """
    decimal, timezone_identifier, delimiter = handle_arguments(file_path, call)

    df = pd.read_csv(file_path, sep=delimiter, decimal=decimal, engine="python")
    stats = handle_dataframe(df, timezone_identifier)
    return stats

def handle_arguments(file_path: str, call: ServiceCall) -> tuple:
    """Handle the arguments for importing statistics from a file.

    Args:
        file_path (str): The path of the file to import statistics from.
        call (ServiceCall): The service call object containing additional data.

    Returns:
        tuple: A tuple containing the decimal separator, timezone identifier, and delimiter.

    Raises:
        ValueError: If the timezone identifier is invalid.
        FileNotFoundError: If the file path does not exist.

    """

    if call.data.get(ATTR_DECIMAL, True):
        decimal = ","
    else:
        decimal = "."
    timezone_identifier = call.data.get(ATTR_TIMEZONE_IDENTIFIER)

    if timezone_identifier not in pytz.all_timezones:
        helpers.handle_error(f"Invalid timezone_identifier: {timezone_identifier}")

    delimiter = call.data.get(ATTR_DELIMITER)
    _LOGGER.info("Importing statistics from file: %s", file_path)
    _LOGGER.debug("Timezone_identifier: %s", timezone_identifier)
    _LOGGER.debug("Delimiter: %s", delimiter)
    _LOGGER.debug("Decimal separator: %s", decimal)

    if not os.path.exists(file_path):
        helpers.handle_error(f"path {file_path} does not exist.")
    return decimal,timezone_identifier,delimiter

def handle_dataframe(df: pd.DataFrame, timezone_identifier: str) -> dict:
    """Process a dataframe and extract statistics based on the specified columns and timezone.

    Args:
        df (pandas.DataFrame): The input dataframe containing the statistics data.
        columns (list): The list of columns to extract from the dataframe.
        timezone_identifier (str): The timezone identifier to convert the timestamps.

    Returns:
        dict: A dictionary containing the extracted statistics, organized by statistic_id.

    Raises:
        ImplementationError: If both 'mean' and 'sum' columns are present in the columns list.

    """
    columns = df.columns
    _LOGGER.debug("Columns:")
    _LOGGER.debug(columns)
    if not helpers.are_columns_valid(columns):
        helpers.handle_error(
            "Implementation error. helpers.are_columns_valid returned false, this should never happen, because helpers.are_columns_valid throws an exception!"
        )
    stats = {}
    timezone = zoneinfo.ZoneInfo(timezone_identifier)
    has_mean = "mean" in columns
    has_sum = "sum" in columns
    for _index, row in df.iterrows():
        statistic_id = row["statistic_id"]
        if statistic_id not in stats: # New statistic id found

            source = helpers.get_source(statistic_id)
            metadata = {
                "has_mean": has_mean,
                "has_sum": has_sum,
                "source": source,
                "statistic_id": statistic_id,
                "name": None,
                "unit_of_measurement": row["unit"],
            }
            stats[statistic_id] = (metadata, [])

        if has_mean:
            new_stat = helpers.get_mean_stat(row, timezone)
        if has_sum:
            new_stat = helpers.get_sum_stat(row, timezone)
        stats[statistic_id][1].append(new_stat)
    return stats
