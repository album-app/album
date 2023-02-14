import enum
import logging
from typing import Dict

import colorlog

from album.core.api.model.catalog_updates import ICatalogUpdates
from album.runner.core.api.model.solution import ISolution


def get_solution_as_string(solution: ISolution, solution_path):
    setup = solution.setup()
    res = "Solution details about %s:\n\n" % solution_path
    if setup.title:
        res += "%s\n" % setup.title
        res += "%s\n" % ("=" * len(setup.title))
    if setup.description:
        res += "%s\n\n" % setup.description
    res += "Group            : %s\n" % setup.group
    res += "Name             : %s\n" % setup.name
    res += "Version          : %s" % setup.version
    res += "%s" % get_credit_as_string(solution)
    res += "\n\n"
    if setup.solution_creators:
        res += "Solution creators : %s\n" % ", ".join(setup.solution_creators)
    if setup.license:
        res += "License           : %s\n" % setup.license
    if setup.acknowledgement:
        res += "Acknowledgement   : %s\n" % setup.acknowledgement
    if setup.tags:
        res += "Tags              : %s\n" % ", ".join(setup.tags)
    res += "\n"
    res += "Usage:\n\n"
    res += "  album install %s\n" % solution_path
    res += "  %s\n" % get_solution_run_call_as_string(solution)
    res += "  album test %s\n" % solution.coordinates()
    res += "  album uninstall %s\n" % solution.coordinates()
    res += "\n"
    if setup.args:
        res += "Run parameters:\n\n"
        for arg in setup.args:
            res += "  --%s: %s\n" % (arg["name"], arg["description"])
    return res


def get_solution_run_call_as_string(solution):
    param_example_str = ""
    if solution.setup().args:
        for arg in solution.setup().args:
            if "required" in arg:
                if arg["required"]:
                    param_example_str += "--%s PARAMETER_VALUE " % arg["name"]
    run_call = "album run %s %s" % (solution.coordinates(), param_example_str)
    return run_call


def get_credit_as_string(solution: ISolution) -> str:
    res = ""
    if solution.setup().cite:
        res += "\n\nCredits:\n\n"
        for citation in solution.setup().cite:
            text = get_citation_as_string(citation)
            res += "%s\n" % text
        res += "\n"
    return res


def get_citation_as_string(citation):
    text = citation["text"]
    if "doi" in citation and "url" in citation:
        text += " (DOI: %s, %s)" % (citation["doi"], citation["url"])
    else:
        if "doi" in citation:
            text += " (DOI: %s)" % citation["doi"]
        if "url" in citation:
            text += " (%s)" % citation["url"]
    return text


def get_updates_as_string(updates: Dict[str, ICatalogUpdates]) -> str:
    res = ""
    for catalog_name in updates:
        change = updates[catalog_name]
        res += "Catalog: %s\n" % change.catalog().name()
        if len(change.catalog_attribute_changes()) > 0:
            res += "  Catalog attribute changes:\n"
            for item in change.catalog_attribute_changes():
                res += "  name: %s, new value: %s\n" % (
                    item.attribute(),
                    item.new_value(),
                )
        if len(change.solution_changes()) > 0:
            res += "  Catalog solution changes:\n"
            for i, item in enumerate(change.solution_changes()):
                if i is len(change.solution_changes()) - 1:
                    res += "  └─ [%s] %s\n" % (
                        item.change_type().name,
                        item.coordinates(),
                    )
                    separator = " "
                else:
                    res += "  ├─ [%s] %s\n" % (
                        item.change_type().name,
                        item.coordinates(),
                    )
                    separator = "|"
                res += "  %s     %schangelog: %s\n" % (
                    separator,
                    (" " * len(item.change_type().name)),
                    item.change_log(),
                )

        if (
            len(change.catalog_attribute_changes()) == 0
            and len(change.solution_changes()) == 0
        ):
            res += "  No changes.\n"
    return res


def get_index_as_string(index_dict: dict):
    res = "\n"
    if "base" in index_dict:
        res += "Album base directory: %s\n" % index_dict["base"]
    res += "Catalogs in your local collection:\n"
    if "catalogs" in index_dict:
        for catalog in index_dict["catalogs"]:
            res += "Catalog '%s':\n" % catalog["name"]
            res += "├─ name: %s\n" % catalog["name"]
            res += "├─ src: %s\n" % catalog["src"]
            res += "├─ catalog_id: %s\n" % catalog["catalog_id"]
            if len(catalog["solutions"]) > 0:
                res += "├─ deletable: %s\n" % catalog["deletable"]
                res += "└─ [installed] solutions:\n"
                for i, solution in enumerate(catalog["solutions"]):
                    installed = " "
                    if solution["internal"]["installed"]:
                        installed = "x"
                    if i is len(catalog["solutions"]) - 1:
                        res += "   └─ [%s] %s:%s:%s\n" % (
                            installed,
                            solution["setup"]["group"],
                            solution["setup"]["name"],
                            solution["setup"]["version"],
                        )
                    else:
                        res += "   ├─ [%s] %s:%s:%s\n" % (
                            installed,
                            solution["setup"]["group"],
                            solution["setup"]["name"],
                            solution["setup"]["version"],
                        )
            else:
                res += "└─ deletable: %s\n" % catalog["deletable"]
    return res


def get_search_result_as_string(args, search_result):
    res = ""
    if len(search_result) > 0:
        res += (
            'Search results for "%s" - run `album info SOLUTION_ID` for more information:\n'
            % " ".join(args.keywords)
        )
        res += "[SCORE] SOLUTION_ID\n"
        for result in search_result:
            res += "[%s] %s\n" % (result[1], result[0])
    else:
        res += 'No search results for "%s".' % " ".join(args.keywords)
    return res


def get_logging_formatter(fmt=None, time=None):
    if isinstance(fmt, enum.Enum):
        if not fmt.value:
            fmt = "%(log_color)s%(asctime)s %(levelname)-7s %(shortened_name)s%(message)s"
    elif not fmt:
        fmt = "%(log_color)s%(asctime)s %(levelname)-7s %(shortened_name)s%(message)s"
    if not time:
        time = "%H:%M:%S"
    return colorlog.ColoredFormatter(
        fmt,
        time,
        log_colors={
            "DEBUG": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bold",
        },
    )


def get_logger_name_minimizer_filter():
    class NameDotFilter(logging.Filter):
        def filter(self, record):
            count = record.name.count(".") + record.name.count("~")
            if count > 0:
                record.shortened_name = "~" * count + " "
            else:
                record.shortened_name = ""
            return True

    return NameDotFilter()


def get_message_filter():
    class MessageFilter(logging.Filter):
        def filter(self, record):
            self._apply_mamba_menuinst_filter(record)
            return True

        def _apply_mamba_menuinst_filter(self, record):
            if (
                record.msg
                and isinstance(record.msg, str)
                and "menuinst called from non-root env" in record.msg
            ):
                record.levelname = "WARNING"
                record.levelno = logging.getLevelName("WARNING")

    return MessageFilter()
