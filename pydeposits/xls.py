"""Provides various utils for working with *.xls files."""


class RowNotFoundError(Exception):
    def __init__(self):
        super(RowNotFoundError, self).__init__("Unable to find a row that satisfy the template.")


def find_row(sheet, columns_template):
    for row_id in range(sheet.nrows):
        column_id = _find_columns(sheet, row_id, columns_template)
        if column_id is not None:
            return row_id, column_id

    raise RowNotFoundError()


def find_table(sheet, table_template):
    row_id, column_id = find_row(sheet, table_template[0])
    for line, columns_template in enumerate(table_template[1:], start=1):
        if not cmp_columns(sheet, row_id + line, column_id, columns_template):
            raise RowNotFoundError()

    return row_id, row_id + len(table_template), column_id


def _find_columns(sheet, row_id, columns_template):
    columns = _strip_values(sheet.row_values(row_id))

    for column_id in range(0, len(columns) - len(columns_template)):
        if _cmp_cell_values(columns_template, columns[column_id:column_id + len(columns_template)]):
            return column_id


def cmp_columns(sheet, row_id, column_id, template):
    values = _strip_values(sheet.row_values(row_id, column_id, column_id + len(template)))
    return _cmp_cell_values(template, values)


def cmp_column_types(sheet, row_id, column_id, template):
    cell_types = sheet.row_types(row_id, column_id, column_id + len(template))
    if len(template) != len(cell_types):
        return False

    for template, cell_type in zip(template, cell_types):
        if cell_type != template:
            return False

    return True


def _cmp_cell_values(template, values):
    if len(template) != len(values):
        return False

    for template, value in zip(template, values):
        if value != template:
            return False

    return True


def _strip_values(values):
    return [value.strip().replace("\n", " ") if isinstance(value, str) else value
            for value in values]
