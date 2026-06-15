#!/usr/bin/env python3
"""Replace # Part N markers in an ebook .txt file with the chapter titles
extracted from the index at the top of the file.

Usage:
    python fix_parts.py libro.txt              # overwrites in place
    python fix_parts.py libro.txt output.txt   # writes to output file
"""

import re
import sys


def extract_chapters(text, index_start, index_end):
    """Return ordered list of (number, title) from the numbered index section."""
    section = text[index_start:index_end]
    return re.findall(r'^(\d+)\.\s+(.+)$', section, re.MULTILINE)


def replace_parts(content, chapters):
    counter = [0]

    def replacer(match):
        i = counter[0]
        counter[0] += 1
        if i < len(chapters):
            num, title = chapters[i]
            return f'# Capítulo {num}. {title}'
        return match.group(0)

    new_content = re.sub(r'^# Part \d+$', replacer, content, flags=re.MULTILINE)
    return new_content, counter[0]


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.txt [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Locate the Author line (index starts after it)
    author_match = re.search(r'^Author:.*$', content, re.MULTILINE)
    if not author_match:
        sys.exit("Error: 'Author:' line not found in file")

    # Locate the first # Part (index ends before it)
    first_part_match = re.search(r'^# Part \d+', content, re.MULTILINE)
    if not first_part_match:
        sys.exit("Error: no '# Part' markers found in file")

    chapters = extract_chapters(content, author_match.end(), first_part_match.start())
    if not chapters:
        sys.exit("Error: no numbered chapter list found between Author line and first # Part")

    print(f"Chapters found in index: {len(chapters)}")
    for num, title in chapters:
        print(f"  {num}. {title}")

    new_content, replaced = replace_parts(content, chapters)

    remaining = len(re.findall(r'^# Part \d+$', new_content, re.MULTILINE))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\nReplaced {replaced} # Part markers with chapter titles.")
    if remaining:
        print(f"Left unchanged (beyond index): {remaining} markers")
    print(f"Written to: {output_file}")


if __name__ == '__main__':
    main()
