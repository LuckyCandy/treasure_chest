import re
import argparse
import os

"""对比mysqldump出的sql脚本，生成修改语句(仅支持建表、增加编辑删除字段，增加删除索引)"""


def parse_table_schema(create_table_sql):
    # Extract table name
    table_name_match = re.search(r"CREATE TABLE `(\w+)`", create_table_sql)
    table_name = table_name_match.group(1) if table_name_match else "Unknown"

    # Extract column definitions including comments
    columns = []
    # This regex now accounts for optional COMMENT clauses at the end of column definitions
    column_matches = re.findall(r"(`([^\n\r\s]*?)\`\s+\w+.*?\s[^\n\r\s]*?COMMENT\s+\'.+?\')", create_table_sql,
                                re.DOTALL)
    for column in column_matches:
        columns.append({
            "name": column[1].strip(),
            "statement": column[0].strip(),
        })
    indexs = []
    index_matches = re.findall(r"((PRIMARY|UNIQUE|FULLTEXT|SPATIAL)?\sKEY\s+(`\w+`)?\s?(\(.*?\)))", create_table_sql,
                               re.DOTALL)
    for index in index_matches:
        indexs.append({
            "statement": index[0].strip(),
            "index_name": index[2].strip(),
            "type": index[1].strip(),
            "attrs": index[3].strip(),
        })

    return {
        "table_name": table_name,
        "all": create_table_sql,
        "index": indexs,
        "columns": columns
    }


def extract_schema_from_sql(file_path):
    with open(file_path, 'r') as file:
        sql_content = file.read()
    # Extract CREATE TABLE statements
    create_table_statements = re.findall(r"CREATE TABLE.*?;\n", sql_content, re.DOTALL)
    # Parse each table's schema
    parsed_schema = [parse_table_schema(statement) for statement in create_table_statements]
    return parsed_schema


def compare_and_generate_sql(source_schema, target_schema):
    statements = ""
    for s_schema in source_schema:
        find_table = False
        for t_schema in target_schema:
            if s_schema["table_name"] == t_schema["table_name"]:
                find_table = True
                # Handle column modifications and deletions.
                for s_colum in s_schema["columns"]:
                    find_column = False
                    for t_colum in t_schema["columns"]:
                        if s_colum["name"] == t_colum["name"]:
                            find_column = True
                            if s_colum["statement"] != t_colum["statement"]:
                                statements += f"ALTER TABLE `{s_schema['table_name']}` MODIFY COLUMN {t_colum['statement']};\n"
                            break
                    if not find_column:
                        statements += f"ALTER TABLE `{s_schema['table_name']}` DROP COLUMN {s_colum['name']};\n"
                # Handle adding new columns.
                for t_colum in t_schema["columns"]:
                    find_column = False
                    for s_colum in s_schema["columns"]:
                        if s_colum["name"] == t_colum["name"]:
                            find_column = True
                            break
                    if not find_column:
                        statements += f"ALTER TABLE `{s_schema['table_name']}` ADD COLUMN {t_colum['statement']};\n"

                # Handle index
                for s_index in s_schema["index"]:
                    find_index = False
                    for t_index in t_schema["index"]:
                        if s_index["statement"] == t_index["statement"]:
                            find_index = True
                    if not find_index:
                        if s_index["type"] == "PRIMARY":
                            statements += f"ALTER TABLE `{s_schema['table_name']}` DROP PRIMARY KEY;\n"
                        else:
                            statements += f"ALTER TABLE `{s_schema['table_name']}` DROP INDEX {s_index['index_name']};\n"
                for t_index in t_schema["index"]:
                    find_index = False
                    for s_index in s_schema["index"]:
                        if s_index["statement"] == t_index["statement"]:
                            find_index = True
                    if not find_index:
                        if t_index["type"] == "PRIMARY":
                            statements += f"ALTER TABLE `{s_schema['table_name']}` ADD PRIMARY KEY {t_index['attrs']};\n"
                        else:
                            statements += f"ALTER TABLE `{s_schema['table_name']}` ADD {t_index['type']} INDEX {t_index['index_name']}{t_index['attrs']};\n"
        if not find_table:
            statements += f"DROP TABLE `{s_schema['table_name']}`;\n"

    for t_schema in target_schema:
        find_table = False
        for s_schema in source_schema:
            if s_schema["table_name"] == t_schema["table_name"]:
                find_table = True
                break
        if not find_table:
            statements += f"{t_schema['all']}\n"
    return statements


def main():
    parser = argparse.ArgumentParser(description="Compare two SQL files and generate modification statements.")
    parser.add_argument("-s", "--source", required=True, help="source schema file")
    parser.add_argument("-t", "--target", required=True, help="target schema file")
    parser.add_argument("-o", "--output", required=True, help="output modification statements file")
    args = parser.parse_args()

    if not os.path.isfile(args.source) or not os.path.isfile(args.target):
        print(f"The specified input file '{args.source}' or '{args.target}' does not exist.")
        return

    source_parsed_schema = extract_schema_from_sql(args.source)
    target_parsed_schema = extract_schema_from_sql(args.target)
    print(compare_and_generate_sql(source_parsed_schema, target_parsed_schema))


if __name__ == "__main__":
    main()
