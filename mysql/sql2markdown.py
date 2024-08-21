import re
import argparse
import os

"""将使用mysqldump出的sql脚本，抽离出创建语句，生成数据词典"""


def parse_table_schema(create_table_sql):
    # Extract table name
    table_name_match = re.search(r"CREATE TABLE `(\w+)`", create_table_sql)
    table_name = table_name_match.group(1) if table_name_match else "Unknown"

    # Extract column definitions including comments
    columns = []
    # This regex now accounts for optional COMMENT clauses at the end of column definitions
    column_matches = re.findall(r"`([^\n\r\s]*?)\`\s+(\w+).*?\s[^\n\r\s]*?COMMENT\s+\'(.+?)\'", create_table_sql,
                                re.DOTALL)
    for column in column_matches:
        columns.append({
            "name": column[0].strip('()'),
            "data_type": column[1].strip('()'),
            "comment": column[2] if column[2] else ""  # If no comment, leave it empty
        })

    return {
        "table_name": table_name,
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


def generate_markdown(tables, head):
    markdown = str.format("## {}\n\n", head)
    count = 1
    for table in tables:
        markdown += f"### `{count}`.`{table['table_name']}`\n\n"
        markdown += "| Field      | Type         | Comment                                    |\n"
        markdown += "|------------|--------------|--------------------------------------------|\n"
        for column in table['columns']:
            markdown += f"| {column['name'].ljust(12)} | {column['data_type'].ljust(14)} | {column['comment']} |\n"
        markdown += "\n"
        count += 1
    return markdown


def main():
    parser = argparse.ArgumentParser(description="Convert SQL file to Markdown format.")
    parser.add_argument("-t", "--title", required=False, help="Markdown file title")
    parser.add_argument("-f", "--file", required=True, help="Path to the SQL file")
    parser.add_argument("-o", "--output", required=True, help="Output Markdown file")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"The specified input file '{args.file}' does not exist.")
        return

    parsed_schema = extract_schema_from_sql(args.file)
    md_content = generate_markdown(parsed_schema, args.title if args.title else "Database Schema")
    with open(args.output, "w") as f:
        f.write(md_content)


if __name__ == "__main__":
    main()
