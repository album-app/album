from typing import Dict

from album.core.api.model.catalog_updates import ICatalogUpdates
from album.runner.core.api.model.solution import ISolution


def get_solution_as_string(solution: ISolution, solution_path):
    param_example_str = ''
    setup = solution.setup()
    if setup.args:
        for arg in setup.args:
            param_example_str += '--%s PARAMETER_VALUE ' % arg['name']
    res = 'Solution details about %s:\n\n' % solution_path
    if setup.title:
        res += '%s\n' % setup.title
        res += '%s\n' % ('=' * len(setup.title))
    if setup.description:
        res += '%s\n\n' % setup.description
    res += 'Group            : %s\n' % setup.group
    res += 'Name             : %s\n' % setup.name
    res += 'Version          : %s' % setup.version
    res += '%s' % get_credit_as_string(solution)
    res += 'Solution metadata:\n\n'
    if setup.authors:
        res += 'Solution authors : %s\n' % ", ".join(setup.authors)
    if setup.license:
        res += 'License          : %s\n' % setup.license
    if setup.acknowledgement:
        res += 'Acknowledgement  : %s\n' % setup.acknowledgement
    if setup.tags:
        res += 'Tags             : %s\n' % ", ".join(setup.tags)
    res += '\n'
    res += 'Usage:\n\n'
    res += '  album install %s\n' % solution_path
    res += '  album run %s %s\n' % (solution.coordinates(), param_example_str)
    res += '  album test %s\n' % solution.coordinates()
    res += '  album uninstall %s\n' % solution.coordinates()
    res += '\n'
    if setup.args:
        res += 'Run parameters:\n\n'
        for arg in setup.args:
            res += '  --%s: %s\n' % (arg["name"], arg["description"])
    return res


def get_credit_as_string(solution: ISolution) -> str:
    res = ''
    if solution.setup().cite:
        res += '\n\nCredits:\n\n'
        for citation in solution.setup().cite:
            text = citation['text']
            if 'doi' in citation:
                text += ' (DOI: %s)' % citation['doi']
            res += '%s\n' % text
        res += '\n'
    return res


def get_updates_as_string(updates: Dict[str, ICatalogUpdates]) -> str:
    res = ''
    for catalog_name in updates:
        change = updates[catalog_name]
        res += 'Catalog: %s\n' % change.catalog().name()
        if len(change.catalog_attribute_changes()) > 0:
            res += '  Catalog attribute changes:\n'
            for item in change.catalog_attribute_changes():
                res += '  name: %s, new value: %s\n' % (item.attribute(), item.new_value())
        if len(change.solution_changes()) > 0:
            res += '  Catalog solution changes:\n'
            for i, item in enumerate(change.solution_changes()):
                if i is len(change.solution_changes()) - 1:
                    res += '  └─ [%s] %s\n' % (item.change_type().name, item.coordinates())
                    separator = ' '
                else:
                    res += '  ├─ [%s] %s\n' % (item.change_type().name, item.coordinates())
                    separator = '|'
                res += '  %s     %schangelog: %s\n' % (
                    separator, (" " * len(item.change_type().name)), item.change_log())

        if len(change.catalog_attribute_changes()) == 0 and len(change.solution_changes()) == 0:
            res += '  No changes.\n'
    return res


def get_index_as_string(index_dict: dict):
    res = '\n'
    if 'catalogs' in index_dict:
        for catalog in index_dict['catalogs']:
            res += 'Catalog \'%s\':\n' % catalog['name']
            res += '├─ name: %s\n' % catalog['name']
            res += '├─ src: %s\n' % catalog['src']
            res += '├─ catalog_id: %s\n' % catalog['catalog_id']
            if len(catalog['solutions']) > 0:
                res += '├─ deletable: %s\n' % catalog['deletable']
                res += '└─ solutions:\n'
                for i, solution in enumerate(catalog['solutions']):
                    if i is len(catalog['solutions']) - 1:
                        res += '   └─ %s:%s:%s\n' % (
                            solution['setup']['group'], solution['setup']['name'], solution['setup']['version'])
                    else:
                        res += '   ├─ %s:%s:%s\n' % (
                            solution['setup']['group'], solution['setup']['name'], solution['setup']['version'])
            else:
                res += '└─ deletable: %s\n' % catalog['deletable']
    return res


def get_search_result_as_string(args, search_result):
    res = ''
    if len(search_result) > 0:
        res += 'Search results for "%s" - run `album info SOLUTION_ID` for more information:\n' % ' '.join(
            args.keywords)
        res += '[SCORE] SOLUTION_ID\n'
        for result in search_result:
            res += '[%s] %s\n' % (result[1], result[0])
    else:
        res += 'No search results for "%s".' % ' '.join(args.keywords)
    return res
